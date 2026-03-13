"""Debug endpoint for comparing pricing internals. Protected by API key."""
import os
import logging

from fastapi import APIRouter, Header, HTTPException
import pandas as pd

from api.schemas.quote_request import InstantQuoteRequest
from api.services.prediction_service import (
    _build_internal_specs,
    get_predictor,
    _apply_margin,
    DEFAULT_MARGIN_PCT,
)
from src.ml.feature_engineering import prepare_features

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["debug"])


@router.post("/quotes/debug")
async def debug_quote(
    request: InstantQuoteRequest,
    x_debug_key: str = Header(...),
):
    expected = os.getenv("DEBUG_API_KEY", "")
    if not expected or x_debug_key != expected:
        raise HTTPException(status_code=403, detail="Invalid debug key")

    predictor = get_predictor()
    specs = _build_internal_specs(request)
    quantities = sorted(request.quantities)

    # Feature snapshot for first quantity
    row = {**specs, "quantity": quantities[0], "print_method": "Digital"}
    df = prepare_features(pd.DataFrame([row]))
    feature_snapshot = df.iloc[0].to_dict()
    # Convert numpy types to Python types for JSON serialization
    feature_snapshot = {
        k: (v.item() if hasattr(v, "item") else v)
        for k, v in feature_snapshot.items()
    }

    # Run predictions for each method
    digital_specs = {**specs, "print_method": "Digital"}
    digital_result = predictor.predict(digital_specs, quantities)

    return {
        "internal_specs": specs,
        "feature_snapshot": feature_snapshot,
        "margin_pct": DEFAULT_MARGIN_PCT,
        "digital": digital_result,
    }
