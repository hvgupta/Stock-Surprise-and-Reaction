from .sbac import get_sbac
from .reader import fetch_reaction_for_ticker

from backend.supabase import (
    AsyncClient,
    DateValues,
    insert_model_data_points,
    insert_proportionality_model,
)
from backend.model import (
    ReactionRequest,
    GeneratedProportionalityLinePoint,
    GeneratedProportionalityPoint,
)
from backend.logger import get_configured_logger
from backend.adapters import SP500_COMPANIES
from backend.helper_functions import normalize_date_str, normalize_x

logger = get_configured_logger(__name__)

import os
import dotenv
import asyncio
import numpy as np
from fastapi import APIRouter, Path, Depends, HTTPException, Request

dotenv.load_dotenv(override=True)


def get_admin_sbac(request: Request):
    if os.getenv("SUPABASE_ADMIN_API_KEY") is None:
        raise HTTPException(
            401,
            "ADMIN key is not provided, so the writing operations are not permitted",
        )
    return get_sbac(request)


writer_router = APIRouter(prefix="/admin", tags=["admin", "writer"])


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

@writer_router.post("/{sector}/proportionality")
async def compute_proportionality_model_for_ticker(
    sbac: AsyncClient = Depends(get_admin_sbac),
    sector: str = Path(),
):
    tickers = SP500_COMPANIES[SP500_COMPANIES["GICS Sector"] == sector]["Symbol"].tolist()
    Y = {"2025-09-30": [], "2025-12-31": [], "2026-03-31": []}
    unnormalized_x = {"2025-09-30": [], "2025-12-31": [], "2026-03-31": []}
    logger.info(
        f"Computing proportionality model for sector {sector} with tickers: {tickers}"
    )
    reaction_results = await asyncio.gather(
        *[
            fetch_reaction_for_ticker(
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

        await insert_proportionality_model(sbac, sector, date, x_mean, x_sd, alpha, beta)

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
        await insert_model_data_points(
            sbac,
            sector,
            date,
            {
                "points": points,
                "outliers": outliers,
                "line_points": line_points,
            },
        )

    return model_dict
