from backend.logger import get_configured_logger

logger = get_configured_logger(__name__)

import pandas as pd
import yfinance as yf
from pandas import Series
from typing import Optional
from datetime import datetime, timedelta
import re


def _round_to_working_day(date: datetime, inc: bool) -> datetime:
    if date.weekday() == 5:  # Saturday
        date += timedelta(days=2) if inc else timedelta(days=-1)
    elif date.weekday() == 6:  # Sunday
        date += timedelta(days=1) if inc else timedelta(days=-2)
    return date


def _normalize_date_str(date: str) -> str:
    date = date.strip()
    if not date:
        raise ValueError("date must be a non-empty string")

    # Fast path
    if len(date) == 10 and date[4] == "-" and date[7] == "-":
        return date

    # If the string starts with a date, keep only the date portion.
    # Handles common pandas/ISO variants like:
    #   "YYYY-MM-DD 00:00:00", "YYYY-MM-DDT00:00:00",
    #   "YYYY-MM-DDT00:00:00.000000000", "YYYY-MM-DDT00:00:00Z"
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", date)
    if match:
        return match.group(1)

    candidate = date
    # Handle trailing Z (UTC) for fromisoformat
    if candidate.endswith("Z"):
        candidate = candidate[:-1]

    try:
        dt = datetime.fromisoformat(candidate)
        return dt.date().isoformat()
    except ValueError:
        # Last resort: attempt to interpret whatever remains as a date.
        dt = datetime.strptime(date, "%Y-%m-%d")
        return dt.date().isoformat()


def get_earnings_history_of_ticker(ticker: str) -> Optional[pd.DataFrame]:
    logger.info(f"Fetching earnings history for {ticker}")
    yf_ticker = yf.Ticker(ticker)
    try:
        earnings_history = yf_ticker.get_earnings_history()
        if earnings_history is not None and not earnings_history.empty:  # type: ignore
            logger.info(f"Successfully fetched earnings history for {ticker}")
            return earnings_history  # type: ignore
        else:
            logger.warning(f"No earnings history found for {ticker}")
            return None
    except Exception as e:
        logger.error(f"Error fetching earnings history for {ticker}: {e}")
        return None


def get_1d_return_of_ticker(ticker: str, date: str) -> Optional[float]:
    """
        returns in this case is defined as the returns from date-1d("closing") to date("closing")
    """
    logger.info(f"Fetching 1-day return for {ticker} on {date}")
    yf_ticker = yf.Ticker(ticker)

    date = _normalize_date_str(date)

    start_date = _round_to_working_day(
        datetime.fromisoformat(date) - timedelta(days=1), inc=False
    ).strftime("%Y-%m-%d")
    end_date = _round_to_working_day(
        datetime.fromisoformat(date) + timedelta(days=1), inc=True
    ).strftime("%Y-%m-%d")

    try:
        # Get data including the target date 
        hist = yf_ticker.history(start=start_date, end=end_date)
    except Exception as e:
        logger.error(f"Error fetching 1-day return for {ticker} on {date}: {e}")
        return None

    if hist.empty:
        logger.warning(f"No historical data found for {ticker} on {date}")
        return None

    closing_prices: Series[float] = hist["Close"]
    logger.info(f"Closing prices for {ticker} from {start_date} to {end_date}: {closing_prices.to_dict()}")
    return float(
        (closing_prices.iloc[-1] - closing_prices.iloc[0]) / closing_prices.iloc[0]
    )
