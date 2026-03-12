"""
Lead capture router.

POST /api/v1/leads - Capture a new lead before they can request quotes.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.schemas.lead_request import LeadCaptureRequest, LeadCaptureResponse
from api.services.supabase_client import insert_lead
from api.services.slack_service import notify_slack_new_lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["leads"])


@router.post("/leads", response_model=LeadCaptureResponse)
async def capture_lead(
    request: LeadCaptureRequest,
    background_tasks: BackgroundTasks,
):
    """
    Capture a new lead.

    Persists to Supabase customer_leads and returns the generated UUID
    for use as lead_id when requesting quotes.
    """
    try:
        row = insert_lead({
            "full_name": request.full_name,
            "business_name": request.business_name,
            "email": request.email,
            "phone": request.phone,
            "annual_spend": request.annual_spend,
        })
    except Exception as e:
        logger.error(f"Failed to persist lead: {e}")
        raise HTTPException(status_code=500, detail="Failed to save lead. Please try again.")

    lead_id = row.get("id", "")
    if not lead_id:
        raise HTTPException(status_code=500, detail="Failed to save lead.")

    logger.info(
        f"Lead captured: {lead_id} | "
        f"{request.business_name} | "
        f"{request.email} | "
        f"Annual spend: {request.annual_spend}"
    )

    # Fire-and-forget Slack notification
    background_tasks.add_task(
        notify_slack_new_lead,
        {
            "lead_id": lead_id,
            "full_name": request.full_name,
            "business_name": request.business_name,
            "email": request.email,
            "phone": request.phone,
            "annual_spend": request.annual_spend,
        },
    )

    return LeadCaptureResponse(lead_id=lead_id)
