"""
Vendor routing logic — determines Dazpak vs Ross vs Internal vs TedPack
based on print method, print width (web width), and order quantities.

Routing rules:
  - Flexographic → Dazpak (MOQ 35K per SKU)
  - Digital + web width ≥ 12" → Ross
  - Digital + web width < 12" → Internal (HP 6900 in-house)
  - Gravure → TedPack (manual selection only)
"""
from config.settings import (
    DAZPAK_MIN_ORDER_QTY,
    ROSS_MIN_PRINT_WIDTH_INCHES,
    INTERNAL_MAX_WEB_WIDTH,
    TEDPACK_MIN_ORDER_QTY,
)


def calculate_print_width(height: float, gusset: float = 0) -> float:
    """Calculate print/web width: Height × 2 + Gusset (inches)."""
    return height * 2 + gusset


def check_ross_eligibility(height: float, gusset: float = 0) -> tuple[bool, str]:
    """Ross only accepts print width > 12"."""
    pw = calculate_print_width(height, gusset)
    if pw > ROSS_MIN_PRINT_WIDTH_INCHES:
        return True, f"Print width {pw:.2f}\" > 12\" — eligible for Ross"
    return False, f"Print width {pw:.2f}\" ≤ 12\" — does NOT meet Ross minimum"


def check_internal_eligibility(height: float, gusset: float = 0) -> tuple[bool, str]:
    """Internal (HP 6900) handles web width ≤ 12"."""
    pw = calculate_print_width(height, gusset)
    if pw <= INTERNAL_MAX_WEB_WIDTH:
        return True, f"Print width {pw:.2f}\" ≤ 12\" — eligible for Internal (HP 6900)"
    return False, f"Print width {pw:.2f}\" > 12\" — too wide for Internal"


def check_dazpak_eligibility(quantities: list[int]) -> tuple[bool, str]:
    """Dazpak requires minimum 35,000 units per SKU."""
    eligible_qtys = [q for q in quantities if q >= DAZPAK_MIN_ORDER_QTY]
    if eligible_qtys:
        return True, f"{len(eligible_qtys)}/{len(quantities)} tiers meet Dazpak MOQ ({DAZPAK_MIN_ORDER_QTY:,})"
    return False, f"No quantities meet Dazpak MOQ of {DAZPAK_MIN_ORDER_QTY:,} units"


def check_tedpack_eligibility(quantities: list[int]) -> tuple[bool, str]:
    """TedPack always eligible (manual select), but warn on very low quantities."""
    below_moq = [q for q in quantities if q < TEDPACK_MIN_ORDER_QTY]
    if below_moq:
        return True, f"⚠ {len(below_moq)} tier(s) below TedPack observed minimum of {TEDPACK_MIN_ORDER_QTY:,}"
    return True, f"All tiers meet TedPack minimum of {TEDPACK_MIN_ORDER_QTY:,}"


def route_vendor(print_method: str, height: float, gusset: float,
                 quantities: list[int]) -> dict:
    """
    Full vendor routing decision.

    Returns:
        {
            "vendor": "dazpak" | "ross" | "internal" | "tedpack",
            "print_method": "flexographic" | "digital" | "gravure",
            "print_width": float,
            "reason": str,
            "ross_eligible": bool,
            "dazpak_eligible": bool,
            "internal_eligible": bool,
            "tedpack_eligible": bool,
            "warnings": [str]
        }
    """
    pw = calculate_print_width(height, gusset)
    ross_ok, ross_msg = check_ross_eligibility(height, gusset)
    internal_ok, internal_msg = check_internal_eligibility(height, gusset)
    daz_ok, daz_msg = check_dazpak_eligibility(quantities)
    ted_ok, ted_msg = check_tedpack_eligibility(quantities)
    warnings = []

    # Explicit print method selection
    if print_method.lower() == "gravure":
        vendor = "tedpack"
        reason = "User selected Gravure → TedPack"
        if "⚠" in ted_msg:
            warnings.append(ted_msg)

    elif print_method.lower() == "flexographic":
        vendor = "dazpak"
        reason = "User selected Flexographic → Dazpak"
        if not daz_ok:
            warnings.append(f"⚠ {daz_msg}")

    elif print_method.lower() == "digital":
        # Digital routing: web width determines Internal vs Ross
        if pw <= INTERNAL_MAX_WEB_WIDTH:
            vendor = "internal"
            reason = f"Digital + print width {pw:.2f}\" ≤ 12\" → Internal (HP 6900)"
        else:
            vendor = "ross"
            reason = f"Digital + print width {pw:.2f}\" > 12\" → Ross"

    else:
        # Auto-route (TedPack is manual-only, never auto-routed)
        if daz_ok and max(quantities, default=0) >= DAZPAK_MIN_ORDER_QTY:
            vendor = "dazpak"
            reason = f"Auto: high volume ({max(quantities):,}) → Dazpak Flexographic"
        elif internal_ok:
            vendor = "internal"
            reason = f"Auto: print width {pw:.1f}\" ≤ 12\" → Internal (HP 6900)"
        elif ross_ok:
            vendor = "ross"
            reason = f"Auto: print width {pw:.1f}\" > 12\" → Ross Digital"
        else:
            vendor = "internal"
            reason = "Auto: defaulting to Internal for smaller runs"

    pm_map = {"dazpak": "flexographic", "ross": "digital",
              "internal": "digital", "tedpack": "gravure"}

    return {
        "vendor": vendor,
        "print_method": pm_map.get(vendor, "digital"),
        "print_width": pw,
        "reason": reason,
        "ross_eligible": ross_ok,
        "dazpak_eligible": daz_ok,
        "internal_eligible": internal_ok,
        "tedpack_eligible": ted_ok,
        "warnings": warnings,
    }
