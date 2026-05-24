from contextlib import asynccontextmanager

import dotenv
from typing import cast
from fastapi import FastAPI, Query

from backend.logger import get_configured_logger
from backend.sql_functions import SQLiteDatabase
from backend.model import ReactionRequest, PropotionateRequest

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

@app.get("/health")
async def health_check():
    return await handlers.health_check()

@app.get("/{ticker}/surprise")
async def fetch_surprise_for_ticker(ticker: str, filing_date: str | None = Query(default=None)):
    db = cast(SQLiteDatabase, app.state.database)
    return await handlers.fetch_surprise_for_ticker(db, ticker, filing_date)

@app.get("/{ticker}/reaction")
async def fetch_reaction_for_ticker(ticker: str, reaction_request: ReactionRequest = Query(...)):
    db = cast(SQLiteDatabase, app.state.database)
    return await handlers.fetch_reaction_for_ticker(db, ticker, reaction_request)

@app.get("/{ticker}/proportionate")
async def fetch_proportionality_for_ticker(ticker: str, proportionate_request: PropotionateRequest = Query(...)):
    db = cast(SQLiteDatabase, app.state.database)
    return await handlers.fetch_proportionality_for_ticker(db, ticker, proportionate_request)
