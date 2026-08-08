from .helper_functions import fyqrt_to_numeric, numeric_to_fyqrt
from .adapters import (
    TICKER_TO_CIK_MAP,
    fetch_sec_concepts,
    clean_period_table,
    conv_dict_to_df,
    get_ticker_price_data,
)

from backend.logger import get_configured_logger

logger = get_configured_logger(__name__)

import numpy as np
import pandas as pd
from datetime import timedelta, datetime
from typing import Dict, Any, List, Tuple, Callable, Optional

BACKFILL_DATES = ["2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31"]


def calc_surprise_of_ticker(trailing_eps: float, forward_eps: float) -> float:
    if trailing_eps == 0:
        return 0.0
    logger.debug(
        f"Calculating surprise for trailing_eps={trailing_eps}, forward_eps={forward_eps}"
    )
    surprise = (trailing_eps - forward_eps) / abs(forward_eps)
    return surprise


def calc_reaction_of_ticker(ticker_returns: float, market_returns: float) -> float:
    return ticker_returns - market_returns


async def calc_pre_event_drift(ticker: str):
    def single_calc(price_data: pd.DataFrame, default_col: str = "Close"):
        col_data = price_data[default_col]
        ratio_array = (col_data / col_data.shift()).dropna().values
        if not isinstance(ratio_array, np.ndarray):
            raise Exception

        mean, sd = ratio_array.mean(), ratio_array.std()

        return (mean / price_data.shape[0]) + (sd**2) / 2

    drift_data = {}
    for d in BACKFILL_DATES:
        one_month_back = (
            (datetime.strptime(d, "%Y-%m-%d") - timedelta(days=30))
            .date()
            .strftime("%Y-%m-%d")
        )
        price_data = get_ticker_price_data(ticker, one_month_back, d)
        if price_data is None:
            logger.error("price data is None")
            continue
        drift_data[d] = single_calc(price_data)

    return drift_data


async def calc_realized_volatility(ticker: str):
    def single_calc(price_data: pd.DataFrame, default_col: str = "Close"):
        col_data = price_data[default_col]
        ratio_array = (col_data / col_data.shift()).dropna().values
        ln_price_ratio = np.log(ratio_array)
        if not isinstance(ln_price_ratio, np.ndarray):
            raise Exception

        return ln_price_ratio.std()

    volatility_data = {}
    for d in BACKFILL_DATES:
        one_year_back = (
            (datetime.strptime(d, "%Y-%m-%d") - timedelta(days=365))
            .date()
            .strftime("%Y-%m-%d")
        )
        price_data = get_ticker_price_data(ticker, one_year_back, d)
        if price_data is None:
            logger.error("price data is None")
            continue
        volatility_data[d] = single_calc(price_data)

    return volatility_data


def get_cleaned_fact(
    concepts: Dict[str, Any],
    fact_keys: List[str],
    start_fyqrt: Tuple[int, str],
    end_fyqrt: Tuple[int, str],
    is_instant: bool = False,
):
    for fact_key in fact_keys:
        fact_df = conv_dict_to_df(concepts["facts"], fact_key, "USD")
        if fact_df.empty:
            logger.warning(f"skipping {fact_key=} because its fact_df was empty")
            continue
        cleaned_fact_df_data = clean_period_table(
            fact_df, start_fyqrt[0], end_fyqrt[0], "key_name", is_instant
        )
        check_for_fyqrt: Callable[[Tuple[int, str]], pd.DataFrame] = lambda fyqrt: (
            cleaned_fact_df_data[
                cleaned_fact_df_data["start"].dt.year
                + (cleaned_fact_df_data["fp"].str[1].astype(int) - 1) / 4
                == fyqrt[0] + ((int(end_fyqrt[1][1]) - 1) / 4)
            ]
        )
        if (
            not check_for_fyqrt(start_fyqrt).empty
            and not check_for_fyqrt(end_fyqrt).empty
        ):
            start_num = start_fyqrt[0] + ((int(start_fyqrt[1][1]) - 1) / 4)
            series_num = cleaned_fact_df_data["start"].dt.year + (
                (cleaned_fact_df_data["fp"].str[1].astype(int) - 1) / 4
            )
            end_num = end_fyqrt[0] + ((int(end_fyqrt[1][1]) - 1) / 4)

            return cleaned_fact_df_data[
                (start_num <= series_num) & (series_num <= end_num)
            ]

    return None


