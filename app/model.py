from fastapi import Query
from typing import Dict, Optional, TypedDict
from pydantic import BaseModel, model_validator

DEFAULT_THRESHOLD = 0.03


class ReactionRequest(BaseModel):
    num_day_return: int = Query(default=1, ge=1, lt=4)
    market_index: str = Query(default="SPY")
    threshold: float = Query(default=DEFAULT_THRESHOLD)
    filings_date: Optional[str] = Query(default=None)
    date: Optional[str] = Query(default=None)


class PropotionateRequest(BaseModel):
    filings_date: Optional[str] = Query(default=None)
    date: Optional[str] = Query(default=None)
    surprise: Optional[float] = Query(default=None)
    cumalative_reaction: Optional[float] = Query(default=None)

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        if (
            self.date is None
            and self.filings_date is None
            and (self.surprise is None or self.cumalative_reaction is None)
        ):
            raise ValueError(
                "Provide either filings_date/date, or both surprise and cumalative_reaction"
            )
        return self


class SurpriseEndpointResponse(TypedDict):
    ticker: str
    surprise: Dict[str, float]