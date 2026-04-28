from app.logger import get_configured_logger
logger = get_configured_logger(__name__)

from app.helper import SQLiteDatabase

import dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager

dotenv.load_dotenv(override=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    with SQLiteDatabase("./market.db") as database:
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

@app.get("/calc_surprise")
async def fetch_surprise_for_ticker(ticker: str):
    ...