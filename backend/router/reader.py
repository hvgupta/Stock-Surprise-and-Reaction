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
    SP500SurprisesResponse,
    SP500TickerSnapshot,
    SurpriseEndpointResponse,
)
from backend.supabase import (
    AsyncClient,
    get_ticker_surprise,
    get_ticker_reaction,
    get_ticker_propotionality_data,
    DateValues,
    get_sp500_latest_surprises
)

from backend.helper_functions import (
    get_reaction_for_date,
    normalize_date_str,
    normalize_x,
)

logger = get_configured_logger(__name__)

import asyncio
import json
import numpy as np
from typing import Dict, List, cast
from fastapi import HTTPException, APIRouter, Query
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PLOT_OUTPUT_DIR = (
    Path(__file__).resolve().parent / "generated_plots" / "proportionality"
)


reader_router = APIRouter(prefix="", tags=["reader"])

def _sector_dir_name(sector: str) -> str:
    return sector.replace("/", "_")


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


def _filter_outliers_iqr(
    x_values: np.ndarray,
) -> np.ndarray:
    if len(x_values) < 4:
        return np.ones(len(x_values), dtype=bool)

    x_q1, x_q3 = np.percentile(x_values, [25, 75])

    x_iqr = x_q3 - x_q1

    if x_iqr <= 0:
        return np.ones(len(x_values), dtype=bool)

    x_mask = np.ones(len(x_values), dtype=bool)

    if x_iqr > 0:
        x_lower = x_q1 - 1.5 * x_iqr
        x_upper = x_q3 + 1.5 * x_iqr
        x_mask = (x_values >= x_lower) & (x_values <= x_upper)

    mask = x_mask
    if int(mask.sum()) < 2:
        return np.ones(len(x_values), dtype=bool)

    return mask


