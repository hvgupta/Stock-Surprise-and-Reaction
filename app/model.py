from pydantic import BaseModel, Field


DEFAULT_THRESHOLD = 0.1

class ReactionRequest(BaseModel):
    ticker: str
    num_day_return: int = Field(default=1, ge=1, le=4)
    market_index: str = Field(default="SPY")
    threshold: float = Field(
        default=DEFAULT_THRESHOLD,
    )