from app.logger import get_configured_logger
logger = get_configured_logger(__name__)

import aiohttp
import requests
import pandas as pd
from typing import Dict

HEADERS = {"User-Agent": "Mozilla/5.0 (Company info@company.com)"}

def fetch_ticker_to_cik_map() -> Dict[str, str]:
    logger.info("Fetching ticker to CIK mapping from SEC (async)")
    url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    ticker_to_cik_map = {
        info["ticker"]: str(info["cik_str"]).zfill(10)
        for info in response.json().values()
    }

    logger.info("Successfully fetched ticker to CIK mapping")
    return ticker_to_cik_map

async def fetch_sec_concepts(cik: str) -> Dict:
    logger.info(f"Fetching SEC concepts for CIK={cik} (async)")
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise Exception(f"Failed to fetch data, code: {resp.status}, reason: {resp.reason or (await resp.text())}")
            
def extract_quarterly_data(
    facts: dict, metric_name: str, unit: str
) -> pd.DataFrame:
    """
    Extract quarterly fact entries from the SEC companyfacts JSON.
    Performs DataFrame construction and datetime conversion in a thread to avoid blocking.
    """
    logger.info(f"Extracting quarterly data for {metric_name} in {unit} (async)")

    def _extract() -> pd.DataFrame:
        if "us-gaap" not in facts:
            logger.warning("us-gaap data not found in facts")
            return pd.DataFrame()

        if metric_name not in facts["us-gaap"]:
            logger.warning(f"{metric_name} not found in us-gaap facts")
            return pd.DataFrame()

        units = facts["us-gaap"][metric_name].get("units", {})
        if unit not in units:
            logger.warning(f"{unit} not found for {metric_name}")
            return pd.DataFrame()

        data = facts["us-gaap"][metric_name]["units"][unit]
        df = pd.DataFrame(data)
        if "end" in df.columns:
            df["end"] = pd.to_datetime(df["end"], errors="coerce")
            df = df.sort_values(by="end").reset_index(drop=True)
        else:
            # no end column -> empty
            return pd.DataFrame()
        return df

    df = _extract()
    if df.empty:
        logger.info(f"No quarterly data extracted for {metric_name}")
    else:
        logger.info(f"Successfully extracted quarterly data for {metric_name}")
    return df
