import numpy as np
from numpy.typing import NDArray

def calc_surprise_of_ticker(trailing_eps: float, forward_eps: float) -> float:
    if trailing_eps == 0:
        return 0.0
    surprise = (forward_eps - trailing_eps) / abs(trailing_eps)
    return surprise

def calc_market_return(x_day_return: NDArray[np.float64], market_cap: NDArray[np.float64]) -> float:
    normalized_market_cap = market_cap / np.sum(market_cap)
    return float(np.sum(x_day_return * normalized_market_cap))

def calc_reaction_of_ticker(surprise: float, market_return: float) -> float:
    return surprise - market_return

