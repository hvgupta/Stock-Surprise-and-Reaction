from .sbac import get_sbac

from backend.adapters import SP500_COMPANIES, get_1d_return_of_ticker
from backend.logger import get_configured_logger
from backend.model import (
    FilingReactionData,
    GeneratedProportionalityLinePoint,
    GeneratedProportionalityPlotResponse,
    GeneratedProportionalityPoint,
    PropotionateRequest,
    ProportionalityResponseEntry,
    ReactionRequest,
    ReactionEndpointResponse,
    SurpriseEndpointResponse,
)
from backend.db_functions.supabase import (
    AsyncClient,
    get_ticker_surprise,
    get_ticker_reaction,
    get_ticker_propotionality_data,
    DateValues,
    get_sp500_latest_surprises,
    get_model_data_points,
)

from backend.helper_functions import (
    get_reaction_for_date,
    normalize_date_str,
)

from typing import cast

logger = get_configured_logger(__name__)

from datetime import datetime
from typing import Dict, List, cast
from fastapi import HTTPException, APIRouter, Depends, Path, Query, Request, Path
# from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


reader_router = APIRouter(prefix="", tags=["reader"])


# def _sector_dir_name(sector: str) -> str:
#     return sector.replace("/", "_")


# def _latest_entry(values: Dict[str, float]) -> tuple[str, float]:
#     latest_key = sorted(values.keys())[-1]
#     return latest_key, float(values[latest_key])


# def _company_details(ticker: str) -> tuple[str, str]:
#     company_rows = SP500_COMPANIES[SP500_COMPANIES["Symbol"] == ticker]
#     if len(company_rows) == 0:
#         raise HTTPException(
#             status_code=404,
#             detail=f"ticker {ticker} not found in S&P 500 list",
#         )

#     company_name = str(company_rows["Security"].values[0])
#     sector = str(company_rows["GICS Sector"].values[0])
#     return company_name, sector


@reader_router.get("/generated_plots/proportionality/data")
async def fetch_generated_proportionality_plot_data(
    sbac: AsyncClient = Depends(get_sbac),
    sector: str = Query(...),
    filing_date: str = Query(...),
) -> GeneratedProportionalityPlotResponse:
    data_points = await get_model_data_points(sbac, sector, filing_date)
    if data_points is None:
        raise HTTPException(
            status_code=404,
            detail=f"No proportionality model data found for sector {sector} on filing date {filing_date}",
        )
    proportionality_data = await get_ticker_propotionality_data(
        sbac, sector, filing_date
    )
    if proportionality_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No proportionality model found for sector {sector} on filing date {filing_date}",
        )
    x_mean, x_sd, alpha, beta = proportionality_data[filing_date]
    return {
        "sector": sector,
        "filing_date": filing_date,
        "x_mean": x_mean,
        "x_sd": x_sd,
        "alpha": alpha,
        "beta": beta,
        "points": cast(List[GeneratedProportionalityPoint], data_points["points"]),
        "outliers": cast(List[GeneratedProportionalityPoint], data_points["outliers"]),
        "line_points": cast(
            List[GeneratedProportionalityLinePoint], data_points["line_points"]
        ),
    }


