"""
Deterministic Internal Calculator v5 — HP 6900 Cost Engine.

Replaces the ML model for Internal vendor (digital ≤12" web width).
Reverse-engineered from Label Traxx press/equipment/stock configuration
and validated at 7.9% MAPE against 285 cost-only estimate rows.

Integration point: called by QuotePredictor.predict() when vendor = "internal".
"""

import math
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONSTANTS — from Label Traxx screenshots & Production tabs
# ═══════════════════════════════════════════════════════════════════

# ── Substrates ($/MSI, all run at 13" stock width) ──
SUBSTRATES = {
    "CLR PET":     0.4150,  # Stock 199
    "CLR_PET":     0.4150,  # Canonical name from settings.py
    "MET PET":     0.4350,  # Stock 201
    "MET_PET":     0.4350,  # Canonical name
    "WHT MET PET": 0.4350,  # Stock 206
    "WHT_MET_PET": 0.4350,  # Canonical name
    "ALOX PET":    0.4890,  # Stock 278
    "ALOX_PET":    0.4890,  # Canonical name
    "HB CLR PET":  0.5460,  # Stock 216
    "HB_CLR_PET":  0.5460,  # Canonical name
    "CUSTOM":      0.4350,  # Default to MET PET pricing
}

# ── Laminates ($/MSI, all run at 13" stock width) ──
LAMINATES = {
    "Matte":            0.1790,  # Stock 286
    "Matte Laminate":   0.1790,
    "Matte Lam":        0.1790,
    "Gloss":            0.1600,  # Stock 193
    "Gloss Laminate":   0.1600,
    "Soft Touch":       0.3500,  # Stock 195
    "Soft Touch Laminate": 0.3500,
    "None":             0.0,
    "N/A":              0.0,
}

# ── Zippers ($/MSI, run at their own width) ──
ZIPPERS = {
    "CR Zipper":                       {"width": 0.95,  "cost_per_msi": 5.2587},  # Stock 174
    "Standard CR":                     {"width": 0.95,  "cost_per_msi": 5.2587},
    "Presto CR Zipper":                {"width": 0.95,  "cost_per_msi": 5.2587},
    "Double Profile Non-CR":           {"width": 0.394, "cost_per_msi": 2.6734},  # Stock 176
    "Double Profile - Non CR Zipper":  {"width": 0.394, "cost_per_msi": 2.6734},
    "Single Profile Non-CR":           {"width": 0.394, "cost_per_msi": 2.6734},
    "Single Profile - Non CR Zipper":  {"width": 0.394, "cost_per_msi": 2.6734},
    "Non-CR Zipper":                   {"width": 0.394, "cost_per_msi": 2.6734},
    "No Zipper":                       {"width": 0,     "cost_per_msi": 0},
    "None":                            {"width": 0,     "cost_per_msi": 0},
}

STOCK_WIDTH = 13.0  # inches — ALWAYS 13" for HP and Thermo

# ── HP 6900 (Stage 1) ──
HP_RATE = 216.0       # $/hr (all color counts)
HP_SETUP_HRS = 0.25   # makeready hours
HP_SETUP_FT = 100     # setup length in feet
HP_SPOILAGE = 0.02    # 2% flat (WS6000 series)
HP_SHEETS_PER_MIN = 24.5  # fixed sheets/min
HP_CLICK_CMYKOVG = 0.0107  # $/click (×2 per sheet)
HP_CLICK_WHITE = 0.0095    # $/click (×2 per sheet)
HP_PRIMING = 0.04     # $/MSI in-line priming
HP_PITCH = 0.125      # inches per gear tooth
HP_MAX_REPEAT = 38.0  # inches
HP_MAX_GEAR = int(HP_MAX_REPEAT / HP_PITCH)  # 304

# Default color config: 4 CMYKOVG + 1 Premium White
# NOTE: WHT MET PET already has an opaque white base in the substrate,
# so it does NOT use the Premium White ink channel on the HP 6900.
DEFAULT_CMYKOVG_COLORS = 4
DEFAULT_WHITE_COLORS = 1

# Substrates that have a built-in white/opaque base and do NOT need white ink
NO_WHITE_INK_SUBSTRATES = {
    "WHT MET PET", "WHT_MET_PET",
    "WHT MET PET (White Metallic)",  # UI display name variant
}

