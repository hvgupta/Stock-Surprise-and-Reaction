from app.logger import get_configured_logger
logger = get_configured_logger(__name__)

import os
import dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager

dotenv.load_dotenv(override=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up the application...")
    yield
    logger.info("Shutting down the application...")

app = FastAPI(lifespan=lifespan)