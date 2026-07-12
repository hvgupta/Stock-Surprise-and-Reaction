from .adapters import TICKER_TO_CIK_MAP, fetch_sec_concepts, clean_period_table

from typing import Tuple

def get_current_ratio(ticker: str, fyqrt_info: Tuple[int, str]):
    ...