def _get_fyqrt_of_date(date: str):
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    return date_obj.year, f"Q{(date_obj.month - 1) // 3 + 1}"


async def get_current_ratio(
    ticker: str, ticker_concepts: Optional[Dict[str, Any]] = None
):
    if ticker_concepts is None:
        ticker_concepts = await fetch_sec_concepts(TICKER_TO_CIK_MAP[ticker])

    start_fyqrt, end_fyqrt = _get_fyqrt_of_date(BACKFILL_DATES[0]), _get_fyqrt_of_date(
        BACKFILL_DATES[-1]
    )

    current_assets = get_cleaned_fact(
        ticker_concepts, ["AssetsCurrent", "Assets"], start_fyqrt, end_fyqrt, True
    )
    if current_assets is None:
        return None

    current_liabilities = get_cleaned_fact(
        ticker_concepts,
        ["LiabilitiesCurrent", "Liabilities"],
        start_fyqrt,
        end_fyqrt,
        True,
    )
    if current_liabilities is None:
        return None

    merged = current_assets.merge(
        current_liabilities,
        on=["start", "end", "fp"],
        suffixes=("_assets", "_liabilities"),
        how="inner",
    )

    # Ensure float to avoid integer division issues
    assets = merged["key_name_assets"].astype(float)
    liabilities = merged["key_name_liabilities"].astype(float)

    # Safe division: set ratio to NaN where liabilities == 0
    merged["current_ratio"] = assets / liabilities.replace(0, np.nan)

    return merged


async def get_asset_turnover(ticker: str, ticker_concepts: Optional[Dict[str, Any]]):

    if ticker_concepts is None:
        ticker_concepts = await fetch_sec_concepts(TICKER_TO_CIK_MAP[ticker])

    start_fyqrt, end_fyqrt = _get_fyqrt_of_date(BACKFILL_DATES[0]), _get_fyqrt_of_date(
        BACKFILL_DATES[-1]
    )

    prev_fyqrt = numeric_to_fyqrt(fyqrt_to_numeric(start_fyqrt) - 0.25)

    revenues = get_cleaned_fact(
        ticker_concepts,
        [
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
        ],
        prev_fyqrt,
        end_fyqrt,
    )
    if revenues is None:
        return None

    assets = get_cleaned_fact(ticker_concepts, ["Assets"], prev_fyqrt, end_fyqrt, True)
    if assets is None:
        return None

    merged = revenues.merge(
        assets,
        on=["start", "end", "fp"],
        suffixes=("_rev", "_assets"),
        how="inner",
    )

    merged = merged.sort_values("end")
    merged["avg_assets"] = (
        merged["key_name_assets"] + merged["key_name_assets"].shift(1)
    ) / 2

    merged.dropna(inplace=True)

    revenues = merged["key_name_rev"].astype(float)
    avg_assets = merged["avg_assets"].astype(float)

    merged["asset_turnover"] = revenues / avg_assets.replace(0, np.nan)

    return merged


async def get_gross_profit_percentage(
    ticker: str, ticker_concepts: Optional[Dict[str, Any]]
):
    if ticker_concepts is None:
        ticker_concepts = await fetch_sec_concepts(TICKER_TO_CIK_MAP[ticker])

    start_fyqrt, end_fyqrt = _get_fyqrt_of_date(BACKFILL_DATES[0]), _get_fyqrt_of_date(
        BACKFILL_DATES[-1]
    )

    revenues = get_cleaned_fact(
        ticker_concepts,
        [
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "RegulatedAndUnregulatedOperatingRevenue",
        ],
        start_fyqrt,
        end_fyqrt,
    )
    if revenues is None:
        return None

    gross_profit = get_cleaned_fact(
        ticker_concepts,
        ["NetIncomeLoss", "GrossProfit", "ProfitLoss"],
        start_fyqrt,
        end_fyqrt,
    )
    if gross_profit is None:
        return gross_profit

    merged = revenues.merge(
        gross_profit,
        on=["start", "end", "fp"],
        suffixes=("_rev", "_gross_profit"),
        how="inner",
    )

    gross_profit = merged["key_name_gross_profit"].astype(float)
    revenues = merged["key_name_rev"].astype(float)

    merged["gross_profit_pct"] = gross_profit / revenues.replace(0, np.nan)

    return merged