async def _compute_proportionality_model_for_ticker(
    sbac: AsyncClient,
    sector: str,
    tickers: list[str],
):
    Y = {"2025-09-30": [], "2025-12-31": [], "2026-03-31": []}
    unnormalized_x = {"2025-09-30": [], "2025-12-31": [], "2026-03-31": []}
    logger.info(
        f"Computing proportionality model for sector {sector} with tickers: {tickers}"
    )
    reaction_results = await asyncio.gather(
        *[
            _fetch_reaction_for_ticker(
                sbac,
                ticker,
                ReactionRequest(reaction_days_threshold=3, surprise_threshold=0),
            )
            for ticker in tickers
        ],
        return_exceptions=True,
    )

    for reaction_data in reaction_results:
        if isinstance(reaction_data, BaseException):
            logger.warning(
                f"Skipping a ticker due to error in fetching reaction data: {reaction_data}"
            )
            continue
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
        # perform outlier filtering on raw surprise values before normalization
        x_raw = np.array(unnormalized_x[date], dtype=np.float64)
        filing_y = np.array(Y[date], dtype=np.float64)

        fit_mask = _filter_outliers_iqr(filing_y)
        filtered_raw = x_raw[fit_mask]
        filtered_y = filing_y[fit_mask]

        # compute excluded (outlier) raw values for plotting and domain calculation
        excluded_raw = x_raw[~fit_mask]
        excluded_y = filing_y[~fit_mask]

        if len(filtered_raw) == 0:
            logger.warning(
                f"No inlier samples after filtering for sector {sector} on date {date}; skipping"
            )
            continue

        # normalize using only the filtered (inlier) raw surprises
        normalized_filtered_x, x_mean, x_sd = normalize_x(filtered_raw.tolist())
        beta, alpha = np.polyfit(normalized_filtered_x, filtered_y, deg=1)

        logger.info(
            f"Proportionality model for sector {sector} on date {date}: "
            f"alpha={alpha}, beta={beta}, x_mean={x_mean}, x_sd={x_sd}, num_samples={len(filing_y)}, filtered_samples={len(filtered_y)}"
        )
        # TODO:
        # upsert_proportionality_model(db, sector, date, x_mean, x_sd, alpha, beta)
        model_dict[date] = (x_mean, x_sd, alpha, beta)

        if len(unnormalized_x[date]) == 0:
            logger.warning(
                f"Skipping plot export for sector {sector} on date {date}: no samples available"
            )
            continue

        # compute z-scores for all raw values using the inlier mean/sd so excluded
        # points appear in the same normalized coordinate system as the fit
        if x_sd == 0:
            x_sd = 1e-9
        x_values = normalized_filtered_x
        y_values = filtered_y
        # compute excluded z-scores so the regression line spans the full plotted domain
        excluded_z: np.ndarray = np.array([])
        if len(excluded_raw) > 0:
            try:
                excluded_z = (excluded_raw - x_mean) / (x_sd if x_sd != 0 else 1e-9)
            except Exception:
                excluded_z = np.array([])

        all_z_values = (
            np.concatenate([x_values, excluded_z]) if excluded_z.size > 0 else x_values
        )
        x_min = float(np.min(all_z_values))
        x_max = float(np.max(all_z_values))
        if x_min == x_max:
            x_min -= 0.01
            x_max += 0.01

        x_line = np.linspace(x_min, x_max, 200)
        y_line = alpha + beta * x_line

        plot_dir = PLOT_OUTPUT_DIR / sector.replace("/", "_")
        plot_dir.mkdir(parents=True, exist_ok=True)
        plot_path = plot_dir / f"{date}.png"
        plot_data_path = plot_dir / f"{date}.json"

        fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
        ax.scatter(
            x_values,
            y_values,
            color="black",
            s=22,
            alpha=0.85,
            label="Data points",
        )
        ax.plot(x_line, y_line, color="red", linewidth=2.5, label="Regression line")
        ax.axhline(0, color="#9ca3af", linewidth=1, linestyle="--")
        ax.axvline(0, color="#9ca3af", linewidth=1, linestyle="--")
        ax.set_title(f"{sector} proportionality on {date}")
        ax.set_xlabel("Surprise z-score")
        ax.set_ylabel("CAR / Reaction")
        ax.legend(loc="best")
        ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.5)
        fig.tight_layout()
        fig.savefig(plot_path, bbox_inches="tight")
        plt.close(fig)

        points: list[GeneratedProportionalityPoint] = [
            {
                "z_score": float(z_val),
                "reaction": float(y_val),
            }
            for z_val, y_val in zip(x_values.tolist(), y_values.tolist())
        ]
        outliers: list[GeneratedProportionalityPoint] = [
            {
                "z_score": float((raw_val - x_mean) / x_sd),
                "reaction": float(y_val),
            }
            for raw_val, y_val in zip(excluded_raw.tolist(), excluded_y.tolist())
        ]
        line_points: list[GeneratedProportionalityLinePoint] = [
            {
                "z_score": float(z_val),
                "expected_reaction": float(y_val),
            }
            for z_val, y_val in zip(x_line.tolist(), y_line.tolist())
        ]

        plot_payload: GeneratedProportionalityPlotResponse = {
            "sector": sector,
            "filing_date": date,
            "alpha": float(alpha),
            "beta": float(beta),
            "x_mean": float(x_mean),
            "x_sd": float(x_sd),
            "points": points,
            "outliers": outliers,
            "line_points": line_points,
        }
        plot_data_path.write_text(json.dumps(plot_payload), encoding="utf-8")
        logger.info(f"Saved proportionality plot to {plot_path}")

    return model_dict


async def fetch_generated_proportionality_plot_data(
    sbac: AsyncClient,
    sector: str,
    filing_date: str,
) -> GeneratedProportionalityPlotResponse:
    normalized_filing_date = normalize_date_str(filing_date)
    data_path = (
        PLOT_OUTPUT_DIR / _sector_dir_name(sector) / f"{normalized_filing_date}.json"
    )
    if not data_path.exists():
        sector_tickers: list[str] = (
            SP500_COMPANIES[SP500_COMPANIES["GICS Sector"] == sector]["Symbol"]
            .dropna()
            .astype(str)
            .tolist()
        )

        if len(sector_tickers) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"sector {sector} not found in S&P 500 list",
            )

        logger.info(
            f"Generated plot data not found for sector {sector} on {normalized_filing_date}; computing on demand"
        )
        await _compute_proportionality_model_for_ticker(sbac, sector, sector_tickers)

    if not data_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"generated proportionality plot data not found for sector {sector} on {normalized_filing_date}",
        )

    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"failed to read generated proportionality plot data: {exc}",
        )

    if "outliers" not in payload:
        payload["outliers"] = []

    return payload

