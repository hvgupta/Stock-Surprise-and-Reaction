from backend.logger import get_configured_logger
logger = get_configured_logger(__name__)

import numpy as np
import pandas as pd

def calc_surprise_of_ticker(trailing_eps: float, forward_eps: float) -> float:
    if trailing_eps == 0:
        return 0.0
    logger.debug(f"Calculating surprise for trailing_eps={trailing_eps}, forward_eps={forward_eps}")
    surprise = (trailing_eps - forward_eps) / abs(forward_eps)
    return surprise

def calc_reaction_of_ticker(ticker_returns: float, market_returns: float) -> float:
    return ticker_returns - market_returns

def calc_pre_event_drift(price_data: pd.DataFrame, default_col: str = "Close"):
    col_data = price_data[default_col]
    ratio_array = (col_data/col_data.shift()).dropna().values
    if not isinstance(ratio_array, np.ndarray):
        raise Exception

    mean, sd = ratio_array.mean(), ratio_array.std()

    return (mean/price_data.shape[0]) + (sd**2)/2
    