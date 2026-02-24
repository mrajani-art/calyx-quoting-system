#!/usr/bin/env python3
"""
Deterministic Internal Calculator v2 — Validation Script
=========================================================
Fetches all internal cost-only quotes from Supabase, runs each through
the deterministic calculator (reverse-engineered from Label Traxx),
and outputs a comparison CSV + summary statistics.

Usage:
    # Set env vars first:
    export SUPABASE_URL="https://dernxirzvawjmdxzxefl.supabase.co"
    export SUPABASE_KEY="your-anon-key"

    python compare_calculator_vs_supabase.py

Output:
    calculator_vs_supabase.csv — row-by-row actual vs calculated
    Console — summary MAPE, median error, breakdowns
"""

import os
import sys
import math
import csv
import json
from typing import Optional

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: Install supabase-py first:  pip install supabase")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — All values from Label Traxx screenshots
# ═══════════════════════════════════════════════════════════════

# --- HP 6900 Press ---
HP_EST_RATE = 125.00          # $/hr (flat, all color counts)
HP_STOCK_WIDTH = 13.0         # inches (FIXED — always 13")
HP_PITCH = 0.125              # inches per gear tooth
HP_MAX_REPEAT = 38.0          # inches (max print repeat)
HP_MIN_REPEAT = 0.5           # inches (min print repeat)
HP_SETUP_HOURS = 0.25         # Job set up make-ready
HP_SETUP_LENGTH_FT = 100      # feet
HP_COPY_CHANGE_HOURS = 0.10   # Ticket hours per copy change
HP_COPY_CHANGE_LENGTH_FT = 30 # feet
HP_SPOILAGE_PCT = 2.0         # flat 2% (WS6000 series)
HP_INLINE_PRIMING = 0.04      # $/MSI
HP_TRIM_WIDTH = 0.5           # inches
HP_CLICK_CHARGE_CMYKOVG = 0.0107   # $/click
HP_CLICK_CHARGE_WHITE = 0.0095     # $/click (White Plus, Premium White, Blank, White for sleeves)
HP_CLICK_MULTIPLIER = 2       # clicks per sheet per color (from job data analysis)
HP_EPM_INK_MARKUP = 0.15      # 15% Enhanced Productivity Mode ink markup

# --- Thermo Laminator ---
THERMO_EST_RATE = 45.00       # $/hr (0 or 1 color)
THERMO_STOCK_WIDTH = 13.0     # inches (FIXED — always 13")
THERMO_PITCH = 0.125          # inches per gear tooth
THERMO_SETUP_LENGTH_FT = 25   # feet (from Set Up Length in screenshot)
THERMO_FIRST_COLOR_MR = 0.30  # Make Ready hours (First Color)
THERMO_STOCK_MR = 0.16        # Make Ready hours (Stock)
THERMO_INK_COST_MSI = 0.0001  # Thermolam ink (negligible)
# Thermo Speed & Spoilage (from screenshot)
THERMO_SPEED_SPOILAGE = [
    # (from_ft, to_ft, spoilage_pct, speed_ft_min)
    (0,    500,   3, 80),
    (501,  2500,  1, 80),
    (2501, 5000,  1, 85),
    (5001, None,  1, 120),  # "5001 to 0" means 5001+
]

# --- Suncentre Poucher SCSG-600XL ---
POUCHER_EST_RATE = 200.00     # $/hr (0 or 1 color)
POUCHER_PITCH = 0.125         # inches per gear tooth
POUCHER_SEALER_INK_MSI = 0.02 # $/MSI sealer ink
POUCHER_SEALER_MIN = 5.00     # min $ for sealer
# Poucher Speed & Spoilage (12 levels from screenshot)
POUCHER_SPEED_SPOILAGE = [
    # (from_ft, to_ft, spoilage_pct, speed_ft_min)
    (0,       250,     7,   14),
    (251,     500,     7,   18),
    (501,     1250,    6.5, 20),
    (1251,    2500,    6,   30),
    (2501,    5000,    5.5, 35),
    (5001,    12500,   5,   40),
    (12501,   25000,   4.5, 40),
    (25001,   50000,   4,   40),
    (50001,   125000,  3.5, 40),
    (125001,  250000,  3,   40),
    (250001,  500000,  2.5, 40),
    (500001,  1000000, 2,   40),
]

