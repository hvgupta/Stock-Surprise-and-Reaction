from app.logger import get_configured_logger
logger = get_configured_logger(__name__)

def calc_surprise_of_ticker(trailing_eps: float, forward_eps: float) -> float:
    if trailing_eps == 0:
        return 0.0
    logger.debug(f"Calculating surprise for trailing_eps={trailing_eps}, forward_eps={forward_eps}")
    surprise = (trailing_eps - forward_eps) / abs(forward_eps)
    return surprise

def calc_reaction_of_ticker(ticker_returns: float, market_returns: float) -> float:
    return ticker_returns - market_returns

