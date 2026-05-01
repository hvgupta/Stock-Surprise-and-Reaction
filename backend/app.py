from __future__ import annotations

from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI

from backend.logger import get_configured_logger
from backend.sql_functions import SQLiteDatabase

logger = get_configured_logger(__name__)

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

from . import main as handlers

app.get("/health")(handlers.health_check)
app.get("/supported_tickers")(handlers.get_supported_tickers)
app.get("/{ticker}/dates")(handlers.get_filing_dates_for_ticker)
app.get("/{ticker}/surprise")(handlers.fetch_surprise_for_ticker)
app.get("/{ticker}/reaction")(handlers.fetch_reaction_for_ticker)
app.get("/{ticker}/proportionate")(handlers.fetch_proportionate_for_ticker)
app.get("/{ticker}/pe")(handlers.ticker_pe)
app.get("/{ticker}/earnings_last")(handlers.ticker_last_earnings)
app.get("/{ticker}/history")(handlers.ticker_history)
