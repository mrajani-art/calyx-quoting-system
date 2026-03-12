"""
Instant quote router.

POST /api/v1/quotes/instant - Generate an instant quote across all print methods.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.schemas.quote_request import InstantQuoteRequest
from api.schemas.quote_response import InstantQuoteResponse
from api.services.prediction_service import generate_instant_quote, DEFAULT_MARGIN_PCT
from api.services.supabase_client import insert_quote
from api.services.slack_service import notify_slack_quote
from api.middleware.sanitizer import sanitize_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["quotes"])


def _method_to_json(method_pricing) -> dict | None:
    """Serialize a MethodPricing to a JSON-safe dict for Supabase storage."""
    if method_pricing is None:
        return None
    return method_pricing.model_dump()


@router.post("/quotes/instant", response_model=InstantQuoteResponse)
async def instant_quote(
    request: InstantQuoteRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate an instant quote for the given bag specifications.

    Returns pricing across up to 4 print methods:
    - Digital
    - Flexographic
    - International Air (Gravure)
    - International Ocean (Gravure)

    All prices are sell prices with margin applied.
    No internal cost data, vendor names, or model metrics are exposed.
    """
    try:
        raw_result = generate_instant_quote(request)
    except Exception as e:
        logger.error(f"Quote generation failed for lead {request.lead_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate quote. Please try again.",
        )

    # Sanitize to strip any accidentally leaked internal data
    sanitized = sanitize_response(raw_result)

    # Build customer-facing specifications echo
    specifications = {
        "width": request.width,
        "height": request.height,
        "gusset": request.gusset,
        "substrate": request.substrate,
        "finish": request.finish,
        "seal_type": request.seal_type,
        "fill_style": request.fill_style,
        "zipper": request.zipper,
        "tear_notch": request.tear_notch,
        "hole_punch": request.hole_punch,
        "corners": request.corners,
        "embellishment": request.embellishment,
        "quantities": request.quantities,
    }

    response = InstantQuoteResponse(
        quote_id="pending",  # Will be replaced by DB-generated UUID
        specifications=specifications,
        digital=sanitized.get("digital"),
        flexographic=sanitized.get("flexographic"),
        international_air=sanitized.get("international_air"),
        international_ocean=sanitized.get("international_ocean"),
    )

    # Persist to Supabase
    try:
        row = insert_quote({
            "lead_id": request.lead_id,
            "specifications": specifications,
            "pricing_digital": _method_to_json(response.digital),
            "pricing_flexo": _method_to_json(response.flexographic),
            "pricing_intl_air": _method_to_json(response.international_air),
            "pricing_intl_ocean": _method_to_json(response.international_ocean),
            "margin_applied": DEFAULT_MARGIN_PCT,
        })
        quote_id = row.get("id", response.quote_id)
        response.quote_id = quote_id
    except Exception as e:
        logger.error(f"Failed to persist quote for lead {request.lead_id}: {e}")
        # Non-fatal: still return the quote even if DB write fails
        response.quote_id = "transient"

    # Fire-and-forget Slack notification
    background_tasks.add_task(
        notify_slack_quote,
        {
            "lead_id": request.lead_id,
            "full_name": "",  # Slack service will look up from lead if needed
            "business_name": "",
            "email": "",
            "phone": "",
            "annual_spend": "",
        },
        {
            "quote_id": response.quote_id,
            "specifications": specifications,
            "digital": _method_to_json(response.digital),
            "flexographic": _method_to_json(response.flexographic),
            "international_air": _method_to_json(response.international_air),
            "international_ocean": _method_to_json(response.international_ocean),
        },
    )

    logger.info(
        f"Quote {response.quote_id} generated for lead {request.lead_id} | "
        f"Digital={'yes' if response.digital else 'no'} | "
        f"Flexo={'yes' if response.flexographic else 'no'} | "
        f"Air={'yes' if response.international_air else 'no'} | "
        f"Ocean={'yes' if response.international_ocean else 'no'}"
    )

    return response
