from app.logger import get_configured_logger
from app.helper import (
    SQLiteDatabase,
    get_all_supported_tickers,
    get_ticker_surprise,
    get_eps_data_of_ticker,
    calc_surprise_of_ticker,
    insert_surprise_data
)

logger = get_configured_logger(__name__)


import dotenv
from typing import cast
from fastapi import FastAPI
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


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/supported_tickers")
async def get_supported_tickers():
    all_tickers = get_all_supported_tickers(cast(SQLiteDatabase, app.state.database))
    return {"tickers": all_tickers, "count": len(all_tickers)}


@app.get("/calc_surprise")
async def fetch_surprise_for_ticker(ticker: str):
    db_conn = cast(SQLiteDatabase, app.state.database)
    surprise = get_ticker_surprise(db_conn, ticker)
    if surprise is not None:
        return {"ticker": ticker, "surprise": surprise}

    eps_data = get_eps_data_of_ticker(db_conn, ticker)
    if eps_data is None:
        return {"error": f"the ticker {ticker} is not supported, check the /supported_tickers endpoint for the list of supported tickers"}

    surprise = calc_surprise_of_ticker(eps_data[0], eps_data[1])
    insert_surprise_data(db_conn, ticker, surprise)  # Using a placeholder date for now
    return {"ticker": ticker, "surprise": surprise}