import os
import dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from backend.logger import get_configured_logger
from backend.db_functions.supabase import create_async_client

logger = get_configured_logger(__name__)

dotenv.load_dotenv(override=True)

ADMIN_MODE = os.getenv("SUPABASE_ADMIN_API_KEY")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if ADMIN_MODE is not None:
        logger.info("ADMIN key is provided")
    sbac = create_async_client(ADMIN_MODE)
    logger.info("Initializing Supabase AsyncClient")
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

from backend.router import reader_router, writer_router

app.include_router(reader_router)
app.include_router(writer_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
