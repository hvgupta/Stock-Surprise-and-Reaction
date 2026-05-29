from fastapi import Query
from pydantic import BaseModel, model_validator
from typing import Dict, NotRequired, Optional, TypedDict, Union, overload

SURPRISE_THRESHOLD = 0.03


class ReactionRequest(BaseModel):
    reaction_days_threshold: int = Query(default=1, ge=1, lt=4)
    surprise_threshold: float = Query(default=SURPRISE_THRESHOLD)
    filings_date: Optional[str] = Query(default=None)
    reaction_date: Optional[str] = Query(default=None)


class PropotionateRequest(BaseModel):
    filings_date: Optional[str] = Query(default=None)
    surprise: Optional[float] = Query(default=None)
    cumalative_reaction: Optional[float] = Query(default=None)

    @model_validator(mode="after")
    def validate_at_least_one_field(
        self: "PropotionateRequest",
    ) -> "PropotionateRequest":
        # Enforce that either filings_date/date is provided, or both surprise and cumalative_reaction
        if self.filings_date is None and (
            self.surprise is None or self.cumalative_reaction is None
        ):
            raise ValueError(
                "Provide either filings_date/date, or both surprise and cumalative_reaction"
            )
        return self


class SurpriseEndpointResponse(TypedDict):
    ticker: str
    surprise: Dict[str, float]


class FilingReactionData(TypedDict):
    reaction: Union[Dict[str, float], str]
    surprise: float
    market: NotRequired[Union[Dict[str, float], str]]


class ReactionEndpointResponse(TypedDict):
    ticker: str
    reaction_data: Dict[str, FilingReactionData]


class SP500TickerSnapshot(TypedDict):
    ticker: str
    company_name: str
    sector: str
    filing_date: str
    surprise: float
    latest_reaction: NotRequired[Optional[float]]


class SP500SurprisesResponse(TypedDict):
    count: int
    items: list[SP500TickerSnapshot]



class RegressionModelValues(TypedDict):
    surprise_mean: float
    surprise_sd: float
    alpha: float
    beta: float


class ProportionalityResponseEntry(TypedDict):
    pct_diff: float
    expected_CAR: float
    actual_CAR: float
    regression_model: RegressionModelValues


class GeneratedProportionalityPoint(TypedDict):
    z_score: float
    reaction: float


class GeneratedProportionalityLinePoint(TypedDict):
    z_score: float
    expected_reaction: float


class GeneratedProportionalityPlotResponse(TypedDict):
    sector: str
    filing_date: str
    alpha: float
    beta: float
    x_mean: float
    x_sd: float
    points: list[GeneratedProportionalityPoint]
    outliers: list[GeneratedProportionalityPoint]
    line_points: list[GeneratedProportionalityLinePoint]
