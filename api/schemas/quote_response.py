"""
Response models for instant quotes.

IMPORTANT: These models ONLY expose customer-safe data.
Never include vendor names, costs, margins, model metrics, or routing reasons.
"""
from pydantic import BaseModel
from typing import Optional


class TierPrice(BaseModel):
    quantity: int
    unit_price: float
    total_price: float


class MethodPricing(BaseModel):
    tiers: list[TierPrice]
    lead_time: str
    notes: list[str]


class InstantQuoteResponse(BaseModel):
    quote_id: int
    specifications: dict  # echo back the bag configuration
    digital: Optional[MethodPricing] = None
    flexographic: Optional[MethodPricing] = None
    international_air: Optional[MethodPricing] = None
    international_ocean: Optional[MethodPricing] = None
