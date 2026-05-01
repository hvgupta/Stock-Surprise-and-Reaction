from app.adapters import (
    SP500_COMPANIES,
    fetch_ticker_historical_prices,
    get_current_forward_pe_of_ticker,
    get_current_pe_of_ticker,
    get_earnings_history_of_ticker,
    get_last_earnings_call_of_ticker,
)
from app.logger import get_configured_logger
from app.model import PropotionateRequest, ReactionRequest
from app.sql_functions import (
    SQLiteDatabase,
    get_all_supported_tickers,
    get_dates_of_ticker,
    get_ticker_proportionality_data,
    get_ticker_surprise,
    ticker_in_db,
    upsert_earnings_calendar_rows,
)
from app.helper_functions import get_reaction_for_date, get_surprise_for_date

logger = get_configured_logger(__name__)

import asyncio
import pandas as pd
from typing import Dict, List, Any, cast
from fastapi import Depends, HTTPException, Query, Request


async def health_check():
    return {"status": "ok"}


async def get_supported_tickers(request: Request):
    all_tickers = get_all_supported_tickers(
        cast(SQLiteDatabase, request.app.state.database)
    )
    return {"tickers": all_tickers, "count": len(all_tickers)}


async def get_filing_dates_for_ticker(request: Request, ticker: str):
    db_conn = cast(SQLiteDatabase, request.app.state.database)
    filing_dates = get_dates_of_ticker(db_conn, ticker)
    if not filing_dates:
        raise HTTPException(
            status_code=404,
            detail=f"filing dates not found for ticker {ticker}",
        )
    return {"ticker": ticker, "filing_dates": filing_dates}


async def fetch_surprise_for_ticker(
    request: Request, ticker: str, date: str | None = Query(default=None)
):
    db_conn = cast(SQLiteDatabase, request.app.state.database)

    surprise = get_ticker_surprise(db_conn, ticker, date)
    logger.info(f"Fetched surprise for {ticker} on {date}: {surprise}")
    if surprise is not None:
        logger.info(
            f"Surprise data found in database for {ticker} on {date}, returning cached value"
        )
        return {
            "ticker": ticker,
            "surprise": (surprise if isinstance(surprise, Dict) else {date: surprise}),
        }

    if ticker_in_db(db_conn, ticker) is True:
        raise HTTPException(
            status_code=404,
            detail=f"surprise data not found for ticker {ticker} on date {date}, even though the ticker exists in the database, likely means that the date is not supported for this ticker",
        )

    eps_data = get_earnings_history_of_ticker(ticker)
    if eps_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"the ticker {ticker} is not supported, check the /supported_tickers endpoint for the list of supported tickers",
        )

    if len(eps_data) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"EPS data incomplete for ticker {ticker} on {date}",
        )

    date_to_surprise: Dict[str, float] = {}

    for row_date, row in eps_data.iterrows():
        logger.info(f"Processing EPS data for {ticker} on {row_date}")
        logger.info(f"Row data: {row}")
        trailing_eps = row.get("epsActual")
        forward_eps = row.get("epsEstimate")
        logger.info(
            f"Processing EPS data for {ticker} on {row_date}: actual={trailing_eps}, estimate={forward_eps}"
        )
        if trailing_eps is None or forward_eps is None:
            continue
        surprise = get_surprise_for_date(
            db_conn, ticker, trailing_eps, forward_eps, str(row_date)
        )
        date_to_surprise[str(row_date)] = surprise

    if date is not None:
        return {"ticker": ticker, "surprise": {date: date_to_surprise.get(date)}}

    return {"ticker": ticker, "surprise": date_to_surprise}


async def fetch_reaction_for_ticker(
    request: Request, ticker: str, reaction_request: ReactionRequest = Depends()
):
    num_days = reaction_request.num_day_return
    threshold = reaction_request.threshold
    market_index = reaction_request.market_index
    filing_date = reaction_request.filing_date
    date = reaction_request.date

    surprise = await fetch_surprise_for_ticker(request, ticker, filing_date)
    valid_dates: List[str] = [
        date
        for date, surprise in surprise["surprise"].items()
        if surprise is not None and abs(surprise) >= threshold
    ]

    if len(valid_dates) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"the surprise value {surprise['surprise']} for ticker {ticker} is below the threshold of {threshold}, so reaction is not calculated",
        )

    db = cast(SQLiteDatabase, request.app.state.database)

    date_to_reaction_data: Dict[str, Dict[str, Any]] = {}

    for filing_date in valid_dates:
        try:
            reaction = get_reaction_for_date(
                db, ticker, num_days, market_index, filing_date, date
            )
            if reaction is None:
                continue

            date_to_reaction_data[filing_date] = {
                "reaction": reaction[filing_date],
                "surprise": surprise["surprise"][filing_date],
            }
        except HTTPException as e:
            logger.error(
                f"Error calculating reaction for {ticker} on {filing_date}: {e.detail}"
            )
            date_to_reaction_data[filing_date] = {
                "reaction": e.detail,
                "surprise": surprise["surprise"][filing_date],
            }

    return {
        "ticker": ticker,
        "reaction_data": date_to_reaction_data,
    }


