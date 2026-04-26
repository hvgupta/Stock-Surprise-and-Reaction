from .SP500_companies import fetch_sp500_companies

SP500_COMPANIES = fetch_sp500_companies()

__all__ = [
    "SP500_COMPANIES"
]