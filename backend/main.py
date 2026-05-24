from backend.adapters import SP500_COMPANIES, get_earnings_history_of_ticker
from backend.logger import get_configured_logger
from backend.model import (
    FilingReactionData,
    PropotionateRequest,
    ReactionRequest,
    SurpriseEndpointResponse,
    ReactionEndpointResponse,
)
from backend.sql_functions import (
    DateValues,
    SQLiteDatabase,
    get_ticker_proportionality_data,
    get_ticker_reaction,
    get_ticker_surprise,
    ticker_in_db,
    upsert_proportionality_model,
)
from backend.helper_functions import (
    get_reaction_for_date,
    get_surprise_for_date,
    normalize_date_str,
    normalize_x,
)

logger = get_configured_logger(__name__)

import asyncio
import numpy as np
from typing import Dict, List
from fastapi import HTTPException


async def _compute_proportionality_model_for_ticker(
    db: SQLiteDatabase,
    sector: str,
    tickers: list[str],
):
    Y = {"2025-09-30": [], "2025-12-31": [], "2026-03-31": []}
    unnormalized_x = {"2025-09-30": [], "2025-12-31": [], "2026-03-31": []}
    logger.info(f"Computing proportionality model for sector {sector} with tickers: {tickers}")
    reaction_results = await asyncio.gather(
        *[
            fetch_reaction_for_ticker(
                db,
                ticker,
                ReactionRequest(reaction_days_threshold=3, surprise_threshold=0),
            )
            for ticker in tickers
        ]
    )

    for reaction_data in reaction_results:
        for filing_date, filing_reaction_data in reaction_data["reaction_data"].items():
            if isinstance(filing_reaction_data["reaction"], str):
                continue
            filing_date_norm = normalize_date_str(filing_date)
            latest_reaction_key = sorted(filing_reaction_data["reaction"].keys())[-1]
            latest_reaction_val = filing_reaction_data["reaction"][latest_reaction_key]
            surprise = filing_reaction_data["surprise"]

            for target_date in Y.keys():
                if target_date <= filing_date_norm:
                    continue
                unnormalized_x[target_date].append(float(surprise))
                Y[target_date].append(float(latest_reaction_val))

    model_dict: DateValues[tuple[float, float, float, float]] = {}
    for date in Y.keys():
        normalized_x, x_mean, x_sd = normalize_x(unnormalized_x[date])
        filing_y = np.array(Y[date], dtype=np.float64)
        beta, alpha = np.polyfit(normalized_x, filing_y, deg=1)

        logger.info(
            f"Proportionality model for sector {sector} on date {date}: "
            f"alpha={alpha}, beta={beta}, x_mean={x_mean}, x_sd={x_sd}, num_samples={len(filing_y)}"
        )
        upsert_proportionality_model(db, sector, date, x_mean, x_sd, alpha, beta)
        model_dict[date] = (x_mean, x_sd, alpha, beta)

    return model_dict


async def health_check():
    return {"status": "ok"}


async def fetch_surprise_for_ticker(
    db: SQLiteDatabase, ticker: str, filing_date: str | None
) -> SurpriseEndpointResponse:

    if filing_date is not None:
        filing_date = normalize_date_str(filing_date)

    surprise = get_ticker_surprise(db, ticker, filing_date)
    logger.info(f"Fetched surprise for {ticker} on {filing_date}: {surprise}")
    if surprise is not None:
        logger.info(
            f"Surprise data found in database for {ticker} on {filing_date}, returning cached value"
        )
        return {"ticker": ticker, "surprise": surprise}

    if ticker_in_db(db, ticker) is True:
        raise HTTPException(
            status_code=404,
            detail=f"surprise data not found for ticker {ticker} on date {filing_date}, even though the ticker exists in the database, likely means that the date is not supported for this ticker",
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
            detail=f"EPS data incomplete for ticker {ticker} on {filing_date}",
        )

    date_to_surprise: Dict[str, float] = {}

    for row_date, row in eps_data.iterrows():
        logger.info(f"Processing EPS data for {ticker} on {row_date}")
        logger.info(f"Row data: {row.to_dict()}")
        trailing_eps = row.get("epsActual")
        forward_eps = row.get("epsEstimate")
        logger.info(
            f"Processing EPS data for {ticker} on {row_date}: actual={trailing_eps}, estimate={forward_eps}"
        )
        if trailing_eps is None or forward_eps is None:
            continue

        normalized_row_date = normalize_date_str(str(row_date))
        surprise = get_surprise_for_date(
            db, ticker, trailing_eps, forward_eps, normalized_row_date
        )
        date_to_surprise[normalized_row_date] = surprise

    if filing_date is not None:
        return {
            "ticker": ticker,
            "surprise": {filing_date: date_to_surprise[filing_date]},
        }

    return {"ticker": ticker, "surprise": date_to_surprise}