# Poucher User Defined Options (from screenshot — 15 rows)
# Each option adds make-ready hours, speed change, spoilage change, setup length
POUCHER_UDO = {
    # key: (make_ready_hrs, wash_up_hrs, speed_change_pct, spoilage_change_pct, setup_length_ft, add_hr_est_rate, add_hr_wip_rate, add_run_length)
    "Stand Up Pouch":   (0.65, 0, 0.0,    0.0, 300, 0, 0, 0),
    "3 Side Seal":      (0.60, 0, 0.0,    0.0, 200, 0, 0, 0),
    "2 Side Seal":      (0.50, 0, 0.0,    0.0, 150, 0, 0, 0),
    "CR Zipper":        (0.08, 0, 0.0,    0.0, 0,   0, 0, 0),
    "Non-CR Zipper":    (1.00, 0, 0.0,    0.0, 0,   0, 0, 0),
    "No Zipper":        (0.03, 0, 5.0,    0.0, 0,   0, 0, 0),
    "Hole Punch":       (0.10, 0, 0.0,    0.0, 0,   0, 0, 0),
    "Tear Notch":       (0.10, 0, 0.0,    0.0, 50,  0, 0, 0),
    "Rounded Corners":  (0.12, 0, 0.0,    0.0, 25,  0, 0, 0),
    "Second Web":       (0.33, 0, 0.0,    2.5, 100, 0, 0, 0),
    "Insert Gusset":    (0.25, 0, 0.0,    2.5, 100, 0, 0, 0),
    "Die Cut Station":  (1.00, 0, -25.0,  5.0, 250, 0, 25, 0),
    "Calyx Cube":       (1.00, 0.25, -25.0, 0.0, 250, 0, 0, 0),
    "Eco - 100% Recyc": (0.00, 0, -10.0,  0.0, 0,   0, 0, 0),
    "Non-Calyx Dieline": (0.00, 0, 0.0,   0.0, 200, 0, 0, 0),
}

# --- HP 6900 User Defined Options ---
HP_UDO = {
    # key: (make_ready_hrs, wash_up_hrs, speed_change_pct, spoilage_change_pct, add_web_width, setup_length_ft, add_hr_est_rate, add_hr_wip_rate, add_run_length)
    "Double Hit White I": (0, 0, -25.0, 0.0, 0, 0, 0, 0, 0),
}

# --- Substrate Costs ($/MSI) ---
SUBSTRATES = {
    "CLR PET":     {"stock_num": 199, "cost_msi": 0.4150, "caliper": 3.5},
    "MET PET":     {"stock_num": 201, "cost_msi": 0.4350, "caliper": 3.5},
    "WHT MET PET": {"stock_num": 206, "cost_msi": 0.4350, "caliper": 3.5},
    "ALOX PET":    {"stock_num": 278, "cost_msi": 0.4890, "caliper": None},
    "HB CLR PET":  {"stock_num": 216, "cost_msi": 0.5460, "caliper": None},
}

# --- Laminate/Finish Costs ($/MSI) ---
LAMINATES = {
    "Matte":      {"stock_num": 286, "cost_msi": 0.1790},
    "Gloss":      {"stock_num": 193, "cost_msi": 0.1600},
    "Soft Touch":  {"stock_num": 195, "cost_msi": 0.3500},
    "None":       {"stock_num": None, "cost_msi": 0.0},
}

# --- Zipper Costs ($/MSI at their own width) ---
ZIPPERS = {
    "CR Zipper":                    {"stock_num": 174, "cost_msi": 5.2587, "width_in": 0.95},
    "Double Profile - Non CR Zipper": {"stock_num": 176, "cost_msi": 2.6734, "width_in": 0.394},
    "Single Profile - Non CR Zipper": {"stock_num": 176, "cost_msi": 2.6734, "width_in": 0.394},
    "None":                         {"stock_num": None, "cost_msi": 0.0, "width_in": 0},
}


# ═══════════════════════════════════════════════════════════════
# CALCULATOR ENGINE
# ═══════════════════════════════════════════════════════════════

def find_best_gear_teeth(bag_width: float, max_repeat: float = HP_MAX_REPEAT, 
                          min_repeat: float = HP_MIN_REPEAT, pitch: float = HP_PITCH) -> dict:
    """
    Find the gear teeth count that maximizes no_around (labels per cycle)
    while staying within press repeat limits.
    
    Returns dict with: gear_teeth, actual_repeat, no_around
    """
    best = {"gear_teeth": 0, "actual_repeat": 0, "no_around": 0, "waste_pct": 100}
    
    min_teeth = max(1, math.ceil(min_repeat / pitch))
    max_teeth = int(max_repeat / pitch)
    
    for teeth in range(min_teeth, max_teeth + 1):
        repeat = teeth * pitch
        no_around = int(repeat / bag_width) if bag_width > 0 else 0
        if no_around < 1:
            continue
        used = no_around * bag_width
        waste = (repeat - used) / repeat * 100
        
        # Prefer higher no_around, then lower waste
        if (no_around > best["no_around"]) or \
           (no_around == best["no_around"] and waste < best["waste_pct"]):
            best = {
                "gear_teeth": teeth,
                "actual_repeat": repeat,
                "no_around": no_around,
                "waste_pct": waste,
            }
    
    return best