@reader_router.get("/{ticker}/surprise")
async def fetch_surprise_for_ticker(
    sbac: AsyncClient = Depends(get_sbac),
    ticker: str = Path(),
    filing_date: str | None = Query(default=None)
) -> SurpriseEndpointResponse:
    logger.info(f"Received request for surprise data for ticker {ticker} on filing date {filing_date}")
    if filing_date is not None:
        filing_date = normalize_date_str(filing_date)

    surprise = await get_ticker_surprise(sbac, ticker, filing_date)
    logger.info(f"Fetched surprise for {ticker} on {filing_date}: {surprise}")
    if surprise is None:
        raise HTTPException(
            status_code=404,
            detail=f"surprise data not found for ticker {ticker} on {filing_date}",
        )
    # if surprise is not None:
    logger.info(
        f"Surprise data found in database for {ticker} on {filing_date}, returning cached value"
    )
    return {"ticker": ticker, "surprise": surprise}

    # eps_data = get_earnings_history_of_ticker(ticker)
    # if eps_data is None:
    #     raise HTTPException(
    #         status_code=404,
    #         detail=f"the ticker {ticker} is not supported, check the /supported_tickers endpoint for the list of supported tickers",
    #     )

    # if len(eps_data) == 0:
    #     raise HTTPException(
    #         status_code=404,
    #         detail=f"EPS data incomplete for ticker {ticker} on {filing_date}",
    #     )

    # date_to_surprise: Dict[str, float] = {}

    # for row_date, row in eps_data.iterrows():
    #     logger.info(f"Processing EPS data for {ticker} on {row_date}")
    #     logger.info(f"Row data: {row.to_dict()}")
    #     trailing_eps = row.get("epsActual")
    #     forward_eps = row.get("epsEstimate")
    #     logger.info(
    #         f"Processing EPS data for {ticker} on {row_date}: actual={trailing_eps}, estimate={forward_eps}"
    #     )
    #     if trailing_eps is None or forward_eps is None:
    #         continue

    #     normalized_row_date = normalize_date_str(str(row_date))
    #     surprise = get_surprise_for_date(
    #         db, ticker, trailing_eps, forward_eps, normalized_row_date
    #     )
    #     date_to_surprise[normalized_row_date] = surprise

    # if filing_date is not None:
    #     return {
    #         "ticker": ticker,
    #         "surprise": {filing_date: date_to_surprise[filing_date]},
    #     }

    # return {"ticker": ticker, "surprise": date_to_surprise}


@reader_router.get("/{ticker}/reaction")
async def fetch_reaction_for_ticker(
    sbac: AsyncClient = Depends(get_sbac),
    ticker: str = Path(),
    reaction_request: ReactionRequest = Query(...)
) -> ReactionEndpointResponse:
    surprise_threshold = reaction_request.surprise_threshold
    threshold_reaction_days = reaction_request.reaction_days_threshold

    filings_date = (
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
        surprise = await fetch_surprise_for_ticker(sbac, ticker, filings_date)
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

    for filings_date in valid_filings_date:
        reaction = await get_reaction_for_date(
            sbac,
            ticker,
            filings_date,
            reaction_date,
            reaction_request.reaction_days_threshold,
        )
        if reaction is None:
            continue

        logger.info(f"the reaction is {reaction}")

        # Build market cumulative returns series aligned to the reaction dates
        market_map: Dict[str, float] = {}
        try:
            sorted_dates = sorted(reaction[filings_date].keys())
            cumulative_market = 0.0
            for d in sorted_dates[:threshold_reaction_days]:
                # one-day return for the market index on this date
                dt = datetime.strptime(d, "%Y-%m-%d")
                m_ret = get_1d_return_of_ticker("SPY", dt)
                if m_ret is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"could not fetch 1-day return for market index SPY on {dt}, cannot calculate market cumulative returns",
                    )
                cumulative_market += m_ret
                market_map[d] = cumulative_market
        except Exception:
            market_map = {}
        date_to_reaction_data[filings_date] = {
            "reaction": {k:v for i, (k,v) in enumerate(reaction[filings_date].items()) if i < threshold_reaction_days},
            "surprise": surprise["surprise"][filings_date],
            "market": market_map,
        }

    return {
        "ticker": ticker,
        "reaction_data": date_to_reaction_data,
    }


