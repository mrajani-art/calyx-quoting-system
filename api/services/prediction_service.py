"""
Prediction service for the customer-facing quoting portal.

Maps customer-friendly field names to internal spec format, calls
QuotePredictor.predict() for each print method, applies margin,
and returns ONLY customer-safe sell prices.

CRITICAL: Never expose vendor names, costs, margins, model metrics,
cost_factors, or routing reasons in any return value.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to path so we can import src.ml and config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.ml.prediction import QuotePredictor
from config.settings import SUBSTRATE_CANONICAL

from api.schemas.quote_request import InstantQuoteRequest
from api.schemas.quote_response import TierPrice, MethodPricing

logger = logging.getLogger(__name__)

# ── Customer-friendly → Internal value maps ────────────────────────

SUBSTRATE_MAP = {
    "Metallic": "MET PET (Metallic)",
    "Clear": "CLR PET (Clear)",
    "White Metallic": "WHT MET PET (White Metallic)",
    "High Barrier": "HB CLR PET (High Barrier Clear)",
}

FINISH_MAP = {
    "Matte": "Matte Laminate",
    "Soft Touch": "Soft Touch Laminate",
    "Gloss": "Gloss Laminate",
    "None": "None",
}

SEAL_TYPE_MAP = {
    "Stand Up Pouch": "Stand Up Pouch",
    "3 Side Seal": "3 Side Seal",
    "2 Side Seal": "2 Side Seal",
}

ZIPPER_MAP = {
    "Child-Resistant": "CR Zipper",
    "Standard": "Non-CR Zipper",
    "None": "No Zipper",
}

HOLE_PUNCH_MAP = {
    "Round": "Round",
    "Euro Slot": "Euro",
    "None": "None",
}

# Default margin percentage applied to convert cost to sell price
DEFAULT_MARGIN_PCT = 20.0

# Lead times by print method (customer-facing)
LEAD_TIMES = {
    "digital": "As little as 2 weeks with faster expedite options available",
    "flexographic": "6-8 weeks",
    "air": "4-6 weeks",
    "ocean": "8-10 weeks",
}

# Singleton predictor instance
_predictor: Optional[QuotePredictor] = None


def get_predictor() -> QuotePredictor:
    """Get or create the singleton QuotePredictor with loaded models."""
    global _predictor
    if _predictor is None:
        _predictor = QuotePredictor()
        _predictor.load_models()
        logger.info("QuotePredictor models loaded")
    return _predictor


def load_models():
    """Pre-load models at startup."""
    get_predictor()


def _apply_margin(cost: float, margin_pct: float = DEFAULT_MARGIN_PCT) -> float:
    """
    Convert cost to sell price using margin formula.
    sell_price = cost / (1 - margin_pct / 100)
    """
    if margin_pct >= 100:
        margin_pct = 99.0
    return cost * (1.0 / (1.0 - margin_pct / 100.0))


def _build_internal_specs(req: InstantQuoteRequest) -> dict:
    """
    Map customer-friendly request fields to the internal spec dict
    format expected by QuotePredictor.predict().
    """
    # Map substrate: customer name -> UI label -> canonical
    substrate_ui = SUBSTRATE_MAP.get(req.substrate, "MET PET (Metallic)")
    substrate_canonical = SUBSTRATE_CANONICAL.get(substrate_ui, "MET_PET")

    # Map finish
    finish = FINISH_MAP.get(req.finish, "None")

    # Map seal type: combine seal_type + fill_style
    base_seal = SEAL_TYPE_MAP.get(req.seal_type, "Stand Up Pouch")
    if base_seal == "Stand Up Pouch":
        seal_type = "Stand Up Pouch"
    else:
        # e.g. "3 Side Seal" + "Top" -> "3 Side Seal - Top Fill"
        seal_type = f"{base_seal} - {req.fill_style} Fill"

    # Map gusset type: Stand Up Pouch -> Plow Bottom, else None
    if req.seal_type == "Stand Up Pouch":
        gusset_type = "Plow Bottom"
    else:
        gusset_type = "None"

    # Map other fields
    zipper = ZIPPER_MAP.get(req.zipper, "No Zipper")
    tear_notch = req.tear_notch  # "Standard" or "None" pass through
    hole_punch = HOLE_PUNCH_MAP.get(req.hole_punch, "None")
    corner_treatment = req.corners  # "Rounded" or "Straight" pass through
    embellishment = req.embellishment  # "Foil", "Spot UV", or "None" pass through

    return {
        "width": req.width,
        "height": req.height,
        "gusset": req.gusset,
        "substrate": substrate_canonical,
        "finish": finish,
        "fill_style": req.fill_style,
        "seal_type": seal_type,
        "gusset_type": gusset_type,
        "zipper": zipper,
        "tear_notch": tear_notch,
        "hole_punch": hole_punch,
        "corner_treatment": corner_treatment,
        "embellishment": embellishment,
    }


def _extract_digital_pricing(
    result: dict,
    quantities: list[int],
    margin_pct: float = DEFAULT_MARGIN_PCT,
) -> Optional[MethodPricing]:
    """
    Extract digital pricing from predict() result.
    Applies margin and strips all internal data.
    """
    predictions = result.get("predictions", [])
    if not predictions:
        return None

    tiers = []
    for pred in predictions:
        cost = pred.get("unit_price", 0)
        if cost is None or cost <= 0:
            continue
        qty = pred["quantity"]
        sell_unit = round(_apply_margin(cost, margin_pct), 4)
        tiers.append(TierPrice(
            quantity=qty,
            unit_price=round(sell_unit, 4),
            total_price=round(sell_unit * qty, 2),
        ))

    if not tiers:
        return None

    notes = []
    # Check for quantity warnings without exposing vendor details
    warnings = result.get("warnings", [])
    for w in warnings:
        # Sanitize warning text: remove vendor references
        clean = w
        for vendor_name in ["dazpak", "ross", "internal", "tedpack", "hp 6900", "hp6900"]:
            if vendor_name.lower() in clean.lower():
                clean = None
                break
        if clean:
            notes.append(clean)

    return MethodPricing(
        tiers=tiers,
        lead_time=LEAD_TIMES["digital"],
        notes=notes,
    )


def _extract_flexo_pricing(
    result: dict,
    quantities: list[int],
    margin_pct: float = DEFAULT_MARGIN_PCT,
) -> Optional[MethodPricing]:
    """
    Extract flexographic pricing from predict() result.
    Applies margin and strips all internal data.
    """
    predictions = result.get("predictions", [])
    if not predictions:
        return None

    tiers = []
    for pred in predictions:
        cost = pred.get("unit_price", 0)
        if cost is None or cost <= 0:
            continue
        qty = pred["quantity"]
        sell_unit = round(_apply_margin(cost, margin_pct), 4)
        tiers.append(TierPrice(
            quantity=qty,
            unit_price=round(sell_unit, 4),
            total_price=round(sell_unit * qty, 2),
        ))

    if not tiers:
        return None

    notes = ["Plate fee: $400/color"]

    return MethodPricing(
        tiers=tiers,
        lead_time=LEAD_TIMES["flexographic"],
        notes=notes,
    )


def _extract_tedpack_pricing(
    result: dict,
    shipping_method: str,
    quantities: list[int],
    margin_pct: float = DEFAULT_MARGIN_PCT,
) -> Optional[MethodPricing]:
    """
    Extract TedPack air or ocean pricing from predict() result.
    TedPack returns both air_unit_price and ocean_unit_price in a single call.
    Applies margin and strips all internal data.

    Args:
        shipping_method: "air" or "ocean"
    """
    predictions = result.get("predictions", [])
    if not predictions:
        return None

    price_key = f"{shipping_method}_unit_price"

    tiers = []
    for pred in predictions:
        cost = pred.get(price_key)
        if cost is None or cost <= 0:
            continue
        qty = pred["quantity"]
        sell_unit = round(_apply_margin(cost, margin_pct), 4)
        tiers.append(TierPrice(
            quantity=qty,
            unit_price=round(sell_unit, 4),
            total_price=round(sell_unit * qty, 2),
        ))

    if not tiers:
        return None

    lead_time = LEAD_TIMES.get(shipping_method, "Contact for estimate")
    notes = ["Plate fee: $150/color"]

    return MethodPricing(
        tiers=tiers,
        lead_time=lead_time,
        notes=notes,
    )


def generate_instant_quote(
    req: InstantQuoteRequest,
    margin_pct: float = DEFAULT_MARGIN_PCT,
) -> dict:
    """
    Generate an instant quote across all 4 print methods.

    Makes 3 calls to QuotePredictor.predict():
      1. Digital (print_method="Digital") -> routes to Internal or Ross
      2. Flexographic (print_method="Flexographic") -> routes to Dazpak
      3. TedPack (vendor_override="tedpack") -> returns both air and ocean

    Returns a dict suitable for InstantQuoteResponse (after sanitization).
    """
    predictor = get_predictor()
    specs = _build_internal_specs(req)
    quantities = sorted(req.quantities)

    result = {
        "digital": None,
        "flexographic": None,
        "international_air": None,
        "international_ocean": None,
    }

    # 1. Digital quote
    try:
        digital_specs = {**specs, "print_method": "Digital"}
        digital_result = predictor.predict(digital_specs, quantities)
        result["digital"] = _extract_digital_pricing(
            digital_result, quantities, margin_pct
        )
    except Exception as e:
        logger.error(f"Digital prediction failed: {e}")

    # 2. Flexographic quote
    try:
        flexo_specs = {**specs, "print_method": "Flexographic"}
        flexo_result = predictor.predict(flexo_specs, quantities)
        result["flexographic"] = _extract_flexo_pricing(
            flexo_result, quantities, margin_pct
        )
    except Exception as e:
        logger.error(f"Flexographic prediction failed: {e}")

    # 3. TedPack (Gravure) — one call returns both air and ocean
    try:
        tedpack_result = predictor.predict(specs, quantities, vendor_override="tedpack")
        result["international_air"] = _extract_tedpack_pricing(
            tedpack_result, "air", quantities, margin_pct
        )
        result["international_ocean"] = _extract_tedpack_pricing(
            tedpack_result, "ocean", quantities, margin_pct
        )
    except Exception as e:
        logger.error(f"TedPack prediction failed: {e}")

    return result