def get_speed_spoilage(run_length_ft: float, table: list) -> tuple:
    """Look up speed and spoilage from a tiered table. Returns (spoilage_pct, speed_ft_min)."""
    for (from_ft, to_ft, spoilage, speed) in table:
        if to_ft is None:
            if run_length_ft >= from_ft:
                return (spoilage, speed)
        elif from_ft <= run_length_ft <= to_ft:
            return (spoilage, speed)
    # Default to last tier
    return (table[-1][2], table[-1][3])


def calculate_internal_cost(
    width: float,           # bag width in inches
    height: float,          # bag height in inches  
    gusset: float,          # gusset depth in inches
    substrate: str,         # e.g. "MET PET", "CLR PET"
    finish: str,            # e.g. "Matte", "Gloss", "Soft Touch", "None"
    seal_type: str,         # e.g. "Stand Up Pouch", "3 Side Seal", etc.
    zipper: str,            # e.g. "CR Zipper", "None"
    tear_notch: str,        # e.g. "Standard", "None"
    hole_punch: str,        # e.g. "None", "Round", "Euro"
    corners: str,           # e.g. "Rounded", "Straight"
    quantity: int,          # number of bags
    cmykovg_colors: int = 4,  # number of CMYKOVG color channels
    white_colors: int = 1,    # number of white/premium white channels
    white_coverage: float = 80,  # white coverage percentage
    gusset_type: str = "K-Seal",  # gusset detail
    double_hit_white: bool = False,  # HP UDO: Double Hit White
) -> dict:
    """
    Calculate the deterministic production cost per unit for an internal HP 6900 job.
    
    Returns dict with cost breakdown and total cost_per_unit.
    """
    result = {
        "quantity": quantity,
        "width": width,
        "height": height, 
        "gusset": gusset,
        "substrate": substrate,
        "finish": finish,
        "seal_type": seal_type,
        "zipper": zipper,
    }
    
    # ─── Layout Calculation ───
    trim = 0.125  # left + right trim per side
    size_across = height * 2 + gusset + 0.25  # 0.25" total trim (0.125 each side)
    stock_width = HP_STOCK_WIDTH
    no_across = max(1, int(stock_width / size_across))
    
    gear = find_best_gear_teeth(width)
    gear_teeth = gear["gear_teeth"]
    actual_repeat = gear["actual_repeat"]
    no_around = gear["no_around"]
    labels_per_cycle = no_across * no_around
    
    if labels_per_cycle == 0:
        result["error"] = "Cannot fit any labels on press"
        result["cost_per_unit"] = None
        return result
    
    result["layout"] = {
        "size_across": size_across,
        "no_across": no_across,
        "gear_teeth": gear_teeth,
        "actual_repeat_in": actual_repeat,
        "no_around": no_around,
        "labels_per_cycle": labels_per_cycle,
    }
    
    # ─── Sheets (copies) needed ───
    good_sheets = math.ceil(quantity / labels_per_cycle)
    spoilage_sheets = math.ceil(good_sheets * HP_SPOILAGE_PCT / 100)
    total_sheets = good_sheets + spoilage_sheets
    
    # Setup length in sheets
    repeat_ft = actual_repeat / 12
    if repeat_ft > 0:
        setup_sheets = math.ceil(HP_SETUP_LENGTH_FT / repeat_ft)
    else:
        setup_sheets = 0
    
    total_sheets_with_setup = total_sheets + setup_sheets
    
    # Run length in feet
    run_length_ft = total_sheets_with_setup * repeat_ft
    
    result["hp_press"] = {
        "good_sheets": good_sheets,
        "spoilage_sheets": spoilage_sheets,
        "setup_sheets": setup_sheets,
        "total_sheets": total_sheets_with_setup,
        "run_length_ft": run_length_ft,
    }
    
    # ─── STAGE 1: HP 6900 Costs ───
    
    # 1a. Click charges
    total_cmykovg_clicks = total_sheets_with_setup * HP_CLICK_MULTIPLIER * cmykovg_colors
    total_white_clicks = total_sheets_with_setup * HP_CLICK_MULTIPLIER * white_colors
    
    # Double Hit White doubles the white clicks
    if double_hit_white:
        total_white_clicks *= 2
    
    click_cost = (total_cmykovg_clicks * HP_CLICK_CHARGE_CMYKOVG + 
                  total_white_clicks * HP_CLICK_CHARGE_WHITE)
    
    # 1b. Material cost (substrate)
    sub_info = SUBSTRATES.get(substrate, SUBSTRATES["MET PET"])
    # MSI = stock_width (in) × run_length (ft) × 12 (in/ft) / 1000
    hp_msi = stock_width * run_length_ft * 12 / 1000
    substrate_cost = hp_msi * sub_info["cost_msi"]
    
    # 1c. In-line priming
    priming_cost = hp_msi * HP_INLINE_PRIMING
    
    # 1d. Labor (setup only — Omit Make Ready and Omit Wash Up are checked)
    hp_labor_cost = HP_SETUP_HOURS * HP_EST_RATE
    
    # 1e. HP UDO adjustments
    hp_speed_change = 0
    if double_hit_white:
        hp_speed_change += HP_UDO["Double Hit White I"][2]  # -25% speed
    
    hp_total = click_cost + substrate_cost + priming_cost + hp_labor_cost
    
    result["hp_costs"] = {
        "click_cost": click_cost,
        "cmykovg_clicks": total_cmykovg_clicks,
        "white_clicks": total_white_clicks,
        "substrate_cost": substrate_cost,
        "substrate_msi": hp_msi,
        "priming_cost": priming_cost,
        "labor_cost": hp_labor_cost,
        "total": hp_total,
    }
    
    # ─── STAGE 2: Thermo Laminator Costs ───
    lam_info = LAMINATES.get(finish, LAMINATES.get("None"))
    
    if lam_info and lam_info["cost_msi"] > 0:
        # Laminate runs at same width and same run length
        thermo_run_ft = run_length_ft  # same length as HP output
        
        # Add setup length
        thermo_total_ft = thermo_run_ft + THERMO_SETUP_LENGTH_FT
        
        # Spoilage
        thermo_spoilage_pct, thermo_speed = get_speed_spoilage(thermo_total_ft, THERMO_SPEED_SPOILAGE)
        thermo_spoilage_ft = thermo_total_ft * thermo_spoilage_pct / 100
        thermo_final_ft = thermo_total_ft + thermo_spoilage_ft
        
        # Laminate material
        thermo_msi = THERMO_STOCK_WIDTH * thermo_final_ft * 12 / 1000
        laminate_material_cost = thermo_msi * lam_info["cost_msi"]
        
        # Thermo ink (negligible)
        thermo_ink_cost = thermo_msi * THERMO_INK_COST_MSI
        
        # Labor: First Color MR + Stock MR
        thermo_mr_hours = THERMO_FIRST_COLOR_MR + THERMO_STOCK_MR
        # Run time
        thermo_run_hours = thermo_final_ft / thermo_speed / 60 if thermo_speed > 0 else 0
        thermo_labor_cost = (thermo_mr_hours + thermo_run_hours) * THERMO_EST_RATE
        
        thermo_total = laminate_material_cost + thermo_ink_cost + thermo_labor_cost
    else:
        thermo_total = 0
        laminate_material_cost = 0
        thermo_labor_cost = 0
        thermo_msi = 0
    
    result["thermo_costs"] = {
        "laminate_material": laminate_material_cost,
        "labor": thermo_labor_cost,
        "total": thermo_total,
    }
    
    # ─── STAGE 3: Suncentre Poucher Costs ───
    
    # Poucher run length = same as HP run length (it's processing the same web)
    poucher_run_ft = run_length_ft
    
    # Determine which UDOs are active based on bag specs
    active_udos = []
    
    # Seal type
    if seal_type in POUCHER_UDO:
        active_udos.append(seal_type)
    elif "Stand Up" in (seal_type or ""):
        active_udos.append("Stand Up Pouch")
    elif "3 Side" in (seal_type or "") and "Bottom" in (seal_type or ""):
        active_udos.append("3 Side Seal")
    elif "3 Side" in (seal_type or "") and "Top" in (seal_type or ""):
        active_udos.append("3 Side Seal")
    elif "2 Side" in (seal_type or ""):
        active_udos.append("2 Side Seal")
    else:
        active_udos.append("Stand Up Pouch")  # default
    
    # Zipper
    zipper_norm = (zipper or "").strip()
    if "CR" in zipper_norm and "Non" not in zipper_norm:
        active_udos.append("CR Zipper")
    elif "Non" in zipper_norm or "Single" in zipper_norm or "Double" in zipper_norm:
        active_udos.append("Non-CR Zipper")
    elif zipper_norm == "" or zipper_norm == "None" or zipper_norm is None:
        active_udos.append("No Zipper")
    else:
        active_udos.append("No Zipper")
    
    # Tear notch
    tear_norm = (tear_notch or "").strip()
    if tear_norm and tear_norm != "None":
        active_udos.append("Tear Notch")
    
    # Hole punch
    hole_norm = (hole_punch or "").strip()
    if hole_norm and hole_norm != "None":
        active_udos.append("Hole Punch")
    
    # Corners
    corners_norm = (corners or "").strip()
    if corners_norm == "Rounded":
        active_udos.append("Rounded Corners")
    
    # Gusset — if Stand Up Pouch, gusset is integral. But "Insert Gusset" is 
    # a separate UDO for specific configurations
    # For now, assume gusset handling is covered by seal type
    
    # Sum up UDO effects
    total_mr_hours = 0
    total_washup_hours = 0
    total_speed_change = 0
    total_spoilage_change = 0
    total_setup_length_ft = 0
    total_add_hr_est = 0
    
    for udo_name in active_udos:
        if udo_name in POUCHER_UDO:
            udo = POUCHER_UDO[udo_name]
            total_mr_hours += udo[0]
            total_washup_hours += udo[1]
            total_speed_change += udo[2]
            total_spoilage_change += udo[3]
            total_setup_length_ft += udo[4]
            total_add_hr_est += udo[5]
    
    # Add setup length to run
    poucher_total_ft = poucher_run_ft + total_setup_length_ft
    
    # Get base speed and spoilage
    base_spoilage_pct, base_speed = get_speed_spoilage(poucher_total_ft, POUCHER_SPEED_SPOILAGE)
    
    # Apply UDO adjustments
    adjusted_speed = base_speed * (1 + total_speed_change / 100)
    adjusted_spoilage = base_spoilage_pct + total_spoilage_change
    
    poucher_spoilage_ft = poucher_total_ft * adjusted_spoilage / 100
    poucher_final_ft = poucher_total_ft + poucher_spoilage_ft
    
    # Run time
    poucher_run_hours = poucher_final_ft / adjusted_speed / 60 if adjusted_speed > 0 else 0
    
    # Total labor = make ready + wash up + run time
    poucher_total_hours = total_mr_hours + total_washup_hours + poucher_run_hours
    poucher_labor_cost = poucher_total_hours * POUCHER_EST_RATE
    
    # Sealer ink
    poucher_msi = HP_STOCK_WIDTH * poucher_final_ft * 12 / 1000  # using original stock width for poucher
    # Actually poucher may use different width — but sealer uses the full web
    # The Suncentre has max stock width 30" but uses whatever the web width is
    poucher_sealer_cost = max(poucher_msi * POUCHER_SEALER_INK_MSI, POUCHER_SEALER_MIN)
    
    # Zipper material cost
    zip_info = ZIPPERS.get(zipper_norm)
    if zip_info is None:
        # Try matching
        for zk, zv in ZIPPERS.items():
            if zk.lower() in zipper_norm.lower() or zipper_norm.lower() in zk.lower():
                zip_info = zv
                break
    if zip_info is None:
        zip_info = ZIPPERS["None"]
    
    zipper_cost = 0
    if zip_info["cost_msi"] > 0:
        # Zipper runs at its own width, same run length as the web
        zipper_msi = zip_info["width_in"] * poucher_final_ft * 12 / 1000
        zipper_cost = zipper_msi * zip_info["cost_msi"]
    
    poucher_total = poucher_labor_cost + poucher_sealer_cost + zipper_cost
    
    result["poucher_costs"] = {
        "active_udos": active_udos,
        "make_ready_hours": total_mr_hours,
        "run_hours": poucher_run_hours,
        "total_hours": poucher_total_hours,
        "labor_cost": poucher_labor_cost,
        "sealer_cost": poucher_sealer_cost,
        "zipper_cost": zipper_cost,
        "base_speed_ft_min": base_speed,
        "adjusted_speed_ft_min": adjusted_speed,
        "base_spoilage_pct": base_spoilage_pct,
        "adjusted_spoilage_pct": adjusted_spoilage,
        "run_length_ft": poucher_final_ft,
        "total": poucher_total,
    }
    
    # ─── Total Cost ───
    total_cost = hp_total + thermo_total + poucher_total
    cost_per_unit = total_cost / quantity if quantity > 0 else 0
    
    result["total_cost"] = total_cost
    result["cost_per_unit"] = cost_per_unit
    
    result["cost_breakdown"] = {
        "hp_6900": hp_total,
        "thermo_laminator": thermo_total,
        "poucher": poucher_total,
        "hp_pct": hp_total / total_cost * 100 if total_cost > 0 else 0,
        "thermo_pct": thermo_total / total_cost * 100 if total_cost > 0 else 0,
        "poucher_pct": poucher_total / total_cost * 100 if total_cost > 0 else 0,
    }
    
    return result


