from contextlib import asynccontextmanager

import os
import dotenv
from typing import cast
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.logger import get_configured_logger
from backend.supabase import create_async_client, AsyncClient
from backend.model import ReactionRequest, PropotionateRequest

logger = get_configured_logger(__name__)

dotenv.load_dotenv(override=True)

ADMIN_MODE = os.getenv("SUPABASE_ADMIN_API_KEY") is not None

@asynccontextmanager
async def lifespan(app: FastAPI):
    sbac = create_async_client()
    app.state.supabase_client = sbac
    yield
    


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.router import reader_router

app.include_router(reader_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}



@app.get("/generated_plots/proportionality/data")
async def fetch_generated_proportionality_plot_data(
    sector: str = Query(...),
    filing_date: str = Query(...),
):
    sbac = cast(AsyncClient, app.state.database)
    return await handlers.fetch_generated_proportionality_plot_data(sbac, sector, filing_date)
