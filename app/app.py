from __future__ import annotations

from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI

from app.logger import get_configured_logger
from app.sql_functions import SQLiteDatabase

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
app.get("/{ticker}/surprise")(handlers.fetch_surprise_for_ticker)
app.get("/{ticker}/reaction")(handlers.fetch_reaction_for_ticker)
app.get("/{ticker}/proportionate")(handlers.fetch_proportionality_for_ticker)
