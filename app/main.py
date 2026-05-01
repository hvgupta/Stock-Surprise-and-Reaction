from app.adapters import (
    SP500_COMPANIES,
    fetch_ticker_historical_prices,
    get_current_forward_pe_of_ticker,
    get_current_pe_of_ticker,
    get_earnings_history_of_ticker,
    get_last_earnings_call_of_ticker,
)
from app.logger import get_configured_logger
from app.model import PropotionateRequest, ReactionRequest, SurpriseEndpointResponse
from app.sql_functions import (
    SQLiteDatabase,
    get_all_supported_tickers,
    get_dates_of_ticker,
    get_ticker_proportionality_data,
    get_ticker_reaction,
    get_ticker_surprise,
    ticker_in_db,
    upsert_proportionality_model,
)
from app.helper_functions import (
    get_reaction_for_date,
    get_surprise_for_date,
    normalize_date_str,
)

logger = get_configured_logger(__name__)

from typing import Dict, List, Any, cast
from fastapi import Depends, HTTPException, Query, Request
import numpy as np


async def _compute_sector_proportionality_model(
    request: Request,
    sector: str,
    tickers: list[str],
    *,
    max_pairs: int = 60,
    min_pairs: int = 12,
    max_tickers_to_fetch: int = 20,
    max_filings_per_ticker: int = 6,
) -> tuple[float, float, float, float]:
    """Compute (mean_surprise, sd_surprise, alpha, beta) for a sector.

    Uses cached DB data where possible; if insufficient points, fetches a limited
    number of tickers from yfinance to seed data.
    """

    db = cast(SQLiteDatabase, request.app.state.database)

    pairs: list[tuple[float, float]] = []

    async def _add_cached_pairs_for_ticker(ticker: str) -> None:
        nonlocal pairs
        try:
            surprise_resp = await fetch_surprise_for_ticker(request, ticker, None)
        except Exception as e:
            logger.error(f"Error fetching surprise for {ticker}: {e}")
            return

        surprise_data = surprise_resp.get("surprise") if isinstance(surprise_resp, dict) else None
        if not isinstance(surprise_data, dict) or not surprise_data:
            return

        for filing_date, surprise_val in surprise_data.items():
            if surprise_val is None:
                continue
            filing_date_norm = normalize_date_str(str(filing_date))

            # Use the existing reaction endpoint logic to compute/retrieve reaction
            try:
                reaction_resp = await fetch_reaction_for_ticker(
                    request,
                    ticker,
                    ReactionRequest(
                        num_day_return=3,
                        market_index="SPY",
                        threshold=0.0,
                        filings_date=filing_date_norm,
                        date=None,
                    ),
                )
            except Exception:
                continue

            reaction_data = reaction_resp.get("reaction_data") if isinstance(reaction_resp, dict) else None
            if not isinstance(reaction_data, dict):
                continue

            filing_entry = reaction_data.get(filing_date_norm)
            if filing_entry is None:
                continue

            reaction_series = filing_entry.get("reaction")
            car_val = None
            if isinstance(reaction_series, dict):
                last_date = sorted(reaction_series.keys())[-1]
                car_val = reaction_series.get(last_date)
            elif isinstance(reaction_series, (int, float)):
                car_val = reaction_series

            if isinstance(car_val, (int, float)):
                pairs.append((float(surprise_val), float(car_val)))
            if len(pairs) >= max_pairs:
                return

    for ticker in tickers:
        await _add_cached_pairs_for_ticker(ticker)
        if len(pairs) >= max_pairs:
            break

    if len(pairs) < min_pairs:
        tickers_fetched = 0
        for ticker in tickers:
            if tickers_fetched >= max_tickers_to_fetch or len(pairs) >= max_pairs:
                break

            eps_data = get_earnings_history_of_ticker(ticker)
            if eps_data is None or eps_data.empty:  # type: ignore[attr-defined]
                continue

            tickers_fetched += 1
            filings_seen = 0
            for row_date, row in eps_data.iterrows():
                if filings_seen >= max_filings_per_ticker or len(pairs) >= max_pairs:
                    break

                trailing_eps = row.get("epsActual")
                forward_eps = row.get("epsEstimate")
                if trailing_eps is None or forward_eps is None:
                    continue

                filing_date_norm = normalize_date_str(str(row_date))
                surprise_val = get_surprise_for_date(
                    db,
                    ticker,
                    float(trailing_eps),
                    float(forward_eps),
                    filing_date_norm,
                )
                reaction = get_reaction_for_date(
                    db,
                    ticker,
                    3,
                    "SPY",
                    filing_date_norm,
                    None,
                )
                if reaction is None:
                    continue

                series = reaction.get(filing_date_norm) or {}
                if not series:
                    continue

                last_date = sorted(series.keys())[-1]
                car_val = series[last_date]
                if isinstance(car_val, (int, float)):
                    pairs.append((float(surprise_val), float(car_val)))
                    filings_seen += 1

    if len(pairs) < min_pairs:
        raise HTTPException(
            status_code=404,
            detail=(
                f"insufficient data to fit proportionality model for sector {sector} "
                f"(need >= {min_pairs} samples, got {len(pairs)})"
            ),
        )

    surprises = [s for s, _ in pairs]
    cars = [c for _, c in pairs]

    surprises_arr = np.array(surprises, dtype=np.float64)
    cars_arr = np.array(cars, dtype=np.float64)

    mean_surprise = float(np.mean(surprises_arr))
    sd_surprise = float(np.std(surprises_arr, ddof=0))
    if sd_surprise < 1e-12:
        sd_surprise = 1e-12

    z_scores = (surprises_arr - mean_surprise) / sd_surprise
    beta, alpha = np.polyfit(z_scores, cars_arr, deg=1)
    return (mean_surprise, sd_surprise, alpha, beta)


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
) -> SurpriseEndpointResponse:
    db_conn = cast(SQLiteDatabase, request.app.state.database)

    if date is not None:
        date = normalize_date_str(date)

    surprise = get_ticker_surprise(db_conn, ticker, date)
    logger.info(f"Fetched surprise for {ticker} on {date}: {surprise}")
    if surprise is not None:
        logger.info(
            f"Surprise data found in database for {ticker} on {date}, returning cached value"
        )
        return {
            "ticker": ticker,
            "surprise": (
                surprise if isinstance(surprise, Dict) else {str(date): float(surprise)}
            ),
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

        normalized_row_date = normalize_date_str(str(row_date))
        surprise = get_surprise_for_date(
            db_conn, ticker, trailing_eps, forward_eps, normalized_row_date
        )
        date_to_surprise[normalized_row_date] = surprise

    if date is not None:
        return {"ticker": ticker, "surprise": {date: date_to_surprise[date]}}

    return {"ticker": ticker, "surprise": date_to_surprise}


async def fetch_reaction_for_ticker(
    request: Request, ticker: str, reaction_request: ReactionRequest = Depends()
):
    num_days = reaction_request.num_day_return
    threshold = reaction_request.threshold
    market_index = reaction_request.market_index
    filing_date = (
        normalize_date_str(reaction_request.filings_date)
        if reaction_request.filings_date is not None
        else None
    )
    date = (
        normalize_date_str(reaction_request.date)
        if reaction_request.date is not None
        else None
    )

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
    filings_date = (
        normalize_date_str(proportionate_request.filings_date)
        if proportionate_request.filings_date is not None
        else None
    )
    date = (
        normalize_date_str(proportionate_request.date)
        if proportionate_request.date is not None
        else None
    )

    # Two modes supported (enforced by the Pydantic validator):
    # 1) `filings_date` provided -> compute surprise via the usual path and fetch reaction
    # 2) `surprise` and `cumalative_reaction` provided -> use the supplied values directly

    if filings_date is not None:
        surprise_data = await fetch_surprise_for_ticker(request, ticker, filings_date)
        surprise_map = surprise_data.get("surprise") if isinstance(surprise_data, dict) else None
        if not isinstance(surprise_map, dict) or filings_date not in surprise_map:
            raise HTTPException(
                status_code=404,
                detail=f"surprise data not available for {ticker} on filings_date {filings_date}",
            )
        surprise_value = float(surprise_map[filings_date])
    else:
        # Validator guarantees these are present when filings_date is missing
        surprise_value = float(proportionate_request.surprise)  # type: ignore[arg-type]

    ticker_sector: str = SP500_COMPANIES[SP500_COMPANIES["Symbol"] == ticker][
        "GICS Sector"
    ].values[0]
    proportionality_data = get_ticker_proportionality_data(
        cast(SQLiteDatabase, request.app.state.database), ticker_sector
    )
    if proportionality_data is None:
        all_companies_in_sector: List[str] = SP500_COMPANIES[
            SP500_COMPANIES["GICS Sector"] == ticker_sector
        ]["Symbol"].tolist()
        db = cast(SQLiteDatabase, request.app.state.database)
        mean_surp, sd_surp, alpha, beta = await _compute_sector_proportionality_model(
            request, ticker_sector, all_companies_in_sector
        )
        upsert_proportionality_model(db, ticker_sector, mean_surp, sd_surp, alpha, beta)
        proportionality_data = (mean_surp, sd_surp, alpha, beta)

    surpirse_mean, surprise_sd, alpha, beta = proportionality_data
    surprise_z_score = (surprise_value - surpirse_mean) / (surprise_sd + 1e-9)
    expected_CAR = alpha + beta * surprise_z_score

    if filings_date is not None:
        reaction_response = await fetch_reaction_for_ticker(
            request,
            ticker,
            ReactionRequest(
                num_day_return=3,
                market_index="SPY",
                threshold=0.0,
                filings_date=filings_date,
                date=date,
            ),
        )

        filing_entry = reaction_response["reaction_data"].get(filings_date)
        if filing_entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"reaction data not available for {ticker} on filings_date {filings_date}",
            )

        reaction_series = filing_entry.get("reaction")
        if isinstance(reaction_series, dict):
            if date is not None:
                if date not in reaction_series:
                    raise HTTPException(
                        status_code=404,
                        detail=f"reaction not available for {ticker} on {date} (filings_date={filings_date})",
                    )
                actual_CAR = float(reaction_series[date])
            else:
                last_date = sorted(reaction_series.keys())[-1]
                actual_CAR = float(reaction_series[last_date])
        elif isinstance(reaction_series, (int, float)):
            actual_CAR = float(reaction_series)
        else:
            raise HTTPException(
                status_code=500,
                detail="unexpected reaction data format",
            )
    else:
        # Use supplied cumulative reaction
        actual_CAR = float(proportionate_request.cumalative_reaction)  # type: ignore[arg-type]

    pct_diff_from_expected = (
        None
        if abs(expected_CAR) < 1e-12
        else (actual_CAR - expected_CAR) / expected_CAR
    )

    return {
        "pct_diff_from_expected": pct_diff_from_expected,
        "expected_CAR": expected_CAR,
        "actual_CAR": actual_CAR,
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