# ═══════════════════════════════════════════════════════════════
# SUPABASE DATA FETCHING
# ═══════════════════════════════════════════════════════════════

def fetch_internal_cost_only_quotes(supabase: Client) -> list:
    """
    Fetch all internal quotes with their price tiers from Supabase.
    Only fetches cost-only estimates (profit_adjustment = 'Costs only' or similar).
    
    Returns list of dicts with quote specs and price tiers.
    """
    # Fetch internal quotes
    response = supabase.table("quotes").select("*").eq("vendor", "internal").execute()
    quotes = response.data
    
    if not quotes:
        print("WARNING: No internal quotes found in Supabase!")
        return []
    
    print(f"Found {len(quotes)} total internal quotes")
    
    # Fetch all price tiers for these quotes
    quote_ids = [q["id"] for q in quotes]
    
    all_prices = []
    # Fetch in batches (Supabase may limit)
    batch_size = 50
    for i in range(0, len(quote_ids), batch_size):
        batch_ids = quote_ids[i:i+batch_size]
        price_response = supabase.table("quote_prices").select("*").in_("quote_id", batch_ids).execute()
        all_prices.extend(price_response.data)
    
    print(f"Found {len(all_prices)} price tier rows")
    
    # Group prices by quote_id
    prices_by_quote = {}
    for p in all_prices:
        qid = p["quote_id"]
        if qid not in prices_by_quote:
            prices_by_quote[qid] = []
        prices_by_quote[qid].append(p)
    
    # Build combined records
    records = []
    for q in quotes:
        qid = q["id"]
        prices = prices_by_quote.get(qid, [])
        if not prices:
            continue
        
        for price in prices:
            record = {
                "quote_id": qid,
                "fl_number": q.get("fl_number", ""),
                "width": q.get("width"),
                "height": q.get("height"),
                "gusset": q.get("gusset", 0),
                "substrate": q.get("substrate", ""),
                "finish": q.get("finish", "None"),
                "seal_type": q.get("seal_type", ""),
                "zipper": q.get("zipper", "None"),
                "tear_notch": q.get("tear_notch", "None"),
                "hole_punch": q.get("hole_punch", "None"),
                "corner_treatment": q.get("corner_treatment", "Rounded"),
                "gusset_type": q.get("gusset_type", ""),
                "embellishment": q.get("embellishment", ""),
                "quantity": price.get("quantity"),
                "actual_unit_price": price.get("unit_price"),
                "actual_total_price": price.get("total_price"),
            }
            records.append(record)
    
    print(f"Built {len(records)} comparison records (quote × price tier)")
    return records


