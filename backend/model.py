from fastapi import Query
from pydantic import BaseModel, model_validator
from typing import Dict, Optional, TypedDict, Union

SURPRISE_THRESHOLD = 0.03


class ReactionRequest(BaseModel):
    reaction_days_threshold: int = Query(default=1, ge=1, lt=4)
    market_index: str = Query(default="SPY")
    surprise_threshold: float = Query(default=SURPRISE_THRESHOLD)
    filings_date: Optional[str] = Query(default=None)
    reaction_date: Optional[str] = Query(default=None)


class PropotionateRequest(BaseModel):
    filings_date: Optional[str] = Query(default=None)
    reaction_date: Optional[str] = Query(default=None)
    surprise: Optional[float] = Query(default=None)
    cumalative_reaction: Optional[float] = Query(default=None)

    @model_validator(mode="after")
    def validate_at_least_one_field(self: "PropotionateRequest") -> "PropotionateRequest":
        # Enforce that either filings_date/date is provided, or both surprise and cumalative_reaction
        if (self.reaction_date is None and self.filings_date is None) and (
            self.surprise is None or self.cumalative_reaction is None
        ):
            raise ValueError(
                "Provide either filings_date/date, or both surprise and cumalative_reaction"
            )
        return self


class SurpriseEndpointResponse(TypedDict):
    ticker: str
    surprise: Dict[str, float]

class ReactionEndpointResponse(TypedDict):
    ticker: str
    reaction_data: Dict[str, Dict[str, Dict[str, Union[float, str]]]]