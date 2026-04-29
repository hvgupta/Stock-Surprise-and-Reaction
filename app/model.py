from pydantic import BaseModel
from fastapi import Query


DEFAULT_THRESHOLD = 0.1


class ReactionRequest(BaseModel):
    # `ticker` will be provided from the path parameter; exclude from query dependency
    num_day_return: int = Query(default=1, ge=1, le=4)
    market_index: str = Query(default="SPY")
    threshold: float = Query(default=DEFAULT_THRESHOLD)