def get_sbac(router: APIRouter):
    _state = getattr(reader_router, "state", None)
    sbac = cast(AsyncClient, getattr(_state, "supabase_client")) if _state else None
    if sbac is None:
        raise HTTPException(
            status_code=500,
            detail="Supabase client not initialized",
        )
    return sbac

@reader_router.get("/{ticker}/surprise")
async def fetch_surprise_for_ticker(ticker: str, filing_date: str | None = Query(default=None)):
    sbac = get_sbac(reader_router)
    return await _fetch_surprise_for_ticker(sbac, ticker, filing_date)
async def _fetch_surprise_for_ticker(
    sbac: AsyncClient, ticker: str, filing_date: str | None
) -> SurpriseEndpointResponse:

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
async def fetch_reaction_for_ticker(ticker: str, reaction_request: ReactionRequest = Query(...)):
    sbac = get_sbac(reader_router)
    return await _fetch_reaction_for_ticker(sbac, ticker, reaction_request)
async def _fetch_reaction_for_ticker(
    sbac: AsyncClient, ticker: str, reaction_request: ReactionRequest
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
        surprise = await _fetch_surprise_for_ticker(sbac, ticker, filing_date)
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
            reaction = await get_reaction_for_date(
                sbac,
                ticker,
                filing_date,
                reaction_date,
                reaction_request.reaction_days_threshold,
            )
            if reaction is None:
                continue

            logger.info(f"the reaction is {reaction}")

            # Build market cumulative returns series aligned to the reaction dates
            market_map: Dict[str, float] = {}
            try:
                sorted_dates = sorted(reaction[filing_date].keys())
                cumulative_market = 0.0
                for d in sorted_dates:
                    # one-day return for the market index on this date
                    from datetime import datetime

                    dt = datetime.strptime(d, "%Y-%m-%d")
                    m_ret = get_1d_return_of_ticker(market_index, dt)
                    if m_ret is None:
                        raise HTTPException(
                            status_code=404,
                            detail=f"could not fetch 1-day return for market index {market_index} on {dt}, cannot calculate market cumulative returns",
                        )
                    cumulative_market += m_ret
                    market_map[d] = cumulative_market
            except Exception:
                market_map = {}

            date_to_reaction_data[filing_date] = {
                "reaction": reaction[filing_date],
                "surprise": surprise["surprise"][filing_date],
                "market": market_map,
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


async def _fetch_surprise_and_latest_reaction(
    sbac: AsyncClient,
    ticker: str,
    filings_date: str,
):
    surprise_data = await get_ticker_surprise(sbac, ticker, filings_date)
    reaction_data = await get_ticker_reaction(sbac, ticker, filing_date=filings_date)

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

    surprise_reaction_data = await _fetch_reaction_for_ticker(
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
async def fetch_proportionality_for_ticker(ticker: str, proportionate_request: PropotionateRequest = Query(...)):
    sbac = get_sbac(reader_router)
    return await _fetch_proportionality_for_ticker(sbac, ticker, proportionate_request)
async def _fetch_proportionality_for_ticker(
    sbac: AsyncClient,
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

    proportionality_data = await get_ticker_propotionality_data(
        sbac, ticker_sector, filings_date
    )

    if proportionality_data is None:
        all_companies_in_sector: List[str] = SP500_COMPANIES[
            SP500_COMPANIES["GICS Sector"] == ticker_sector
        ]["Symbol"].tolist()
        proportionality_data = await _compute_proportionality_model_for_ticker(
            sbac, ticker_sector, all_companies_in_sector
        )

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
            "pct_diff_from_expected": (actual_CAR - expected_CAR) / abs(expected_CAR),
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
async def fetch_sp500_surprises():
    sbac = get_sbac(reader_router)
    return await get_sp500_latest_surprises(sbac)