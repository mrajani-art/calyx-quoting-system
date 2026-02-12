"""
Vendor routing logic — determines Dazpak vs Ross based on
print method, print width, and order quantities.
"""
from config.settings import DAZPAK_MIN_ORDER_QTY, ROSS_MIN_PRINT_WIDTH_INCHES


def calculate_print_width(height: float, gusset: float = 0) -> float:
    """Calculate print width: Height × 2 + Gusset (inches)."""
    return height * 2 + gusset


def check_ross_eligibility(height: float, gusset: float = 0) -> tuple[bool, str]:
    """
    Check if a job qualifies for Ross (digital).
    Ross only accepts print width > 12".
    """
    pw = calculate_print_width(height, gusset)
    if pw > ROSS_MIN_PRINT_WIDTH_INCHES:
        return True, f"Print width {pw:.2f}\" > 12\" — eligible for Ross"
    return False, f"Print width {pw:.2f}\" ≤ 12\" — does NOT meet Ross minimum"


def check_dazpak_eligibility(quantities: list[int]) -> tuple[bool, str]:
    """
    Check if order quantities meet Dazpak MOQ.
    Dazpak requires minimum 35,000 units per SKU.
    """
    eligible_qtys = [q for q in quantities if q >= DAZPAK_MIN_ORDER_QTY]
    if eligible_qtys:
        return True, f"{len(eligible_qtys)}/{len(quantities)} tiers meet Dazpak MOQ ({DAZPAK_MIN_ORDER_QTY:,})"
    return False, f"No quantities meet Dazpak MOQ of {DAZPAK_MIN_ORDER_QTY:,} units"


def route_vendor(print_method: str, height: float, gusset: float,
                 quantities: list[int]) -> dict:
    """
    Full vendor routing decision.

    Returns:
        {
            "vendor": "dazpak" | "ross",
            "print_method": "flexographic" | "digital",
            "print_width": float,
            "reason": str,
            "ross_eligible": bool,
            "dazpak_eligible": bool,
            "warnings": [str]
        }
    """
    pw = calculate_print_width(height, gusset)
    ross_ok, ross_msg = check_ross_eligibility(height, gusset)
    daz_ok, daz_msg = check_dazpak_eligibility(quantities)
    warnings = []

    # Explicit print method selection
    if print_method.lower() == "flexographic":
        vendor = "dazpak"
        reason = "User selected Flexographic → Dazpak"
        if not daz_ok:
            warnings.append(f"⚠ {daz_msg}")
    elif print_method.lower() == "digital":
        vendor = "ross"
        reason = "User selected Digital → Ross"
        if not ross_ok:
            warnings.append(f"⚠ {ross_msg}")
    else:
        # Auto-route
        if daz_ok and max(quantities, default=0) >= DAZPAK_MIN_ORDER_QTY:
            vendor = "dazpak"
            reason = f"Auto: high volume ({max(quantities):,}) → Dazpak Flexographic"
        elif ross_ok:
            vendor = "ross"
            reason = f"Auto: print width {pw:.1f}\" qualifies → Ross Digital"
        else:
            vendor = "ross"
            reason = "Auto: defaulting to Ross Digital for smaller runs"
            if not ross_ok:
                warnings.append(f"⚠ {ross_msg}")

    return {
        "vendor": vendor,
        "print_method": "flexographic" if vendor == "dazpak" else "digital",
        "print_width": pw,
        "reason": reason,
        "ross_eligible": ross_ok,
        "dazpak_eligible": daz_ok,
        "warnings": warnings,
    }
