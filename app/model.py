from fastapi import Query
from typing import Optional
from pydantic import BaseModel

DEFAULT_THRESHOLD = 0.03


class ReactionRequest(BaseModel):
    # `ticker` will be provided from the path parameter; exclude from query dependency
    num_day_return: int = Query(default=1, ge=1, lt=4)
    market_index: str = Query(default="SPY")
    threshold: float = Query(default=DEFAULT_THRESHOLD)
    filing_date: Optional[str] = Query(default=None)
    date: Optional[str] = Query(default=None)


class PropotionateRequest(BaseModel):
    date: Optional[str] = Query(default=None)
    surprise: Optional[float] = Query(default=None)
    cumalative_reaction: Optional[float] = Query(default=None)