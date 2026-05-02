def calc_surprise_of_ticker(trailing_eps: float, forward_eps: float) -> float:
    if trailing_eps == 0:
        return 0.0
    surprise = (forward_eps - trailing_eps) / abs(trailing_eps)
    return surprise

def calc_reaction_of_ticker(ticker_returns: float, market_returns: float) -> float:
    return ticker_returns - market_returns