# ═══════════════════════════════════════════════════════════════
# MAIN VALIDATION
# ═══════════════════════════════════════════════════════════════

def normalize_substrate(raw: str) -> str:
    """Map various substrate names to our standard keys."""
    if not raw:
        return "MET PET"
    raw_upper = raw.upper().strip()
    
    mappings = {
        "CLR PET": "CLR PET",
        "CLEAR PET": "CLR PET",
        "0.5 MIL CLEAR PET": "CLR PET",
        "MET PET": "MET PET",
        "METPET": "MET PET",
        "0.5 MIL METPET": "MET PET",
        "WHT MET PET": "WHT MET PET",
        "WHITE METPET": "WHT MET PET",
        "WHITE MET PET": "WHT MET PET",
        "0.5 MIL WHITE METPET": "WHT MET PET",
        "ALOX PET": "ALOX PET",
        "ALOX": "ALOX PET",
        "HB CLR PET": "HB CLR PET",
        "HIGH BARRIER CLEAR PET": "HB CLR PET",
        "EVOH": "HB CLR PET",
    }
    
    for key, value in mappings.items():
        if key in raw_upper:
            return value
    
    return "MET PET"  # default fallback


def normalize_finish(raw: str) -> str:
    """Map finish names to standard keys."""
    if not raw:
        return "None"
    raw_lower = raw.lower().strip()
    
    if "matte" in raw_lower:
        return "Matte"
    elif "soft" in raw_lower:
        return "Soft Touch"
    elif "gloss" in raw_lower:
        return "Gloss"
    elif raw_lower in ("none", "", "n/a"):
        return "None"
    
    # Check if it looks like a substrate name (sometimes finish field has substrate)
    if any(s in raw_lower for s in ["pet", "met", "clr", "alox", "evoh"]):
        return "None"  # This is a substrate, not a finish
    
    return raw  # return as-is