# ── Thermo Laminator (Stage 2) ──
THERMO_RATE = 45.0    # $/hr
THERMO_SETUP_FT = 25  # from Set Up Options screenshot
# Speed: 100 ft/min for ≤3,500ft, 120 ft/min for >3,500ft

# ── Suncentre Poucher SCSG-600XL (Stage 3) ──
POUCHER_RATE = 200.0           # $/hr
POUCHER_SEALER_PER_MSI = 0.02  # $/MSI
POUCHER_SEALER_MIN = 5.00      # minimum sealer cost

# Poucher spoilage & speed table (12 levels, from screenshot)
POUCHER_SPEED_TABLE = [
    (0,      250,     0.07, 14),
    (251,    500,     0.07, 18),
    (501,    1250,    0.065, 20),
    (1251,   2500,    0.06, 30),
    (2501,   5000,    0.055, 35),
    (5001,   12500,   0.05, 40),
    (12501,  25000,   0.045, 40),
    (25001,  50000,   0.04, 40),
    (50001,  125000,  0.035, 40),
    (125001, 250000,  0.03, 40),
    (250001, 500000,  0.025, 40),
    (500001, 1000000, 0.02, 40),
]

# Poucher User Defined Options (from screenshot)
POUCHER_UDO = {
    # Seal types
    "Stand Up Pouch":     {"mr": 0.65, "setup_ft": 300, "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "Stand Up":           {"mr": 0.65, "setup_ft": 300, "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "3 Side Seal":        {"mr": 0.60, "setup_ft": 200, "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "3-Side Seal":        {"mr": 0.60, "setup_ft": 200, "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "3 Side Bottom Fill": {"mr": 0.60, "setup_ft": 200, "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "3 Side Top Fill":    {"mr": 0.60, "setup_ft": 200, "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "2 Side Seal":        {"mr": 0.50, "setup_ft": 150, "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "Cube":               {"mr": 1.00, "setup_ft": 250, "speed_chg": 0.0,   "spoilage_chg": 0.0},
    # Zippers
    "CR Zipper":          {"mr": 0.08, "setup_ft": 0,   "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "Non-CR Zipper":      {"mr": 1.00, "setup_ft": 0,   "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "No Zipper":          {"mr": 0.03, "setup_ft": 0,   "speed_chg": 0.05,  "spoilage_chg": 0.0},
    # Features
    "Hole Punch":         {"mr": 0.10, "setup_ft": 0,   "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "Tear Notch":         {"mr": 0.10, "setup_ft": 50,  "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "Rounded Corners":    {"mr": 0.12, "setup_ft": 25,  "speed_chg": 0.0,   "spoilage_chg": 0.0},
    "Second Web":         {"mr": 0.33, "setup_ft": 100, "speed_chg": 0.0,   "spoilage_chg": 0.025},
    "Insert Gusset":      {"mr": 0.25, "setup_ft": 100, "speed_chg": 0.0,   "spoilage_chg": 0.025},
    "Die Cut Station":    {"mr": 1.00, "setup_ft": 250, "speed_chg": -0.25, "spoilage_chg": 0.05},
    "Calyx Cube":         {"mr": 1.00, "setup_ft": 250, "speed_chg": -0.25, "spoilage_chg": 0.0},
    "Eco - 100% Recyc":   {"mr": 0.00, "setup_ft": 0,   "speed_chg": -0.10, "spoilage_chg": 0.0},
    "Non-Calyx Dieline":  {"mr": 0.00, "setup_ft": 200, "speed_chg": 0.0,   "spoilage_chg": 0.0},
}

# ── Embellishment costs (per bag, estimated from historical quotes) ──
EMBELLISHMENT_COSTS = {
    "Hot Stamp (Gold)":  0.015,  # $/bag
    "Hot Stamp (Silver)": 0.015,
    "Embossing":         0.010,
    "Foil":              0.015,  # Consolidated UI name — same as Hot Stamp
    "Spot UV":           0.012,
    "None":              0.0,
    "N/A":               0.0,
}

# Combined spoilage table (all 3 stages combined)
COMBINED_SPOILAGE_TABLE = [
    (0,     2000,  0.108),
    (2001,  3500,  0.103),
    (3501,  7000,  0.098),
    (7001,  15000, 0.092),
    (15001, 30000, 0.087),
    (30001, 55000, 0.082),
    (55001, 999999999, 0.077),
]

# Packaging cost per K (from Est 6774)
PACKAGING_CARTON_PER_K = 3.50
PACKAGING_PACK_PER_K = 10.196
PACKAGING_WRAP_PER_K = 0.16


# ═══════════════════════════════════════════════════════════════════
# LAYOUT LOGIC
# ═══════════════════════════════════════════════════════════════════

def calc_layout(width, height, gusset):
    """
    Calculate HP Indigo press layout.

    Key insight from LT screenshots:
    - Width goes in the "around" (repeat) direction
    - Print width (H*2 + G) goes in the "across" direction
    - no_around = floor(repeat_in / width)
    - Gear teeth selected to maximize no_around
    - repeat_in = gear_teeth * 0.125 (pitch)

    Returns: (no_across, no_around, gear_teeth, repeat_in)
    """
    # No. across is always 1 for flexpack
    no_across = 1

    # Select gear teeth to maximize no_around
    best_gear = None
    best_around = 0

    for gear in range(1, HP_MAX_GEAR + 1):
        repeat = gear * HP_PITCH
        around = int(repeat / width)
        if around > best_around and repeat <= HP_MAX_REPEAT:
            best_around = around
            best_gear = gear

    repeat_in = best_gear * HP_PITCH

    return no_across, best_around, best_gear, repeat_in


def _get_combined_spoilage(stock_length_ft):
    """Look up combined spoilage % from the stock_length-based table."""
    for lo, hi, spoilage in COMBINED_SPOILAGE_TABLE:
        if lo <= stock_length_ft <= hi:
            return spoilage
    return 0.077  # default for very long runs


def _get_poucher_speed_and_spoilage(run_length_ft):
    """Look up poucher speed and spoilage from the 12-level table."""
    for lo, hi, spoilage, speed in POUCHER_SPEED_TABLE:
        if lo <= run_length_ft <= hi:
            return speed, spoilage
    return 40, 0.02  # default for very long runs


def _calc_msi(width_in, length_ft):
    """Calculate MSI (thousand square inches) from width and length."""
    return width_in * length_ft * 12 / 1000


# ═══════════════════════════════════════════════════════════════════
# MAIN CALCULATOR — PUBLIC API
# ═══════════════════════════════════════════════════════════════════

def calculate_internal_cost(width, height, gusset, quantity, substrate, finish,
                            seal_type, zipper, tear_notch="Standard",
                            hole_punch="None", corners="Rounded",
                            gusset_detail="K-Seal",
                            embellishment="None",
                            cmykovg_colors=DEFAULT_CMYKOVG_COLORS,
                            white_colors=None):
    """
    Calculate the production cost for one Internal (HP 6900) bag spec
    at one quantity tier.

    Args:
        width, height, gusset: Bag dimensions in inches
        quantity: Number of bags
        substrate: Substrate key (matches SUBSTRATES dict)
        finish: Finish key (matches LAMINATES dict)
        seal_type: Seal type (Stand Up, 3 Side Seal, etc.)
        zipper: Zipper type or "None"/"No Zipper"
        tear_notch: "Standard" or "None"
        hole_punch: "Standard" or "None"
        corners: "Rounded" or "Straight"
        gusset_detail: "K-Seal", "Plow Bottom", "Side Gusset", etc.
        embellishment: "None", "Foil", "Spot UV", etc.
        cmykovg_colors: Number of CMYKOVG ink colors (default 4)
        white_colors: Number of white ink colors (None = auto-detect from substrate)

    Returns:
        dict with keys: quantity, total_cost, unit_cost, layout, components
        OR dict with "error" key if layout is invalid
    """

    # ── Substrate-aware white ink override ──
    # WHT MET PET has a built-in opaque white base, so no Premium White ink needed.
    # When white_colors is None (default), auto-detect based on substrate.
    if white_colors is None:
        if substrate in NO_WHITE_INK_SUBSTRATES:
            white_colors = 0
        else:
            white_colors = DEFAULT_WHITE_COLORS

    # ── Layout ──
    no_across, no_around, gear_teeth, repeat_in = calc_layout(width, height, gusset)
    repeat_ft = repeat_in / 12.0
    labels_per_cycle = no_across * no_around

    if labels_per_cycle == 0:
        return {"error": f"Invalid layout: {width}W × {height}H × {gusset}G → 0 labels/cycle"}

    # ── Good sheets needed ──
    good_sheets = math.ceil(quantity / labels_per_cycle)

    # ── Poucher UDO setup lengths (needed for frame calc) ──
    poucher_setup_ft = 0
    poucher_mr_hrs = 0
    poucher_speed_mult = 1.0
    poucher_add_spoilage = 0.0

    # Seal type
    seal_key = seal_type
    if seal_key in POUCHER_UDO:
        udo = POUCHER_UDO[seal_key]
        poucher_setup_ft += udo["setup_ft"]
        poucher_mr_hrs += udo["mr"]
        poucher_speed_mult *= (1 + udo["speed_chg"])
        poucher_add_spoilage += udo["spoilage_chg"]

    # Zipper
    if zipper and zipper not in ("None", "No Zipper"):
        zip_key = zipper if zipper in POUCHER_UDO else (
            "CR Zipper" if "CR" in zipper else "Non-CR Zipper"
        )
        if zip_key in POUCHER_UDO:
            udo = POUCHER_UDO[zip_key]
            poucher_setup_ft += udo["setup_ft"]
            poucher_mr_hrs += udo["mr"]
            poucher_speed_mult *= (1 + udo["speed_chg"])
            poucher_add_spoilage += udo["spoilage_chg"]
    else:
        # No Zipper UDO
        if "No Zipper" in POUCHER_UDO:
            udo = POUCHER_UDO["No Zipper"]
            poucher_setup_ft += udo["setup_ft"]
            poucher_mr_hrs += udo["mr"]
            poucher_speed_mult *= (1 + udo["speed_chg"])
            poucher_add_spoilage += udo["spoilage_chg"]

    # Tear notch
    if tear_notch and tear_notch not in ("None", "N/A"):
        if "Tear Notch" in POUCHER_UDO:
            udo = POUCHER_UDO["Tear Notch"]
            poucher_setup_ft += udo["setup_ft"]
            poucher_mr_hrs += udo["mr"]

    # Hole punch
    if hole_punch and hole_punch not in ("None", "N/A"):
        if "Hole Punch" in POUCHER_UDO:
            udo = POUCHER_UDO["Hole Punch"]
            poucher_setup_ft += udo["setup_ft"]
            poucher_mr_hrs += udo["mr"]

    # Corners
    if corners and corners == "Rounded":
        if "Rounded Corners" in POUCHER_UDO:
            udo = POUCHER_UDO["Rounded Corners"]
            poucher_setup_ft += udo["setup_ft"]
            poucher_mr_hrs += udo["mr"]

    # Gusset detail — Insert Gusset only for Side Gusset / Flat Bottom
    if gusset_detail and gusset_detail in (
        "Side Gusset", "Flat Bottom", "Flat Bottom / Side Gusset"
    ):
        if "Insert Gusset" in POUCHER_UDO:
            udo = POUCHER_UDO["Insert Gusset"]
            poucher_setup_ft += udo["setup_ft"]
            poucher_mr_hrs += udo["mr"]
            poucher_add_spoilage += udo["spoilage_chg"]

    # ── Frame / stock length calculation (iterative) ──
    hp_setup_sheets = math.ceil(HP_SETUP_FT / repeat_ft) if repeat_ft > 0 else 0
    poucher_setup_sheets = math.ceil(poucher_setup_ft / repeat_ft) if repeat_ft > 0 else 0
    total_setup_sheets = hp_setup_sheets + poucher_setup_sheets

    # Iterative: spoilage depends on stock_length which depends on total_frames
    combined_spoilage = 0.10  # initial guess
    for _ in range(5):  # converges fast
        total_frames = math.ceil(good_sheets * (1 + combined_spoilage)) + total_setup_sheets
        stock_length_ft = total_frames * repeat_ft
        combined_spoilage = _get_combined_spoilage(stock_length_ft)

    # Final values
    total_frames = math.ceil(good_sheets * (1 + combined_spoilage)) + total_setup_sheets
    stock_length_ft = total_frames * repeat_ft

    # ═══ STAGE 1: HP 6900 ═══

    # Substrate cost
    sub_rate = SUBSTRATES.get(substrate, 0.4350)
    substrate_msi = _calc_msi(STOCK_WIDTH, stock_length_ft)
    substrate_cost = substrate_msi * sub_rate

    # In-line priming
    priming_cost = substrate_msi * HP_PRIMING

    # Click charges (×2 per sheet, per color)
    total_sheets = total_frames
    cmykovg_clicks = total_sheets * 2 * cmykovg_colors
    white_clicks = total_sheets * 2 * white_colors
    click_cost = cmykovg_clicks * HP_CLICK_CMYKOVG + white_clicks * HP_CLICK_WHITE

    # HP makeready (0.25hr × $125/hr = $31.25 flat)
    hp_makeready_cost = HP_RATE * HP_SETUP_HRS

    # HP run-time
    hp_speed_ftmin = HP_SHEETS_PER_MIN * repeat_ft
    hp_run_length_ft = stock_length_ft - HP_SETUP_FT - poucher_setup_ft
    hp_run_hrs = max(0, hp_run_length_ft / (hp_speed_ftmin * 60)) if hp_speed_ftmin > 0 else 0
    hp_run_cost = hp_run_hrs * HP_RATE

    hp_total = substrate_cost + priming_cost + click_cost + hp_makeready_cost + hp_run_cost

    # ═══ STAGE 2: THERMO LAMINATOR ═══

    lam_rate = LAMINATES.get(finish, 0.0)
    if finish and finish not in ("None", "N/A") and lam_rate > 0:
        lam_msi = _calc_msi(STOCK_WIDTH, stock_length_ft)
        lam_cost = lam_msi * lam_rate

        # Thermo run-time (0 makeready, confirmed)
        thermo_speed = 100 if stock_length_ft <= 3500 else 120
        thermo_run_hrs = stock_length_ft / (thermo_speed * 60)
        thermo_labor = thermo_run_hrs * THERMO_RATE

        thermo_total = lam_cost + thermo_labor
    else:
        thermo_total = 0
        lam_cost = 0
        thermo_labor = 0

    # ═══ STAGE 3: ZIPPER (3rd Stock cost) ═══

    zip_info = ZIPPERS.get(zipper, ZIPPERS["None"])
    if zip_info["width"] > 0:
        zip_msi = _calc_msi(zip_info["width"], stock_length_ft)
        zip_cost = zip_msi * zip_info["cost_per_msi"]
    else:
        zip_cost = 0

    # ═══ STAGE 4: SUNCENTRE POUCHER ═══

    poucher_run_ft = good_sheets * repeat_ft
    poucher_speed, poucher_base_spoilage = _get_poucher_speed_and_spoilage(poucher_run_ft)

    # Apply UDO speed multiplier
    effective_poucher_speed = poucher_speed * poucher_speed_mult

    # Poucher run hours
    poucher_total_run_ft = stock_length_ft
    poucher_run_hrs = (
        poucher_total_run_ft / (effective_poucher_speed * 60)
        if effective_poucher_speed > 0 else 0
    )

    # Poucher labor = makeready + running
    poucher_labor = (poucher_mr_hrs + poucher_run_hrs) * POUCHER_RATE

    # Sealer ink
    sealer_msi = _calc_msi(STOCK_WIDTH, stock_length_ft)
    sealer_cost = max(sealer_msi * POUCHER_SEALER_PER_MSI, POUCHER_SEALER_MIN)

    poucher_total = poucher_labor + sealer_cost

    # ═══ EMBELLISHMENT ═══

    embellishment_per_bag = EMBELLISHMENT_COSTS.get(embellishment, 0.0)
    embellishment_cost = embellishment_per_bag * quantity

    # ═══ PACKAGING ═══

    qty_k = quantity / 1000
    packaging_cost = (PACKAGING_CARTON_PER_K + PACKAGING_PACK_PER_K + PACKAGING_WRAP_PER_K) * qty_k

    # ═══ TOTAL ═══

    total_cost = hp_total + thermo_total + zip_cost + poucher_total + embellishment_cost + packaging_cost
    unit_cost = total_cost / quantity if quantity > 0 else 0

    return {
        "quantity": quantity,
        "total_cost": round(total_cost, 2),
        "unit_cost": round(unit_cost, 6),
        "layout": {
            "no_across": no_across,
            "no_around": no_around,
            "gear_teeth": gear_teeth,
            "repeat_in": round(repeat_in, 3),
            "repeat_ft": round(repeat_ft, 4),
            "labels_per_cycle": labels_per_cycle,
            "good_sheets": good_sheets,
            "total_frames": total_frames,
            "stock_length_ft": round(stock_length_ft, 1),
            "combined_spoilage": combined_spoilage,
        },
        "components": {
            "substrate": round(substrate_cost, 2),
            "priming": round(priming_cost, 2),
            "clicks": round(click_cost, 2),
            "hp_makeready": round(hp_makeready_cost, 2),
            "hp_running": round(hp_run_cost, 2),
            "laminate": round(lam_cost, 2),
            "thermo_labor": round(thermo_labor, 2),
            "zipper": round(zip_cost, 2),
            "poucher_labor": round(poucher_labor, 2),
            "sealer": round(sealer_cost, 2),
            "embellishment": round(embellishment_cost, 2),
            "packaging": round(packaging_cost, 2),
        },
    }


def calculate_internal_quote(specs: dict, quantity_tiers: list[int]) -> dict:
    """
    High-level interface matching QuotePredictor.predict() output format.

    Called by QuotePredictor when vendor = "internal".
    Maps the UI spec field names to calculator parameters, runs
    calculate_internal_cost() for each quantity tier, and returns
    a result dict compatible with _render_results() in app.py.

    Args:
        specs: Dict from Quote Builder with keys like substrate, finish,
               seal_type, zipper, etc.
        quantity_tiers: List of quantities to quote.

    Returns:
        Dict matching the structure of QuotePredictor.predict() output,
        with additional "is_deterministic" and "component_costs" keys.
    """
    width = float(specs.get("width", 0))
    height = float(specs.get("height", 0))
    gusset = float(specs.get("gusset", 0))
    print_width = height * 2 + gusset

    # ── Map UI field names to calculator parameters ──
    # Substrate: UI sends canonical names like "MET_PET"
    substrate = specs.get("substrate", "MET_PET")

    # Finish: UI sends names like "Matte Laminate", "Soft Touch Laminate"
    finish = specs.get("finish", "Matte Laminate")

    # Seal type: UI sends "Stand Up", "3 Side Seal", etc.
    seal_type = specs.get("seal_type", "Stand Up")
    # Map "Stand Up" → "Stand Up Pouch" for calculator
    seal_map = {
        "Stand Up": "Stand Up Pouch",
        "Stand Up Pouch": "Stand Up Pouch",
        "3 Side Seal": "3 Side Seal",
        "3-Side Seal": "3 Side Seal",
        "3 Side Seal - Top Fill": "3 Side Top Fill",
        "3 Side Seal - Bottom Fill": "3 Side Seal",
        "2 Side Seal": "2 Side Seal",
        "2 Side Seal - Top Fill": "2 Side Seal",
        "3 Side Top Fill": "3 Side Top Fill",
        "3 Side Bottom Fill": "3 Side Seal",
        "Cube": "Cube",
    }
    seal_type = seal_map.get(seal_type, seal_type)

    # Zipper: direct match
    zipper = specs.get("zipper", "No Zipper")

    # Tear notch: UI sends "Standard", "Double (2)", "None"
    tear_notch = specs.get("tear_notch", "Standard")
    if tear_notch in ("Double (2)", "2 - Tear Notch"):
        tear_notch = "Standard"  # both trigger the UDO

    # Hole punch: "None", "Round", "Euro" (new UI); old values kept for compat
    hole_punch = specs.get("hole_punch", "None")
    hole_punch_map = {
        "None": "None",
        "N/A": "None",
        # New consolidated UI values
        "Round": "Standard",
        "Euro": "Standard",
        # Old values → same internal key (all trigger the Hole Punch UDO)
        "Standard": "Standard",
        "Round (Butterfly)": "Standard",
        "Euro Slot": "Standard",
        "Sombrero": "Standard",
    }
    hole_punch = hole_punch_map.get(hole_punch, hole_punch)

    # Corners: "Rounded", "Straight"
    corners = specs.get("corner_treatment", "Rounded")

    # Gusset detail / type
    gusset_detail = specs.get("gusset_type", "K Seal")
    gusset_map = {
        "K Seal": "K-Seal",
        "K Seal & Skirt Seal": "K-Seal",
        "Plow Bottom": "Plow Bottom",
        "Flat Bottom / Side Gusset": "Flat Bottom / Side Gusset",
        "None": "K-Seal",
    }
    gusset_detail = gusset_map.get(gusset_detail, gusset_detail)

    # Embellishment: "None", "Foil", "Spot UV" (new UI); old values kept for compat
    embellishment = specs.get("embellishment", "None")
    embellishment_map = {
        "None": "None",
        "N/A": "None",
        # New consolidated UI value
        "Foil": "Foil",
        "Spot UV": "Spot UV",
        # Old values → same internal cost
        "Hot Stamp (Gold)": "Hot Stamp (Gold)",
        "Hot Stamp (Silver)": "Hot Stamp (Silver)",
        "Embossing": "Embossing",
    }
    embellishment = embellishment_map.get(embellishment, embellishment)

    # ── Run calculator for each tier ──
    predictions = []
    component_costs = []  # detailed cost breakdown per tier
    warnings = []

    for qty in quantity_tiers:
        result = calculate_internal_cost(
            width=width,
            height=height,
            gusset=gusset,
            quantity=qty,
            substrate=substrate,
            finish=finish,
            seal_type=seal_type,
            zipper=zipper,
            tear_notch=tear_notch,
            hole_punch=hole_punch,
            corners=corners,
            gusset_detail=gusset_detail,
            embellishment=embellishment,
        )

        if "error" in result:
            warnings.append(result["error"])
            continue

        predictions.append({
            "quantity": qty,
            "unit_price": result["unit_cost"],
            "total_price": result["total_cost"],
            "lower_bound": result["unit_cost"],  # deterministic — no CI
            "upper_bound": result["unit_cost"],  # deterministic — no CI
            "confidence_range": 0.0,
        })

        component_costs.append({
            "quantity": qty,
            **result["components"],
            "total": result["total_cost"],
        })

    # Build cost factor breakdown (for the bar chart)
    # Show component % of total cost at the first quantity tier
    cost_factors = {}
    if component_costs:
        first = component_costs[0]
        total = first["total"]
        component_labels = {
            "substrate": "Substrate Film",
            "priming": "HP Priming",
            "clicks": "HP Click Charges",
            "hp_makeready": "HP Makeready",
            "hp_running": "HP Run Time",
            "laminate": "Laminate Film",
            "thermo_labor": "Thermo Labor",
            "zipper": "Zipper Stock",
            "poucher_labor": "Poucher Labor",
            "sealer": "Sealer Ink",
            "embellishment": "Embellishment",
            "packaging": "Packaging",
        }
        for key, label in component_labels.items():
            val = first.get(key, 0)
            if val > 0 and total > 0:
                cost_factors[label] = {
                    "importance": round(val / total * 100, 1),
                    "value": f"${val:,.2f}",
                }

    # Layout info for first tier
    layout_info = {}
    if predictions:
        first_result = calculate_internal_cost(
            width=width, height=height, gusset=gusset,
            quantity=quantity_tiers[0], substrate=substrate, finish=finish,
            seal_type=seal_type, zipper=zipper, tear_notch=tear_notch,
            hole_punch=hole_punch, corners=corners, gusset_detail=gusset_detail,
            embellishment=embellishment,
        )
        if "layout" in first_result:
            layout_info = first_result["layout"]

    return {
        "vendor": "internal",
        "print_method": "digital",
        "routing_reason": f"Digital, web width {print_width:.1f}\" ≤ 12\" → Internal (HP 6900) — Deterministic Calculator v5",
        "print_width": round(print_width, 3),
        "bag_area": round(width * height, 3),
        "predictions": predictions,
        "cost_factors": cost_factors,
        "model_metrics": {
            "mape": 7.9,  # validated MAPE (clean dataset)
            "method": "Deterministic Calculator v5",
            "training_rows": 285,
        },
        "warnings": warnings,
        "is_deterministic": True,
        "component_costs": component_costs,
        "layout": layout_info,
    }
