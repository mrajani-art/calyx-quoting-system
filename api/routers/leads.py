"""
Lead capture router.

POST /api/v1/leads - Capture a new lead before they can request quotes.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.schemas.lead_request import LeadCaptureRequest, LeadCaptureResponse
from api.services.supabase_client import insert_lead, get_supabase, get_files_for_lead
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


@router.get("/leads/{lead_id}/detail")
async def get_lead_detail(lead_id: str):
    """Get complete lead detail including all quotes and files. Used by sales rep backend page."""
    sb = get_supabase()

    # Fetch lead
    lead_result = sb.table("customer_leads").select("*").eq("id", lead_id).execute()
    if not lead_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = lead_result.data[0]

    # Fetch all quotes for this lead, newest first
    quotes_result = sb.table("customer_quotes").select("*").eq("lead_id", lead_id).order("created_at", desc=True).execute()
    quotes = quotes_result.data or []

    # Sanitize quotes: strip internal fields
    safe_quotes = []
    for q in quotes:
        safe_quotes.append({
            "id": q.get("id"),
            "created_at": q.get("created_at"),
            "specifications": q.get("specifications"),
            "pricing_digital": q.get("pricing_digital"),
            "pricing_flexo": q.get("pricing_flexo"),
            "pricing_intl_air": q.get("pricing_intl_air"),
            "pricing_intl_ocean": q.get("pricing_intl_ocean"),
            "requested_manager": q.get("requested_manager", False),
            "margin_applied": q.get("margin_applied"),
        })

    # Fetch all files
    files = get_files_for_lead(lead_id)

    return {"lead": lead, "quotes": safe_quotes, "files": files}