async def fetch_proportionate_for_ticker(
    request: Request,
    ticker: str,
    proportionate_request: PropotionateRequest = Depends(),
):
    date = proportionate_request.date
    surprise = proportionate_request.surprise
    cumalative_reaction = proportionate_request.cumalative_reaction

    surprise_data = await fetch_surprise_for_ticker(request, ticker, date)
    ticker_sector = str(
        SP500_COMPANIES.loc[
            SP500_COMPANIES["Symbol"] == ticker, "GICS Sector"
        ].values.tolist()[0]
    )
    proportionality_data = get_ticker_proportionality_data(
        cast(SQLiteDatabase, request.app.state.database), ticker_sector
    )
    if proportionality_data is not None:
        surpirse_mean, surprise_sd, alpha, beta = proportionality_data

    all_companies_in_sector: List[str] = SP500_COMPANIES[
        SP500_COMPANIES["GICS Sector"] == ticker_sector
    ]["Symbol"].tolist()


def _normalize_earnings_history(
    df: pd.DataFrame,
) -> list[tuple[str, float | None, float | None]]:
    if df is None or df.empty:
        return []

    # Try common yfinance column variants
    cols = {c.lower(): c for c in df.columns}

    actual_col = None
    for key in (
        "epsactual",
        "eps_actual",
        "eps actual",
        "actual",
        "actualeps",
        "actual eps",
    ):
        if key in cols:
            actual_col = cols[key]
            break

    estimated_col = None
    for key in (
        "epsestimated",
        "eps_estimated",
        "eps estimate",
        "estimate",
        "epsconsensus",
        "consensus",
        "estimatedeps",
        "estimated eps",
    ):
        if key in cols:
            estimated_col = cols[key]
            break

    date_series = None
    for key in (
        "startdatetime",
        "start_date",
        "earningsdate",
        "earnings date",
        "date",
        "quarter",
        "quarterend",
        "quarter end",
    ):
        if key in cols:
            date_series = pd.to_datetime(df[cols[key]], errors="coerce")
            break
    if date_series is None:
        # Fallback: use index if it looks like datetimes
        try:
            date_series = pd.to_datetime(df.index, errors="coerce")
        except Exception:
            return []

    # Ensure a consistent, iloc-friendly type
    date_series = pd.Series(date_series)

    actual = pd.to_numeric(df[actual_col], errors="coerce") if actual_col else None
    estimated = (
        pd.to_numeric(df[estimated_col], errors="coerce") if estimated_col else None
    )

    rows: list[tuple[str, float | None, float | None]] = []
    for i in range(len(df)):
        dt = date_series.iloc[i]
        if pd.isna(dt):
            continue
        date_str = dt.strftime("%Y-%m-%d")
        eps_actual = (
            None
            if actual is None
            else (None if pd.isna(actual.iloc[i]) else float(actual.iloc[i]))
        )
        eps_estimated = (
            None
            if estimated is None
            else (None if pd.isna(estimated.iloc[i]) else float(estimated.iloc[i]))
        )
        rows.append((date_str, eps_actual, eps_estimated))

    return rows


async def populate_sp500_earnings_calendar(
    request: Request, batch_size: int = Query(default=10, ge=1, le=25)
):
    """Fetch S&P500 tickers' historical earnings (yfinance) and upsert into earnings_calendar."""
    from app.adapters.yf import get_earnings_history_of_ticker

    tickers = [str(x) for x in SP500_COMPANIES["Symbol"].tolist()]
    db_conn = cast(SQLiteDatabase, request.app.state.database)

    semaphore = asyncio.Semaphore(batch_size)
    inserted_rows = 0
    processed = 0
    succeeded = 0
    failed: list[str] = []

    async def fetch_one(t: str) -> tuple[str, pd.DataFrame | None]:
        async with semaphore:
            df = await asyncio.to_thread(get_earnings_history_of_ticker, t)
            return t, df

    tasks = [asyncio.create_task(fetch_one(t)) for t in tickers]
    for task in asyncio.as_completed(tasks):
        ticker, df = await task
        processed += 1
        if df is None or df.empty:  # type: ignore[truthy-bool]
            failed.append(ticker)
            continue

        normalized = _normalize_earnings_history(cast(pd.DataFrame, df))
        if not normalized:
            failed.append(ticker)
            continue

        normalized_rows = [(ticker, d, a, e) for (d, a, e) in normalized]
        upsert_earnings_calendar_rows(db_conn, normalized_rows)
        inserted_rows += len(normalized_rows)
        succeeded += 1

    return {
        "tickers_total": len(tickers),
        "tickers_processed": processed,
        "tickers_succeeded": succeeded,
        "tickers_failed": len(failed),
        "rows_upserted": inserted_rows,
        "failed_sample": failed[:25],
    }


async def ticker_pe(ticker: str):
    """Return current trailing and forward P/E ratios for a ticker."""
    trailing = get_current_pe_of_ticker(ticker)
    forward = get_current_forward_pe_of_ticker(ticker)

    if trailing is None and forward is None:
        raise HTTPException(status_code=404, detail=f"P/E data not found for {ticker}")

    return {"ticker": ticker, "pe": trailing, "forward_pe": forward}


async def ticker_last_earnings(ticker: str):
    """Return the last earnings call date for a ticker (YYYY-MM-DD)."""
    last = get_last_earnings_call_of_ticker(ticker)
    if last is None:
        raise HTTPException(
            status_code=404, detail=f"No earnings date found for {ticker}"
        )
    return {"ticker": ticker, "last_earnings_date": last}


async def ticker_history(ticker: str, start: str, end: str):
    """Return historical OHLCV data for a ticker between start and end dates.

    Dates must be in YYYY-MM-DD format.
    """
    try:
        df = await fetch_ticker_historical_prices(ticker, start, end)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching historical prices")

    # Convert Date to ISO string for JSON serialization
    df = df.copy()
    if "Date" in df.columns:
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    return {"ticker": ticker, "data": df.to_dict(orient="records")}
