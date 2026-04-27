import os
import dotenv
import aiohttp
from typing import Any

dotenv.load_dotenv(override=True)

BASE_URL = "https://financialmodelingprep.com/"


async def _call_fmp_async(endpoint: str, params: dict[str, Any]) -> dict:
    url = f"{BASE_URL}{endpoint}"
    API_KEY = os.getenv("FMP_API_KEY")
    if not API_KEY:
        raise ValueError("FMP_API_KEY is not set in environment variables.")

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"apikey": API_KEY, **params}) as response:
            try:
                response.raise_for_status()
            except aiohttp.ClientResponseError as e:
                print(f"HTTP error: {e.status} - {e.message}")
                return {}
            return await response.json()


async def call_earnings_calendar_async(page: int = 0) -> dict:
    return await _call_fmp_async("stable/earnings-calendar", {"page": page})
