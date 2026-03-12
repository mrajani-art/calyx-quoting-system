"""
Pydantic model for instant quote requests.

Customer-friendly field names that get mapped to internal spec format
by the prediction service before calling QuotePredictor.
"""
from pydantic import BaseModel, Field
from typing import Optional


class InstantQuoteRequest(BaseModel):
    width: float = Field(..., gt=0, le=20, description="Bag width in inches")
    height: float = Field(..., gt=0, le=20, description="Bag height in inches")
    gusset: float = Field(default=0, ge=0, le=10, description="Gusset depth in inches")
    substrate: str = Field(
        ...,
        description="Bag substrate material: Metallic | Clear | White Metallic | High Barrier",
    )
    finish: str = Field(
        ...,
        description="Surface finish: Matte | Soft Touch | Gloss | None",
    )
    seal_type: str = Field(
        ...,
        description="Seal type: Stand Up Pouch | 3 Side Seal | 2 Side Seal",
    )
    fill_style: str = Field(
        ...,
        description="Fill orientation: Top | Bottom",
    )
    zipper: str = Field(
        ...,
        description="Zipper type: Child-Resistant | Standard | None",
    )
    tear_notch: str = Field(
        ...,
        description="Tear notch: Standard | None",
    )
    hole_punch: str = Field(
        ...,
        description="Hole punch: Round | Euro Slot | None",
    )
    corners: str = Field(
        ...,
        description="Corner treatment: Rounded | Straight",
    )
    embellishment: str = Field(
        ...,
        description="Special embellishment: Foil | Spot UV | None",
    )
    quantities: list[int] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Quantity tiers to quote (1-6 values)",
    )
    lead_id: str = Field(
        ...,
        description="UUID from lead capture step",
    )
