from app.helper import (
    SQLiteDatabase,
    get_all_supported_tickers,
    get_ticker_surprise,
    get_eps_data_of_ticker,
    calc_surprise_of_ticker,
    calc_reaction_of_ticker,
    upsert_surprise_data,
    upsert_reaction_data,
    get_ticker_reaction,
    get_ticker_filing_date,
)
from app.model import ReactionRequest
from app.logger import get_configured_logger
from app.adapters import get_n_day_return_of_ticker

logger = get_configured_logger(__name__)


import dotenv
from typing import cast
from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager

dotenv.load_dotenv(override=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SQLiteDatabase("./markets.db") as database:
        database.initialize()
        app.state.database = database
        logger.info("Starting up the application...")
        yield
        logger.info("Shutting down the application...")
        app.state.database = None

app = FastAPI(lifespan=lifespan)

from app.adapters import (
    get_current_pe_of_ticker,
    get_current_forward_pe_of_ticker,
    get_last_earnings_call_of_ticker,
    fetch_ticker_historical_prices,
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/supported_tickers")
async def get_supported_tickers():
    all_tickers = get_all_supported_tickers(cast(SQLiteDatabase, app.state.database))
    return {"tickers": all_tickers, "count": len(all_tickers)}


@app.get("/{ticker}/surprise")
async def fetch_surprise_for_ticker(ticker: str):
    db_conn = cast(SQLiteDatabase, app.state.database)
    surprise = get_ticker_surprise(db_conn, ticker)
    if surprise is not None:
        return {"ticker": ticker, "surprise": surprise}
    eps_data = get_eps_data_of_ticker(db_conn, ticker)
    if eps_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"the ticker {ticker} is not supported, check the /supported_tickers endpoint for the list of supported tickers",
        )

    surprise = calc_surprise_of_ticker(eps_data[0], eps_data[1])
    upsert_surprise_data(db_conn, ticker, surprise)  # Using a placeholder date for now
    return {"ticker": ticker, "surprise": surprise}


@app.get("/{ticker}/reaction")
async def fetch_reaction_for_ticker(ticker: str, reaction_request: ReactionRequest = Depends()):
    num_days = reaction_request.num_day_return
    threshold = reaction_request.threshold
    market_index = reaction_request.market_index

    surprise = await fetch_surprise_for_ticker(ticker)
    if abs(surprise["surprise"]) < threshold:
        raise HTTPException(
            status_code=400,
            detail=f"the surprise value {surprise['surprise']} for ticker {ticker} is below the threshold of {threshold}, so reaction is not calculated",
        )
    
    db_conn = cast(SQLiteDatabase, app.state.database)
    reaction = get_ticker_reaction(db_conn, ticker)
    if reaction is not None:
        return {"ticker": ticker, "reaction": reaction}
    filing_date = get_ticker_filing_date(db_conn, ticker)
    if filing_date is None:
        raise HTTPException(
            status_code=404,
            detail=f"filing date not found for ticker {ticker}, cannot calculate reaction",
        )
    
    market_n_day_return = get_n_day_return_of_ticker(market_index, filing_date, num_days)
    if market_n_day_return is None:
        raise HTTPException(
            status_code=404,
            detail=f"could not fetch {num_days}-day return for market index {market_index} starting from {filing_date}, cannot calculate reaction",
        )
    ticker_n_day_return = get_n_day_return_of_ticker(ticker, filing_date, num_days)
    if ticker_n_day_return is None:
        raise HTTPException(
            status_code=404,
            detail=f"could not fetch {num_days}-day return for ticker {ticker} starting from {filing_date}, cannot calculate reaction",
        )

    reaction = calc_reaction_of_ticker(ticker_n_day_return, market_n_day_return)
    upsert_reaction_data(db_conn, ticker, reaction)  
    return {"ticker": ticker, "reaction": reaction}
      


@app.get("/{ticker}/pe")
async def ticker_pe(ticker: str):
    """Return current trailing and forward P/E ratios for a ticker."""
    trailing = get_current_pe_of_ticker(ticker)
    forward = get_current_forward_pe_of_ticker(ticker)

    if trailing is None and forward is None:
        raise HTTPException(status_code=404, detail=f"P/E data not found for {ticker}")

    return {"ticker": ticker, "pe": trailing, "forward_pe": forward}


@app.get("/{ticker}/earnings_last")
async def ticker_last_earnings(ticker: str):
    """Return the last earnings call date for a ticker (YYYY-MM-DD)."""
    last = get_last_earnings_call_of_ticker(ticker)
    if last is None:
        raise HTTPException(
            status_code=404, detail=f"No earnings date found for {ticker}"
        )
    return {"ticker": ticker, "last_earnings_date": last}


@app.get("/{ticker}/history")
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
