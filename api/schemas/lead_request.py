"""
Pydantic models for lead capture.
"""
from pydantic import BaseModel, Field


class LeadCaptureRequest(BaseModel):
    full_name: str = Field(..., min_length=1, description="Contact full name")
    business_name: str = Field(..., min_length=1, description="Company / business name")
    email: str = Field(..., min_length=5, description="Business email address")
    phone: str = Field(..., min_length=7, description="Phone number")
    annual_spend: str = Field(
        ...,
        description="Estimated annual packaging spend: <$10K | $10-50K | $50-100K | $100-250K | $250K+",
    )


class LeadCaptureResponse(BaseModel):
    lead_id: int
    message: str = "Lead captured successfully"