async def _fetch_surprise_and_latest_reaction(
    sbac: AsyncClient,
    ticker: str,
    filings_date: str,
):
    surprise_data = await get_ticker_surprise(sbac, ticker, filings_date)
    reaction_data = await get_ticker_reaction(sbac, ticker, filings_date=filings_date)

    if (
        surprise_data is not None
        and reaction_data is not None
        and filings_date in surprise_data
        and filings_date in reaction_data
    ):
        latest_reaction_key = sorted(reaction_data[filings_date].keys())[-1]
        return (
            surprise_data[filings_date],
            reaction_data[filings_date][latest_reaction_key],
        )

    surprise_reaction_data = await fetch_reaction_for_ticker(
        sbac,
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


@reader_router.get("/{ticker}/proportionate")
async def fetch_proportionality_for_ticker(
    sbac: AsyncClient = Depends(get_sbac),
    ticker: str = Path(),
    proportionate_request: PropotionateRequest = Query(...),
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
    ].values[0] # type: ignore 

    proportionality_data = await get_ticker_propotionality_data(
        sbac, ticker_sector, filings_date
    )
    if proportionality_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No proportionality model found for sector {ticker_sector} on filing date {filings_date}",
        )

    # if proportionality_data is None:
    #     all_companies_in_sector: List[str] = SP500_COMPANIES[
    #         SP500_COMPANIES["GICS Sector"] == ticker_sector
    #     ]["Symbol"].tolist()
    #     proportionality_data = await _compute_proportionality_model_for_ticker(
    #         sbac, ticker_sector, all_companies_in_sector
    #     )

    valid_dates = (
        [filings_date]
        if filings_date is not None
        else list(proportionality_data.keys())
    )

    pct_diff_dict: DateValues[ProportionalityResponseEntry] = {}
    for date in valid_dates:
        actual_surprise, actual_CAR = (
            await _fetch_surprise_and_latest_reaction(sbac, ticker, date)
            if filings_date is not None
            else (
                float(proportionate_request.surprise),  # type: ignore
                float(proportionate_request.cumalative_reaction),  # type: ignore
            )
        )

        surpirse_mean, surprise_sd, alpha, beta = proportionality_data[date]
        surprise_z_score = (actual_surprise - surpirse_mean) / (surprise_sd + 1e-9)
        expected_CAR = alpha + beta * surprise_z_score

        logger.info(
            f"Computed proportionality for {ticker}: expected_CAR={expected_CAR}, actual_CAR={actual_CAR}"
        )
        pct_diff_dict[date] = {
            "pct_diff": (actual_CAR - expected_CAR),
            "expected_CAR": expected_CAR,
            "actual_CAR": actual_CAR,
            "regression_model": {
                "surprise_mean": float(surpirse_mean),
                "surprise_sd": float(surprise_sd),
                "alpha": float(alpha),
                "beta": float(beta),
            },
        }

    return pct_diff_dict


# async def _build_snapshot_for_ticker(
#     sbac: AsyncClient,
#     ticker: str,
#     semaphore: asyncio.Semaphore,
# ) -> SP500TickerSnapshot | None:
#     async with semaphore:
#         try:
#             surprise_payload = await _fetch_surprise_for_ticker(
#                 sbac, ticker, filing_date=None
#             )
#             if len(surprise_payload["surprise"]) == 0:
#                 return None

#             filing_date, surprise = _latest_entry(surprise_payload["surprise"])
#             company_name, sector = _company_details(ticker)
#             return {
#                 "ticker": ticker,
#                 "company_name": company_name,
#                 "sector": sector,
#                 "filing_date": filing_date,
#                 "surprise": surprise,
#             }
#         except Exception as exc:
#             logger.warning(f"Skipping ticker {ticker}; unable to build snapshot: {exc}")
#             return None


@reader_router.get("/sp500/surprises")
async def fetch_sp500_surprises(sbac: AsyncClient = Depends(get_sbac)):
    resp = await get_sp500_latest_surprises(sbac)
    if resp is None:
        raise HTTPException(
            status_code=404,
            detail="could not fetch latest surprises for S&P 500 companies",
        )
    return {
        "count": len(resp),
        "items": [
            {
                "ticker": row["symbol"],
                "company_name": SP500_COMPANIES[SP500_COMPANIES["Symbol"] == row["symbol"]]["Security"].values[0],
                "sector": SP500_COMPANIES[SP500_COMPANIES["Symbol"] == row["symbol"]]["GICS Sector"].values[0],
                "filings_date": row["filings_date"],
                "surprise": row["surprise"],
                "latest_reaction": row["reaction"]
            } for row in resp if isinstance(row, Dict)
        ]
    }
