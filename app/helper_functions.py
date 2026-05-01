from app.sql_functions import (
    SQLiteDatabase,
    FilingDateValues,
    get_ticker_reaction,
    upsert_reaction_data,
    upsert_surprise_data,
    upsert_eps_data_of_ticker,
)
from app.logger import get_configured_logger
from app.adapters import (
    get_1d_return_of_ticker,
    calc_reaction_of_ticker,
    calc_surprise_of_ticker,
)

logger = get_configured_logger(__name__)

from typing import Optional
from fastapi import HTTPException
from datetime import datetime, timedelta
import re


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
    num_days: int,
    market_index: str,
    cur_filing_date: str,
    cur_date: Optional[str],
) -> Optional[FilingDateValues[float]]:
    cur_filing_date = normalize_date_str(cur_filing_date)
    cur_date = normalize_date_str(cur_date) if cur_date is not None else None

    if cur_date is not None:
        filing_dt = datetime.strptime(cur_filing_date, "%Y-%m-%d")
        date_dt = datetime.strptime(cur_date, "%Y-%m-%d")
        if filing_dt > date_dt or (date_dt - filing_dt) > timedelta(days=3):
            return None

    cached = get_ticker_reaction(db, ticker, filing_date=cur_filing_date, date=cur_date)
    if cached is not None:
        logger.info(
            f"Reaction for {ticker} on filing date {cur_filing_date} and date {cur_date} found in database, returning cached value: {cached}"
        )
        return cached

    ticker_cumulative_return = 0.0
    market_cumulative_return = 0.0

    filings_data: FilingDateValues[float] = {cur_filing_date: {}}

    for n in range(1, num_days + 1):
        insert_date = (
            datetime.strptime(cur_filing_date, "%Y-%m-%d") + timedelta(days=n)
        ).strftime("%Y-%m-%d")
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

        reaction = calc_reaction_of_ticker(
            ticker_cumulative_return, market_cumulative_return
        )
        upsert_reaction_data(db, ticker, cur_filing_date, insert_date, reaction)
        filings_data[cur_filing_date][insert_date] = reaction

    if cur_date is not None and cur_date not in filings_data[cur_filing_date]:
        # If the requested date is not within the num_days window, calculate reaction up to that date
        raise HTTPException(
            status_code=400,
            detail=f"the requested date {cur_date} is outside the num_days window of {num_days} days from the filing date {cur_filing_date}, cannot calculate reaction",
        )
    elif cur_date is not None:
        return {cur_filing_date: {cur_date: filings_data[cur_filing_date][cur_date]}}
    else:
        return filings_data