def normalize_seal_type(raw: str) -> str:
    """Map seal type to UDO key."""
    if not raw:
        return "Stand Up Pouch"
    raw_lower = raw.lower().strip()
    
    if "stand up" in raw_lower or "sup" in raw_lower:
        return "Stand Up Pouch"
    elif "3 side" in raw_lower and "bottom" in raw_lower:
        return "3 Side Seal"
    elif "3 side" in raw_lower and "top" in raw_lower:
        return "3 Side Seal"
    elif "3 side" in raw_lower:
        return "3 Side Seal"
    elif "2 side" in raw_lower:
        return "2 Side Seal"
    elif "cube" in raw_lower:
        return "Stand Up Pouch"  # Cube is special but treat as SUP for now
    
    return "Stand Up Pouch"


def normalize_zipper(raw: str) -> str:
    """Map zipper to standard key."""
    if not raw:
        return "None"
    raw_lower = raw.lower().strip()
    
    if raw_lower in ("none", "", "n/a", "no zipper"):
        return "None"
    elif "cr" in raw_lower and "non" not in raw_lower:
        return "CR Zipper"
    elif "non" in raw_lower or "single" in raw_lower:
        return "Single Profile - Non CR Zipper"
    elif "double" in raw_lower:
        return "Double Profile - Non CR Zipper"
    
    return raw


