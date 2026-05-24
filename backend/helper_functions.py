from backend.sql_functions import (
    SQLiteDatabase,
    DateValues,
    get_ticker_reaction,
    upsert_reaction_data,
    upsert_surprise_data,
    upsert_eps_data_of_ticker,
)
from backend.logger import get_configured_logger
from backend.adapters import (
    round_to_working_day,
    get_1d_return_of_ticker,
    calc_reaction_of_ticker,
    calc_surprise_of_ticker,
)

logger = get_configured_logger(__name__)

import re
import numpy as np
from numpy.typing import NDArray
from fastapi import HTTPException
from typing import Optional, Tuple
from datetime import datetime, timedelta

_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def normalize_date_str(value: str) -> str:
    """Normalize a date-like string to YYYY-MM-DD.

    Accepts values like:
    - "2025-03-31"
    - "2025-03-31 00:00:00" (pandas Timestamp str)
    - "2025-03-31T00:00:00" (ISO datetime)
    - "2025-03-31T00:00:00+00:00" (ISO with tz)
    """

    s = str(value).strip()
    match = _DATE_PREFIX_RE.match(s)
    if match:
        return match.group(1)

    raise HTTPException(
        status_code=400,
        detail=f"invalid date format: {value!r}; expected YYYY-MM-DD (optionally with a time component)",
    )


def get_surprise_for_date(
    db: SQLiteDatabase, ticker: str, trailing_eps: float, forward_eps: float, date: str
) -> float:
    date = normalize_date_str(date)
    surprise = calc_surprise_of_ticker(trailing_eps, forward_eps)
    upsert_eps_data_of_ticker(db, ticker, date, trailing_eps, forward_eps)
    upsert_surprise_data(db, ticker, date, surprise)
    return surprise

def get_reaction_for_date(
    db: SQLiteDatabase,
    ticker: str,
    market_index: str,
    cur_filing_date: str,
    cur_date: Optional[str],
    reaction_days_threshold: int = 3,
) -> Optional[DateValues[DateValues[float]]]:
    cur_filing_date = normalize_date_str(
        cur_filing_date
    )  # YYYY-MM-DD , YYYY-MM-DD HH:MM:SS, ISO format
    cur_date = normalize_date_str(cur_date) if cur_date is not None else None

    if cur_date is not None:
        filing_dt = datetime.strptime(cur_filing_date, "%Y-%m-%d")
        reaction_date_dt = datetime.strptime(cur_date, "%Y-%m-%d")
        if filing_dt > reaction_date_dt or (reaction_date_dt - filing_dt) > timedelta(
            days=reaction_days_threshold
        ):
            return None

    cached = get_ticker_reaction(db, ticker, filing_date=cur_filing_date, reaction_date=cur_date)
    if cached is not None:
        logger.info(
            f"Reaction for {ticker} on filing date {cur_filing_date} and date {cur_date} found in database, returning cached value: {cached}"
        )
        return cached

    ticker_cumulative_return = 0.0
    market_cumulative_return = 0.0

    filings_data: DateValues[DateValues[float]] = {cur_filing_date: {}}

    days_offset = 0

    for n in range(1, 1 + reaction_days_threshold):
        insert_date = (
            datetime.strptime(cur_filing_date, "%Y-%m-%d") + timedelta(days=n+days_offset)
        )
        if insert_date.weekday() >= 5:
            days_offset += 7 - insert_date.weekday()
            insert_date = round_to_working_day(insert_date, inc=True)

        one_day_return = get_1d_return_of_ticker(ticker, insert_date)
        if one_day_return is None:
            raise HTTPException(
                status_code=404,
                detail=f"could not fetch 1-day return for ticker {ticker} on {insert_date}, cannot calculate reaction",
            )
        ticker_cumulative_return += one_day_return
        market_n_day_return = get_1d_return_of_ticker(market_index, insert_date)
        if market_n_day_return is None:
            raise HTTPException(
                status_code=404,
                detail=f"could not fetch 1-day return for market index {market_index} on {insert_date}, cannot calculate reaction",
            )
        market_cumulative_return += market_n_day_return

        logger.info(
            f"for ticker {ticker} on filing date {cur_filing_date}, day {n} return is {one_day_return}, cumulative return is {ticker_cumulative_return}; for market index {market_index}, day {n} return is {market_n_day_return}, cumulative return is {market_cumulative_return}"
        )

        reaction = calc_reaction_of_ticker(
            ticker_cumulative_return, market_cumulative_return
        )

        upsert_reaction_data(db, ticker, cur_filing_date, insert_date.strftime("%Y-%m-%d"), reaction)
        filings_data[cur_filing_date][insert_date.strftime("%Y-%m-%d")] = reaction

    if cur_date is not None and cur_date not in filings_data[cur_filing_date]:
        # If the requested date is not within the num_days window, calculate reaction up to that date
        raise HTTPException(
            status_code=400,
            detail=f"the requested date {cur_date} is outside the num_days window of 3 days from the filing date {cur_filing_date}, cannot calculate reaction",
        )
    elif cur_date is not None:
        return {cur_filing_date: {cur_date: filings_data[cur_filing_date][cur_date]}}
    else:
        return filings_data


def normalize_x(unnormalized_x: list[float]) -> Tuple[NDArray[np.float64], np.float64, np.float64]:
    mean = np.mean(unnormalized_x)
    sd = np.std(unnormalized_x)

    return (np.array(unnormalized_x) - mean) / (sd + 1e-8), np.float64(mean), np.float64(sd)