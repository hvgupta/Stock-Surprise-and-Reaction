from app.logger import get_configured_logger

logger = get_configured_logger(__name__)

import pandas as pd
import yfinance as yf
from typing import Optional

async def fetch_ticker_historical_prices(
    ticker_symbol: str, start_date: str, end_date: str
) -> pd.DataFrame:
    """
    yfinance is synchronous; run the download call in a thread to avoid blocking the event loop.
    """
    logger.info(
        f"Fetching historical prices for {ticker_symbol} from {start_date} to {end_date} (async)"
    )

    data = yf.download(
        ticker_symbol, start=start_date, end=end_date, multi_level_index=False
    )

    logger.info(f"Successfully fetched historical prices for {ticker_symbol}")

    if data is None or data.empty:
        logger.warning(f"No historical price data found for {ticker_symbol}")
        raise ValueError(f"No historical price data found for {ticker_symbol}")

    data.reset_index(inplace=True)
    data["Date"] = pd.to_datetime(data["Date"])

    return data

def get_current_pe_of_ticker(ticker: str) -> Optional[float]:
    logger.info(f"Fetching current P/E ratio for {ticker}")
    yf_ticker = yf.Ticker(ticker)
    try:
        pe_ratio = yf_ticker.info.get('trailingPE', None)
        if pe_ratio is not None:
            logger.info(f"Current P/E ratio for {ticker}: {pe_ratio}")
        else:
            logger.warning(f"Current P/E ratio not found for {ticker}")
        return pe_ratio
    except Exception as e:
        logger.error(f"Error fetching current P/E ratio for {ticker}: {e}")
        return None

def get_current_forward_pe_of_ticker(ticker: str) -> Optional[float]:
    logger.info(f"Fetching forward P/E ratio for {ticker}")
    yf_ticker = yf.Ticker(ticker)
    try:
        forward_pe = yf_ticker.info.get('forwardPE', None)
        if forward_pe is not None:
            logger.info(f"Forward P/E ratio for {ticker}: {forward_pe}")
        else:
            logger.warning(f"Forward P/E ratio not found for {ticker}")
        return forward_pe
    except Exception as e:
        logger.error(f"Error fetching forward P/E ratio for {ticker}: {e}")
        return None

def get_last_earnings_call_of_ticker(ticker: str) -> Optional[str]:
    logger.info(f"Fetching last earnings call date for {ticker}")
    yf_ticker = yf.Ticker(ticker)
    try:
        earnings_dates = yf_ticker.earnings_dates
        if not earnings_dates.empty:
            last_earnings_date = earnings_dates.index[-1].strftime('%Y-%m-%d')
            logger.info(f"Last earnings call date for {ticker}: {last_earnings_date}")
            return last_earnings_date
        else:
            logger.warning(f"No earnings dates found for {ticker}")
            return None
    except Exception as e:
        logger.error(f"Error fetching last earnings call date for {ticker}: {e}")
        return None