def run_validation():
    """Main validation routine."""
    
    # Connect to Supabase
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY environment variables")
        print("  export SUPABASE_URL='https://dernxirzvawjmdxzxefl.supabase.co'")
        print("  export SUPABASE_KEY='your-anon-key'")
        sys.exit(1)
    
    supabase = create_client(url, key)
    
    # Fetch data
    records = fetch_internal_cost_only_quotes(supabase)
    
    if not records:
        print("No records to validate!")
        return
    
    # Run calculator on each record
    results = []
    errors = []
    
    for rec in records:
        width = rec.get("width")
        height = rec.get("height")
        gusset = rec.get("gusset", 0) or 0
        quantity = rec.get("quantity")
        actual_price = rec.get("actual_unit_price")
        
        if not all([width, height, quantity, actual_price]):
            errors.append(f"Missing data: FL={rec.get('fl_number')}, qty={quantity}")
            continue
        
        if actual_price <= 0 or quantity <= 0:
            errors.append(f"Invalid price/qty: FL={rec.get('fl_number')}, price={actual_price}, qty={quantity}")
            continue
        
        substrate = normalize_substrate(rec.get("substrate", ""))
        finish = normalize_finish(rec.get("finish", ""))
        seal_type = normalize_seal_type(rec.get("seal_type", ""))
        zipper = normalize_zipper(rec.get("zipper", ""))
        tear_notch = rec.get("tear_notch", "None") or "None"
        hole_punch = rec.get("hole_punch", "None") or "None"
        corners = rec.get("corner_treatment", "Rounded") or "Rounded"
        
        try:
            calc = calculate_internal_cost(
                width=float(width),
                height=float(height),
                gusset=float(gusset),
                substrate=substrate,
                finish=finish,
                seal_type=seal_type,
                zipper=zipper,
                tear_notch=tear_notch,
                hole_punch=hole_punch,
                corners=corners,
                quantity=int(quantity),
            )
        except Exception as e:
            errors.append(f"Calc error: FL={rec.get('fl_number')}, qty={quantity}: {e}")
            continue
        
        if calc.get("cost_per_unit") is None:
            errors.append(f"No result: FL={rec.get('fl_number')}")
            continue
        
        calc_price = calc["cost_per_unit"]
        error_pct = abs(calc_price - actual_price) / actual_price * 100
        direction = "OVER" if calc_price > actual_price else "UNDER"
        
        results.append({
            "fl_number": rec.get("fl_number", ""),
            "quantity": quantity,
            "width": width,
            "height": height,
            "gusset": gusset,
            "substrate": substrate,
            "finish": finish,
            "seal_type": seal_type,
            "zipper": zipper,
            "tear_notch": tear_notch,
            "hole_punch": hole_punch,
            "corners": corners,
            "actual_unit_price": actual_price,
            "calculated_unit_price": round(calc_price, 5),
            "error_pct": round(error_pct, 2),
            "direction": direction,
            "hp_cost": round(calc["hp_costs"]["total"], 2),
            "thermo_cost": round(calc["thermo_costs"]["total"], 2),
            "poucher_cost": round(calc["poucher_costs"]["total"], 2),
            "total_cost": round(calc["total_cost"], 2),
            "labels_per_cycle": calc["layout"]["labels_per_cycle"],
            "gear_teeth": calc["layout"]["gear_teeth"],
            "no_across": calc["layout"]["no_across"],
            "no_around": calc["layout"]["no_around"],
        })
    
    if not results:
        print("No valid results!")
        if errors:
            print(f"\n{len(errors)} errors:")
            for e in errors[:20]:
                print(f"  {e}")
        return
    
    # ─── Write CSV ───
    output_path = "calculator_vs_supabase.csv"
    fieldnames = list(results[0].keys())
    
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {len(results)} comparisons written to {output_path}")
    print(f"{'='*70}")
    
    # ─── Summary Statistics ───
    errors_pct = [r["error_pct"] for r in results]
    
    mape = sum(errors_pct) / len(errors_pct)
    median_error = sorted(errors_pct)[len(errors_pct) // 2]
    max_error = max(errors_pct)
    min_error = min(errors_pct)
    within_10 = sum(1 for e in errors_pct if e <= 10) / len(errors_pct) * 100
    within_20 = sum(1 for e in errors_pct if e <= 20) / len(errors_pct) * 100
    within_30 = sum(1 for e in errors_pct if e <= 30) / len(errors_pct) * 100
    
    over_count = sum(1 for r in results if r["direction"] == "OVER")
    under_count = sum(1 for r in results if r["direction"] == "UNDER")
    
    print(f"\nOVERALL METRICS:")
    print(f"  MAPE:          {mape:.1f}%")
    print(f"  Median Error:  {median_error:.1f}%")
    print(f"  Min Error:     {min_error:.1f}%")
    print(f"  Max Error:     {max_error:.1f}%")
    print(f"  Within 10%:    {within_10:.0f}% of predictions")
    print(f"  Within 20%:    {within_20:.0f}% of predictions")
    print(f"  Within 30%:    {within_30:.0f}% of predictions")
    print(f"  Over-predict:  {over_count} ({over_count/len(results)*100:.0f}%)")
    print(f"  Under-predict: {under_count} ({under_count/len(results)*100:.0f}%)")
    
    # ─── Breakdown by Substrate ───
    print(f"\nBY SUBSTRATE:")
    substrates = set(r["substrate"] for r in results)
    for sub in sorted(substrates):
        sub_results = [r for r in results if r["substrate"] == sub]
        sub_mape = sum(r["error_pct"] for r in sub_results) / len(sub_results)
        print(f"  {sub:15s}  MAPE: {sub_mape:6.1f}%  ({len(sub_results)} rows)")
    
    # ─── Breakdown by Seal Type ───
    print(f"\nBY SEAL TYPE:")
    seal_types = set(r["seal_type"] for r in results)
    for st in sorted(seal_types):
        st_results = [r for r in results if r["seal_type"] == st]
        st_mape = sum(r["error_pct"] for r in st_results) / len(st_results)
        print(f"  {st:20s}  MAPE: {st_mape:6.1f}%  ({len(st_results)} rows)")
    
    # ─── Breakdown by Zipper ───
    print(f"\nBY ZIPPER:")
    zippers = set(r["zipper"] for r in results)
    for z in sorted(zippers):
        z_results = [r for r in results if r["zipper"] == z]
        z_mape = sum(r["error_pct"] for r in z_results) / len(z_results)
        print(f"  {z:35s}  MAPE: {z_mape:6.1f}%  ({len(z_results)} rows)")
    
    # ─── Breakdown by Quantity Range ───
    print(f"\nBY QUANTITY RANGE:")
    qty_ranges = [
        ("≤1K", 0, 1000),
        ("1K-5K", 1001, 5000),
        ("5K-10K", 5001, 10000),
        ("10K-25K", 10001, 25000),
        ("25K-50K", 25001, 50000),
        ("50K-100K", 50001, 100000),
        ("100K+", 100001, 999999999),
    ]
    for label, lo, hi in qty_ranges:
        qr_results = [r for r in results if lo <= r["quantity"] <= hi]
        if qr_results:
            qr_mape = sum(r["error_pct"] for r in qr_results) / len(qr_results)
            print(f"  {label:12s}  MAPE: {qr_mape:6.1f}%  ({len(qr_results)} rows)")
    
    # ─── Worst 10 Predictions ───
    print(f"\nWORST 10 PREDICTIONS:")
    worst = sorted(results, key=lambda r: r["error_pct"], reverse=True)[:10]
    for r in worst:
        print(f"  {r['fl_number']:15s}  qty={r['quantity']:>7,}  actual=${r['actual_unit_price']:.4f}  "
              f"calc=${r['calculated_unit_price']:.4f}  err={r['error_pct']:.1f}% {r['direction']}  "
              f"({r['substrate']}, {r['finish']}, {r['seal_type']}, {r['zipper']})")
    
    # ─── Best 10 Predictions ───
    print(f"\nBEST 10 PREDICTIONS:")
    best = sorted(results, key=lambda r: r["error_pct"])[:10]
    for r in best:
        print(f"  {r['fl_number']:15s}  qty={r['quantity']:>7,}  actual=${r['actual_unit_price']:.4f}  "
              f"calc=${r['calculated_unit_price']:.4f}  err={r['error_pct']:.1f}%  "
              f"({r['substrate']}, {r['finish']}, {r['seal_type']}, {r['zipper']})")
    
    # ─── Reference Estimate 6774 Check ───
    print(f"\n{'='*70}")
    print(f"REFERENCE CHECK — Estimate 6774 (FL-DL-1670)")
    print(f"  3.62W × 5H × 1.5G, MET PET, Matte, SUP, CR Zipper, K-Seal")
    print(f"{'='*70}")
    
    ref_targets = {
        5000:   0.19543,
        10000:  0.15517,
        25000:  0.12936,
        50000:  0.12194,
        100000: 0.11800,
    }
    
    for qty, target in ref_targets.items():
        calc = calculate_internal_cost(
            width=3.62, height=5.0, gusset=1.5,
            substrate="MET PET", finish="Matte",
            seal_type="Stand Up Pouch", zipper="CR Zipper",
            tear_notch="Standard", hole_punch="None",
            corners="Rounded", quantity=qty,
        )
        calc_price = calc["cost_per_unit"]
        err = abs(calc_price - target) / target * 100
        print(f"  qty={qty:>7,}  LT=${target:.5f}  calc=${calc_price:.5f}  err={err:.1f}%")
    
    # Print data errors
    if errors:
        print(f"\nDATA ERRORS ({len(errors)}):")
        for e in errors[:20]:
            print(f"  {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")


if __name__ == "__main__":
    run_validation()