async def fetch_reaction_for_ticker(
    db: SQLiteDatabase, ticker: str, reaction_request: ReactionRequest
) -> ReactionEndpointResponse:
    surprise_threshold = reaction_request.surprise_threshold
    market_index = reaction_request.market_index

    filing_date = (
        normalize_date_str(reaction_request.filings_date)
        if reaction_request.filings_date is not None
        else None
    )
    reaction_date = (
        normalize_date_str(reaction_request.reaction_date)
        if reaction_request.reaction_date is not None
        else None
    )

    try:
        surprise = await fetch_surprise_for_ticker(db, ticker, filing_date)
        logger.info(f"Fetched surprise data for {ticker}: {surprise}")
    except HTTPException as e:
        logger.error(f"Error fetching surprise data for {ticker}: {e.detail}")
        raise

    valid_filings_date: List[str] = [
        date
        for date, surprise in surprise["surprise"].items()
        if surprise is not None and abs(surprise) >= surprise_threshold
    ]
    logger.info(
        f"Valid filing dates for {ticker} with surprise threshold {surprise_threshold}: {valid_filings_date}"
    )
    if len(valid_filings_date) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"the surprise value {surprise['surprise']} for ticker {ticker} is below the threshold of {surprise_threshold}, so reaction is not calculated",
        )

    date_to_reaction_data: Dict[str, FilingReactionData] = {}

    for filing_date in valid_filings_date:
        try:
            reaction = get_reaction_for_date(
                db,
                ticker,
                market_index,
                filing_date,
                reaction_date,
                reaction_request.reaction_days_threshold,
            )
            if reaction is None:
                continue

            logger.info(f"the reaction is {reaction}")

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


async def fetch_surprise_and_latest_reaction(
    db: SQLiteDatabase,
    ticker: str,
    filings_date: str,
):
    surprise_data = get_ticker_surprise(db, ticker, filings_date)
    reaction_data = get_ticker_reaction(db, ticker, filing_date=filings_date)

    if surprise_data is not None and reaction_data is not None and filings_date in surprise_data and filings_date in reaction_data:
        latest_reaction_key = sorted(reaction_data[filings_date].keys())[-1]
        return surprise_data[filings_date], reaction_data[filings_date][latest_reaction_key]

    surprise_reaction_data = await fetch_reaction_for_ticker(
        db,
        ticker,
        ReactionRequest(
            reaction_days_threshold=3,
            surprise_threshold=0,
        ),
    )
    surprise_reaction_map = surprise_reaction_data["reaction_data"]
    if filings_date not in surprise_reaction_map:
        raise HTTPException(
            status_code=404,
            detail=f"surprise data not available for {ticker} on filings_date {filings_date} or the provided filings_date is not correct",
        )
    surprise_reaction = surprise_reaction_map[filings_date]
    if isinstance(surprise_reaction["reaction"], str):
        raise HTTPException(
            status_code=400,
            detail=f"reaction data for {ticker} on filings_date {filings_date} is not sufficient to compute proportionality, reason: {surprise_reaction['reaction']}",
        )
    sorted_dates = sorted(surprise_reaction_map.keys())
    if filings_date == sorted_dates[0]:
        raise HTTPException(
            status_code=400,
            detail=f"Filings date {filings_date} for ticker {ticker} is the earliest available date in the database, therefore no model can be made for it",
        )
    surprise_value = surprise_reaction["surprise"]
    reaction_value = surprise_reaction["reaction"][sorted_dates[-1]]

    return surprise_value, reaction_value


async def fetch_proportionality_for_ticker(
    db: SQLiteDatabase,
    ticker: str,
    proportionate_request: PropotionateRequest,
):
    filings_date = (
        normalize_date_str(proportionate_request.filings_date)
        if proportionate_request.filings_date is not None
        else None
    )

    # Two modes supported (enforced by the Pydantic validator):
    # 1) `filings_date` provided -> compute surprise via the usual path and fetch reaction
    # 2) `surprise` and `cumalative_reaction` provided -> use the supplied values directly

    ticker_sector: str = SP500_COMPANIES[SP500_COMPANIES["Symbol"] == ticker][
        "GICS Sector"
    ].values[0]

    proportionality_data = get_ticker_proportionality_data(
        db, ticker_sector, filings_date
    )

    if proportionality_data is None:
        all_companies_in_sector: List[str] = SP500_COMPANIES[
            SP500_COMPANIES["GICS Sector"] == ticker_sector
        ]["Symbol"].tolist()
        proportionality_data = await _compute_proportionality_model_for_ticker(
            db, ticker_sector, all_companies_in_sector
        )

    valid_dates = (
        [filings_date]
        if filings_date is not None
        else list(proportionality_data.keys())
    )

    pct_diff_dict: DateValues[Dict[str, float]] = {}
    for date in valid_dates:
        actual_surprise, actual_CAR = (
            await fetch_surprise_and_latest_reaction(db, ticker, date)
            if filings_date is not None
            else (
                float(proportionate_request.surprise), # type: ignore
                float(proportionate_request.cumalative_reaction), # type: ignore
            )
        )

        surpirse_mean, surprise_sd, alpha, beta = proportionality_data[date]
        surprise_z_score = (actual_surprise - surpirse_mean) / (surprise_sd + 1e-9)
        expected_CAR = alpha + beta * surprise_z_score

        logger.info(
            f"Computed proportionality for {ticker}: expected_CAR={expected_CAR}, actual_CAR={actual_CAR}"
        )
        pct_diff_dict[date] = {
            "pct_diff_from_expected": (actual_CAR - expected_CAR) / expected_CAR,
            "expected_CAR": expected_CAR,
            "actual_CAR": actual_CAR,
        }

    return pct_diff_dict
