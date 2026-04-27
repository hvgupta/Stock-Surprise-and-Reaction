from app.logger import get_configured_logger
logger = get_configured_logger(__name__)

import requests
import pandas as pd
from io import StringIO

HEADERS = {"User-Agent": "Mozilla/5.0 (Company info@company.com)"}


def fetch_sp500_companies() -> pd.DataFrame:
    logger.info("Fetching S&P 500 company list from Wikipedia (async)")
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url, headers=HEADERS)
    sp500 = pd.read_html(StringIO(response.text))[0]

    logger.info("Successfully fetched S&P 500 company list")
    sp500 = sp500.drop(sp500[sp500["Symbol"].str.contains(r"\.", na=False)].index)
    return sp500.reset_index(drop=True)
