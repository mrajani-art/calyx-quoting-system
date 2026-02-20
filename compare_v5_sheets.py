#!/usr/bin/env python3
"""
Deterministic Internal Calculator v5 — Validation Script
=========================================================
Fetches all internal cost-only quotes from Google Sheet,
runs each through the deterministic calculator, and outputs
comparison CSV + summary statistics.

v5 changes from v4:
  - Updated frame repeat / layout logic from HP Indigo press screenshots
  - Width goes in "around" direction, print_width (H*2+G) goes "across"
  - no_around = floor(repeat_in / width)
  - Gear teeth selected to maximize no_around within 38" max repeat
  - repeat_in = gear_teeth * 0.125

Usage:
  pip install gspread google-auth pandas
  python compare_v5_sheets.py
"""

import math
import json
import csv
import os
import sys

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False
    print("WARNING: gspread not installed. Will look for local CSV fallback.")

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# ═══════════════════════════════════════════════════════════
# CONSTANTS — from Label Traxx screenshots & Production tabs
# ═══════════════════════════════════════════════════════════

SHEET_ID = "1L1HRn7WpTnGvZwRIQnppNlMxQdmnOxxUcpbU2r25Bkk"
SERVICE_ACCOUNT_PATH = "config/google_service_account.json"

# ── Substrates ($/MSI, all run at 13" stock width) ──
SUBSTRATES = {
    "CLR PET":     0.4150,  # Stock 199
    "MET PET":     0.4350,  # Stock 201
    "WHT MET PET": 0.4350,  # Stock 206
    "ALOX PET":    0.4890,  # Stock 278
    "HB CLR PET":  0.5460,  # Stock 216
}

# ── Laminates ($/MSI, all run at 13" stock width) ──
LAMINATES = {
    "Matte":      0.1790,  # Stock 286 (note: Prod tab for 4984 shows $0.22 — discrepancy)
    "Gloss":      0.1600,  # Stock 193 (verified in 4996 Production)
    "Soft Touch": 0.3500,  # Stock 195 (not yet verified in Production)
    "Matte Lam":  0.1790,  # Alias
    "None":       0.0,
}

# ── Zippers ($/MSI, run at their own width) ──
ZIPPERS = {
    "CR Zipper":                     {"width": 0.95,  "cost_per_msi": 5.2587},  # Stock 174
    "Double Profile - Non CR Zipper":{"width": 0.394, "cost_per_msi": 2.6734},  # Stock 176
    "Single Profile - Non CR Zipper":{"width": 0.394, "cost_per_msi": 2.6734},  # Stock 176
    "Non-CR Zipper":                 {"width": 0.394, "cost_per_msi": 2.6734},
    "None":                          {"width": 0,     "cost_per_msi": 0},
}

STOCK_WIDTH = 13.0  # inches — ALWAYS 13" for HP and Thermo

# ── HP 6900 (Stage 1) ──
HP_RATE = 125.0       # $/hr (all color counts)
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

# Default color config (most common): 4 CMYKOVG + 1 Premium White
DEFAULT_CMYKOVG_COLORS = 4
DEFAULT_WHITE_COLORS = 1

# ── Thermo Laminator (Stage 2) ──
THERMO_RATE = 45.0   # $/hr
THERMO_SETUP_FT = 25  # from Set Up Options screenshot
# Thermo has 0 makeready hours (confirmed from Production tabs)
# Speed: 100 ft/min for ≤3,500ft, 120 ft/min for >3,500ft
# Spoilage: included in combined spoilage table

# ── Suncentre Poucher SCSG-600XL (Stage 3) ──
POUCHER_RATE = 200.0  # $/hr
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
    "Stand Up Pouch":    {"mr": 0.65, "setup_ft": 300, "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "3 Side Seal":       {"mr": 0.60, "setup_ft": 200, "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "3 Side Bottom Fill":{"mr": 0.60, "setup_ft": 200, "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "3 Side Top Fill":   {"mr": 0.60, "setup_ft": 200, "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "2 Side Seal":       {"mr": 0.50, "setup_ft": 150, "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "Cube":              {"mr": 1.00, "setup_ft": 250, "speed_chg": 0.0,     "spoilage_chg": 0.0},
    # Zippers
    "CR Zipper":         {"mr": 0.08, "setup_ft": 0,   "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "Non-CR Zipper":     {"mr": 1.00, "setup_ft": 0,   "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "No Zipper":         {"mr": 0.03, "setup_ft": 0,   "speed_chg": 0.05,    "spoilage_chg": 0.0},
    # Features
    "Hole Punch":        {"mr": 0.10, "setup_ft": 0,   "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "Tear Notch":        {"mr": 0.10, "setup_ft": 50,  "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "Rounded Corners":   {"mr": 0.12, "setup_ft": 25,  "speed_chg": 0.0,     "spoilage_chg": 0.0},
    "Second Web":        {"mr": 0.33, "setup_ft": 100, "speed_chg": 0.0,     "spoilage_chg": 0.025},
    "Insert Gusset":     {"mr": 0.25, "setup_ft": 100, "speed_chg": 0.0,     "spoilage_chg": 0.025},
    "Die Cut Station":   {"mr": 1.00, "setup_ft": 250, "speed_chg": -0.25,   "spoilage_chg": 0.05},
    "Calyx Cube":        {"mr": 1.00, "setup_ft": 250, "speed_chg": -0.25,   "spoilage_chg": 0.0},
    "Eco - 100% Recyc":  {"mr": 0.00, "setup_ft": 0,   "speed_chg": -0.10,   "spoilage_chg": 0.0},
    "Non-Calyx Dieline": {"mr": 0.00, "setup_ft": 200, "speed_chg": 0.0,     "spoilage_chg": 0.0},
}

# Combined spoilage table (Discovery 3 from v4)
# This is the COMBINED spoilage % for all 3 stages
COMBINED_SPOILAGE_TABLE = [
    (0,     2000,  0.108),
    (2001,  3500,  0.103),
    (3501,  7000,  0.098),
    (7001,  15000, 0.092),
    (15001, 30000, 0.087),
    (30001, 55000, 0.082),
    (55001, 999999999, 0.077),
]

# Packaging cost per K (averaged — varies by bag size; known issue)
PACKAGING_CARTON_PER_K = 3.50    # Est 6774 rate
PACKAGING_PACK_PER_K = 10.196    # Est 6774 rate
PACKAGING_WRAP_PER_K = 0.16      # consistent across estimates


# ═══════════════════════════════════════════════════════════
# LAYOUT LOGIC (updated in v5 from frame repeat screenshots)
# ═══════════════════════════════════════════════════════════

def calc_layout(width, height, gusset):
    """
    Calculate HP Indigo press layout.
    
    Key insight from screenshots (Image 30/31):
    - Width goes in the "around" (repeat) direction
    - Print width (H*2 + G) goes in the "across" direction  
    - no_around = floor(repeat_in / width)
    - Gear teeth selected to maximize no_around
    - repeat_in = gear_teeth * 0.125 (pitch)
    - Size across = H*2 + G + 0.25 (trims)
    
    Returns: (no_across, no_around, gear_teeth, repeat_in)
    """
    print_width = height * 2 + gusset  # This goes across the web
    size_across = print_width + 0.25   # Add left+right trim (0.125 each)
    
    # No. across is always 1 for flexpack (size_across must fit in 13" stock)
    no_across = max(1, int(STOCK_WIDTH / size_across))
    # In practice, always 1 for our bag sizes
    no_across = 1
    
    # Select gear teeth to maximize no_around
    # Width goes in the "around" direction
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


def get_combined_spoilage(stock_length_ft):
    """Look up combined spoilage % from the stock_length-based table."""
    for lo, hi, spoilage in COMBINED_SPOILAGE_TABLE:
        if lo <= stock_length_ft <= hi:
            return spoilage
    return 0.077  # default for very long runs


def get_poucher_speed_and_spoilage(run_length_ft):
    """Look up poucher speed and spoilage from the 12-level table."""
    for lo, hi, spoilage, speed in POUCHER_SPEED_TABLE:
        if lo <= run_length_ft <= hi:
            return speed, spoilage
    return 40, 0.02  # default for very long runs


def calc_msi(width_in, length_ft):
    """Calculate MSI (thousand square inches) from width and length."""
    return width_in * length_ft * 12 / 1000


# ═══════════════════════════════════════════════════════════
# MAIN CALCULATOR
# ═══════════════════════════════════════════════════════════

def calculate_cost(width, height, gusset, quantity, substrate, finish,
                   seal_type, zipper, tear_notch="Standard", hole_punch="None",
                   corners="Rounded", gusset_detail="K-Seal",
                   cmykovg_colors=DEFAULT_CMYKOVG_COLORS,
                   white_colors=DEFAULT_WHITE_COLORS):
    """
    Calculate the production cost for one bag spec at one quantity.
    Returns dict with total cost, unit cost, and component breakdown.
    """
    
    # ── Layout ──
    no_across, no_around, gear_teeth, repeat_in = calc_layout(width, height, gusset)
    repeat_ft = repeat_in / 12.0
    labels_per_cycle = no_across * no_around
    
    if labels_per_cycle == 0:
        return {"error": f"Invalid layout: {width}W x {height}H x {gusset}G -> 0 labels/cycle"}
    
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
    if zipper and zipper != "None":
        zip_key = zipper if zipper in POUCHER_UDO else "CR Zipper" if "CR" in zipper else "Non-CR Zipper"
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
    if tear_notch and tear_notch != "None":
        if "Tear Notch" in POUCHER_UDO:
            udo = POUCHER_UDO["Tear Notch"]
            poucher_setup_ft += udo["setup_ft"]
            poucher_mr_hrs += udo["mr"]
    
    # Hole punch
    if hole_punch and hole_punch != "None":
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
    
    # Gusset detail — Insert Gusset only applies to Side Gusset, not K-Seal
    if gusset_detail and gusset_detail in ("Side Gusset", "Flat Bottom"):
        if "Insert Gusset" in POUCHER_UDO:
            udo = POUCHER_UDO["Insert Gusset"]
            poucher_setup_ft += udo["setup_ft"]
            poucher_mr_hrs += udo["mr"]
            poucher_add_spoilage += udo["spoilage_chg"]
    
    # ── Frame / stock length calculation (iterative) ──
    # total_setup_sheets = ceil(HP_setup_ft / repeat_ft) + ceil(poucher_setup_ft / repeat_ft)
    hp_setup_sheets = math.ceil(HP_SETUP_FT / repeat_ft) if repeat_ft > 0 else 0
    poucher_setup_sheets = math.ceil(poucher_setup_ft / repeat_ft) if repeat_ft > 0 else 0
    total_setup_sheets = hp_setup_sheets + poucher_setup_sheets
    
    # Iterative: spoilage depends on stock_length which depends on total_frames
    # Start with a guess
    combined_spoilage = 0.10  # initial guess
    for _ in range(5):  # converges fast
        total_frames = math.ceil(good_sheets * (1 + combined_spoilage)) + total_setup_sheets
        stock_length_ft = total_frames * repeat_ft
        combined_spoilage = get_combined_spoilage(stock_length_ft)
    
    # Final values
    total_frames = math.ceil(good_sheets * (1 + combined_spoilage)) + total_setup_sheets
    stock_length_ft = total_frames * repeat_ft
    
    # ══ STAGE 1: HP 6900 ══
    
    # Substrate cost
    sub_rate = SUBSTRATES.get(substrate, 0.4350)
    substrate_msi = calc_msi(STOCK_WIDTH, stock_length_ft)
    substrate_cost = substrate_msi * sub_rate
    
    # In-line priming
    priming_cost = substrate_msi * HP_PRIMING
    
    # Click charges (×2 per sheet, per color)
    total_sheets = total_frames  # 1 sheet = 1 frame on HP Indigo
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
    
    # ══ STAGE 2: THERMO LAMINATOR ══
    
    lam_rate = LAMINATES.get(finish, 0.0)
    if finish and finish != "None" and lam_rate > 0:
        lam_msi = calc_msi(STOCK_WIDTH, stock_length_ft)
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
    
    # ══ STAGE 3: ZIPPER (3rd Stock cost) ══
    
    zip_info = ZIPPERS.get(zipper, ZIPPERS["None"])
    if zip_info["width"] > 0:
        zip_msi = calc_msi(zip_info["width"], stock_length_ft)
        zip_cost = zip_msi * zip_info["cost_per_msi"]
    else:
        zip_cost = 0
    
    # ══ STAGE 4: SUNCENTRE POUCHER ══
    
    # Poucher uses the good portion of run length for speed lookup
    poucher_run_ft = good_sheets * repeat_ft  # good sheets only
    poucher_speed, poucher_base_spoilage = get_poucher_speed_and_spoilage(poucher_run_ft)
    
    # Apply UDO speed multiplier
    effective_poucher_speed = poucher_speed * poucher_speed_mult
    
    # Poucher run hours
    poucher_total_run_ft = stock_length_ft  # poucher processes entire web
    poucher_run_hrs = poucher_total_run_ft / (effective_poucher_speed * 60) if effective_poucher_speed > 0 else 0
    
    # Poucher labor = makeready + running
    poucher_labor = (poucher_mr_hrs + poucher_run_hrs) * POUCHER_RATE
    
    # Sealer ink
    sealer_msi = calc_msi(STOCK_WIDTH, stock_length_ft)
    sealer_cost = max(sealer_msi * POUCHER_SEALER_PER_MSI, POUCHER_SEALER_MIN)
    
    poucher_total = poucher_labor + sealer_cost
    
    # ══ PACKAGING ══
    
    qty_k = quantity / 1000
    packaging_cost = (PACKAGING_CARTON_PER_K + PACKAGING_PACK_PER_K + PACKAGING_WRAP_PER_K) * qty_k
    
    # ══ TOTAL ══
    
    total_cost = hp_total + thermo_total + zip_cost + poucher_total + packaging_cost
    unit_cost = total_cost / quantity if quantity > 0 else 0
    
    return {
        "quantity": quantity,
        "total_cost": total_cost,
        "unit_cost": unit_cost,
        "layout": {
            "no_across": no_across,
            "no_around": no_around,
            "gear_teeth": gear_teeth,
            "repeat_in": repeat_in,
            "repeat_ft": repeat_ft,
            "labels_per_cycle": labels_per_cycle,
            "good_sheets": good_sheets,
            "total_frames": total_frames,
            "stock_length_ft": stock_length_ft,
            "combined_spoilage": combined_spoilage,
        },
        "components": {
            "substrate": substrate_cost,
            "priming": priming_cost,
            "clicks": click_cost,
            "hp_makeready": hp_makeready_cost,
            "hp_running": hp_run_cost,
            "laminate": lam_cost,
            "thermo_labor": thermo_labor,
            "zipper": zip_cost,
            "poucher_labor": poucher_labor,
            "sealer": sealer_cost,
            "packaging": packaging_cost,
        },
    }


# ═══════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════

def load_from_google_sheet():
    """Load internal estimates from Google Sheet."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.sheet1
    data = ws.get_all_records()
    return data


def normalize_field(val):
    """Clean up a field value."""
    if val is None or val == "":
        return None
    s = str(val).strip()
    return s if s else None


def parse_estimate(row):
    """Parse a row from the Google Sheet into calculator inputs."""
    # Get dimensions
    try:
        width = float(row.get("SizeAround", 0) or 0)
        height = float(row.get("FlexPack_Height", 0) or 0)
        gusset = float(row.get("FlexPack_Gusset", 0) or 0)
    except (ValueError, TypeError):
        return None
    
    if width <= 0 or height <= 0:
        return None
    
    # Get seal type from FPUD_Popup1
    seal_type = normalize_field(row.get("FPUD_Popup1"))
    if not seal_type:
        seal_type = "Stand Up Pouch"
    
    # Zipper from FPUD_Popup2
    zipper = normalize_field(row.get("FPUD_Popup2"))
    if not zipper or zipper.lower() == "none":
        zipper = "None"
    
    # Tear notch from FPUD_Popup3
    tear_notch = normalize_field(row.get("FPUD_Popup3"))
    if not tear_notch or tear_notch.lower() == "none":
        tear_notch = "None"
    
    # Hole punch from FPUD_Popup4
    hole_punch = normalize_field(row.get("FPUD_Popup4"))
    if not hole_punch or hole_punch.lower() == "none":
        hole_punch = "None"
    
    # Seal/gusset detail from FPUD_Popup5
    gusset_detail = normalize_field(row.get("FPUD_Popup5"))
    if not gusset_detail:
        gusset_detail = "K-Seal"
    
    # Corners from FPUD_Popup6
    corners = normalize_field(row.get("FPUD_Popup6"))
    if not corners:
        corners = "Rounded"
    
    # Substrate from StockDescr2 (main stock / base film)
    # StockDescr1 = laminate, StockDescr2 = substrate (confirmed from LT export)
    stock_descr2 = normalize_field(row.get("StockDescr2")) or ""
    stock_num2 = normalize_field(row.get("StockNum2")) or ""
    substrate = map_substrate(stock_descr2)
    
    # Get actual face stock price if available
    face_stock_msi = 0
    try:
        face_stock_msi = float(row.get("FaceStockMSI", 0) or 0)
    except (ValueError, TypeError):
        pass
    
    # Finish/laminate from StockDescr1 (laminate stock)
    finish_descr = normalize_field(row.get("StockDescr1")) or ""
    stock_num1 = normalize_field(row.get("StockNum1")) or ""
    finish = map_finish(finish_descr)
    
    # If StockDescr1 is empty, check StockNum1 — sometimes laminate not described
    # Also check if there's a laminate MSI price
    lam_msi_price = 0
    try:
        lam_msi_price = float(row.get("LaminateMSI", 0) or 0)
    except (ValueError, TypeError):
        pass
    
    # FALLBACK: If finish is "None" but there are laminate prices, detect the finish
    if finish == "None":
        # Check if any StockPrice_Laminate tier has a value
        has_lam_price = False
        for i in range(1, 7):
            try:
                lp = float(row.get(f"StockPrice_Laminate_{i}", 0) or 0)
                if lp > 0:
                    has_lam_price = True
                    lam_msi_price = lp  # use first non-zero
                    break
            except (ValueError, TypeError):
                pass
        
        if has_lam_price or lam_msi_price > 0:
            # Detect finish type from laminate price
            if lam_msi_price >= 0.30:
                finish = "Soft Touch"
            elif lam_msi_price >= 0.20:
                finish = "Matte"  # $0.22 variant
            elif lam_msi_price >= 0.15 and lam_msi_price < 0.175:
                finish = "Gloss"
            else:
                finish = "Matte"  # default laminated = Matte
        elif stock_num1:
            # Has a laminate stock number but no price — map by stock number
            if stock_num1 == "195":
                finish = "Soft Touch"
            elif stock_num1 == "193":
                finish = "Gloss"
            elif stock_num1 == "286":
                finish = "Matte"
            else:
                finish = "Matte"  # default
        else:
            # No laminate info at all — default to Matte (most flexpack bags are laminated)
            finish = "Matte"
    
    # Get per-tier laminate prices (StockPrice_Laminate_1 through 6)
    lam_prices_per_tier = []
    for i in range(1, 7):
        try:
            lp = float(row.get(f"StockPrice_Laminate_{i}", 0) or 0)
            lam_prices_per_tier.append(lp)
        except (ValueError, TypeError):
            lam_prices_per_tier.append(0)
    
    # Get per-tier 3rd stock prices (zipper)
    zip_prices_per_tier = []
    for i in range(1, 7):
        try:
            zp = float(row.get(f"StockPrice_3rdStock_{i}", 0) or 0)
            zip_prices_per_tier.append(zp)
        except (ValueError, TypeError):
            zip_prices_per_tier.append(0)
    
    # Quantities and prices (up to 6 tiers)
    tiers = []
    for i in range(1, 7):
        qty_raw = row.get(f"Quantity{i}", 0)
        price_raw = row.get(f"PricePerM{i}", 0)
        try:
            qty = int(float(qty_raw or 0))
            price = float(price_raw or 0)
        except (ValueError, TypeError):
            continue
        if qty > 0 and price > 0:
            tiers.append((qty, price))
    
    if not tiers:
        return None
    
    # Get estimate number — column is "Number" in LT export
    est_no = row.get("Number", row.get("EstimateNo", row.get("Estimate_No", "")))
    fl_num = normalize_field(row.get("AdditionalDescr")) or ""
    profit_adj = normalize_field(row.get("ProfitAdjLabel")) or ""
    
    # Get LT's own layout values for comparison
    lt_no_around = int(float(row.get("NoAround", 0) or 0))
    lt_no_across = int(float(row.get("NoAcross", 0) or 0))
    
    # Check for additional cost (to flag Est 2201-style outliers)
    add_cost = 0
    for i in range(1, 7):
        ac = row.get(f"AddCost{i}", 0)
        try:
            add_cost += float(ac or 0)
        except (ValueError, TypeError):
            pass
    
    return {
        "est_no": est_no,
        "fl_num": fl_num,
        "profit_adj": profit_adj,
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
        "gusset_detail": gusset_detail,
        "tiers": tiers,
        "add_cost": add_cost,
        "lt_no_around": lt_no_around,
        "lt_no_across": lt_no_across,
        "face_stock_msi": face_stock_msi,
        "lam_msi_price": lam_msi_price,
        "lam_prices_per_tier": lam_prices_per_tier,
        "zip_prices_per_tier": zip_prices_per_tier,
    }


def map_substrate(descr):
    """Map Label Traxx stock description to substrate name."""
    d = descr.upper()
    if "ALOX" in d:
        return "ALOX PET"
    if "HB" in d or "EVOH" in d:
        return "HB CLR PET"
    if "WHT" in d or "WHITE" in d:
        return "WHT MET PET"
    if "MET" in d:
        return "MET PET"
    if "CLR" in d or "CLEAR" in d:
        return "CLR PET"
    # Default
    return "MET PET"


def map_finish(descr):
    """Map Label Traxx finish description to finish name."""
    d = descr.upper()
    if "SOFT" in d:
        return "Soft Touch"
    if "MATTE" in d or "MAT" in d:
        return "Matte"
    if "GLOSS" in d:
        return "Gloss"
    if d == "" or "NONE" in d:
        return "None"
    return "Matte"  # default


# ═══════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════

def run_validation():
    """Main validation: load data, run calculator, compare."""
    
    print("=" * 70)
    print("Deterministic Internal Calculator v5 — Validation")
    print("=" * 70)
    
    # Load data
    if HAS_GSPREAD and os.path.exists(SERVICE_ACCOUNT_PATH):
        print(f"\nLoading from Google Sheet {SHEET_ID}...")
        try:
            data = load_from_google_sheet()
            print(f"  Loaded {len(data)} rows")
        except Exception as e:
            print(f"  ERROR: {e}")
            print("  Falling back to local CSV...")
            data = load_local_csv()
    else:
        print("\nNo Google credentials found, loading local CSV...")
        data = load_local_csv()
    
    if not data:
        print("ERROR: No data loaded!")
        return
    
    # Filter to cost-only
    cost_only = []
    for row in data:
        adj = str(row.get("ProfitAdjLabel", "")).strip()
        if adj == "Costs only":
            cost_only.append(row)
    
    print(f"  Cost-only estimates: {len(cost_only)}")
    
    # Parse and calculate
    results = []
    skipped = 0
    errors = 0
    excluded_addcost = 0
    
    for row in cost_only:
        parsed = parse_estimate(row)
        if not parsed:
            skipped += 1
            continue
        
        # Optionally exclude estimates with Additional Cost
        if parsed["add_cost"] > 0:
            excluded_addcost += 1
            # Still include but flag them
        
        for qty, lt_price in parsed["tiers"]:
            try:
                result = calculate_cost(
                    width=parsed["width"],
                    height=parsed["height"],
                    gusset=parsed["gusset"],
                    quantity=qty,
                    substrate=parsed["substrate"],
                    finish=parsed["finish"],
                    seal_type=parsed["seal_type"],
                    zipper=parsed["zipper"],
                    tear_notch=parsed["tear_notch"],
                    hole_punch=parsed["hole_punch"],
                    corners=parsed["corners"],
                    gusset_detail=parsed["gusset_detail"],
                )
                
                if "error" in result:
                    errors += 1
                    continue
                
                calc_price = result["unit_cost"]
                error_pct = (calc_price - lt_price) / lt_price * 100 if lt_price > 0 else 0
                
                results.append({
                    "est_no": parsed["est_no"],
                    "fl_num": parsed["fl_num"],
                    "width": parsed["width"],
                    "height": parsed["height"],
                    "gusset": parsed["gusset"],
                    "substrate": parsed["substrate"],
                    "finish": parsed["finish"],
                    "seal_type": parsed["seal_type"],
                    "zipper": parsed["zipper"],
                    "tear_notch": parsed["tear_notch"],
                    "corners": parsed["corners"],
                    "gusset_detail": parsed["gusset_detail"],
                    "quantity": qty,
                    "lt_price": lt_price,
                    "calc_price": calc_price,
                    "error_pct": error_pct,
                    "abs_error_pct": abs(error_pct),
                    "has_addcost": parsed["add_cost"] > 0,
                    "layout_around": result["layout"]["no_around"],
                    "lt_around": parsed["lt_no_around"],
                    "layout_match": "Y" if result["layout"]["no_around"] == parsed["lt_no_around"] else "N",
                    "layout_gear": result["layout"]["gear_teeth"],
                    "layout_repeat": result["layout"]["repeat_in"],
                    "stock_length": result["layout"]["stock_length_ft"],
                    "spoilage": result["layout"]["combined_spoilage"],
                    **{f"c_{k}": v for k, v in result["components"].items()},
                })
                
            except Exception as e:
                errors += 1
                print(f"  ERROR on Est {parsed['est_no']} @ {qty}: {e}")
    
    print(f"\n  Parsed: {len(cost_only) - skipped} estimates, Skipped: {skipped}, Errors: {errors}")
    print(f"  Estimates with Additional Cost: {excluded_addcost}")
    print(f"  Total comparison rows: {len(results)}")
    
    if not results:
        print("No results to analyze!")
        return
    
    # ── Write CSV ──
    csv_path = "calculator_v5_vs_labeltraxx.csv"
    fieldnames = list(results[0].keys())
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\n  Saved: {csv_path}")
    
    # ── Summary Statistics ──
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    # All results
    all_errors = [r["abs_error_pct"] for r in results]
    print_stats("ALL ROWS", results)
    
    # Excluding Additional Cost estimates
    clean = [r for r in results if not r["has_addcost"]]
    if len(clean) < len(results):
        print_stats(f"EXCLUDING ADDCOST ({len(results) - len(clean)} rows removed)", clean)
    
    # Excluding Soft Touch + AddCost
    clean_no_st = [r for r in clean if r["finish"] != "Soft Touch"]
    if len(clean_no_st) < len(clean):
        print_stats(f"EXCL ADDCOST + SOFT TOUCH ({len(clean) - len(clean_no_st)} ST rows removed)", clean_no_st)
    
    # Excluding "None" finish (incomplete data) + AddCost
    clean_no_none = [r for r in clean if r["finish"] != "None"]
    if len(clean_no_none) < len(clean):
        print_stats(f"EXCL ADDCOST + NO-LAMINATE ({len(clean) - len(clean_no_none)} None-finish rows removed)", clean_no_none)
    
    # Best case: exclude AddCost + None finish + No Zipper outliers
    clean_best = [r for r in clean if r["finish"] != "None" and r["zipper"] != "None"]
    if len(clean_best) < len(clean):
        print_stats(f"EXCL ADDCOST + NO-LAM + NO-ZIP (best case)", clean_best)
    
    # Layout match check
    print("\n── Layout Match Check ──")
    layout_matches = [r for r in results if r["lt_around"] > 0]
    if layout_matches:
        matched = sum(1 for r in layout_matches if r["layout_match"] == "Y")
        mismatched = sum(1 for r in layout_matches if r["layout_match"] == "N")
        print(f"  Matched: {matched}/{len(layout_matches)} ({matched/len(layout_matches)*100:.0f}%)")
        if mismatched > 0:
            print(f"  Mismatched ({mismatched}):")
            seen = set()
            for r in layout_matches:
                if r["layout_match"] == "N" and r["est_no"] not in seen:
                    seen.add(r["est_no"])
                    print(f"    Est {r['est_no']}: {r['width']}W×{r['height']}H×{r['gusset']}G "
                          f"→ calc={r['layout_around']} vs LT={r['lt_around']}")
    
    # By quantity range
    print("\n── By Quantity Range ──")
    qty_ranges = [
        ("1K-5K",    1000,  5000),
        ("5K-10K",   5001,  10000),
        ("10K-25K",  10001, 25000),
        ("25K-50K",  25001, 50000),
        ("50K-100K", 50001, 100000),
        ("100K+",    100001, 999999999),
    ]
    for label, lo, hi in qty_ranges:
        subset = [r for r in clean if lo <= r["quantity"] <= hi]
        if subset:
            mape = sum(r["abs_error_pct"] for r in subset) / len(subset)
            print(f"  {label:12s}  MAPE: {mape:5.1f}%  ({len(subset)} rows)")
    
    # By substrate
    print("\n── By Substrate ──")
    for sub in sorted(set(r["substrate"] for r in clean)):
        subset = [r for r in clean if r["substrate"] == sub]
        if subset:
            mape = sum(r["abs_error_pct"] for r in subset) / len(subset)
            print(f"  {sub:15s}  MAPE: {mape:5.1f}%  ({len(subset)} rows)")
    
    # By finish
    print("\n── By Finish ──")
    for fin in sorted(set(r["finish"] for r in clean)):
        subset = [r for r in clean if r["finish"] == fin]
        if subset:
            mape = sum(r["abs_error_pct"] for r in subset) / len(subset)
            print(f"  {fin:15s}  MAPE: {mape:5.1f}%  ({len(subset)} rows)")
    
    # By seal type
    print("\n── By Seal Type ──")
    for seal in sorted(set(r["seal_type"] for r in clean)):
        subset = [r for r in clean if r["seal_type"] == seal]
        if subset:
            mape = sum(r["abs_error_pct"] for r in subset) / len(subset)
            print(f"  {seal:20s}  MAPE: {mape:5.1f}%  ({len(subset)} rows)")
    
    # By zipper
    print("\n── By Zipper ──")
    for zip_type in sorted(set(r["zipper"] for r in clean)):
        subset = [r for r in clean if r["zipper"] == zip_type]
        if subset:
            mape = sum(r["abs_error_pct"] for r in subset) / len(subset)
            print(f"  {zip_type:30s}  MAPE: {mape:5.1f}%  ({len(subset)} rows)")
    
    # Reference estimate 6774
    print("\n── Reference Estimate 6774 ──")
    ref = [r for r in results if str(r["est_no"]) == "6774"]
    if ref:
        print(f"  Layout: {ref[0]['layout_around']} around (LT={ref[0]['lt_around']}), gear={ref[0]['layout_gear']}, repeat={ref[0]['layout_repeat']:.2f}\"")
        for r in sorted(ref, key=lambda x: x["quantity"]):
            direction = "OVER" if r["error_pct"] > 0 else "UNDER"
            print(f"  {r['quantity']:>8,}  LT: ${r['lt_price']:.5f}  Calc: ${r['calc_price']:.5f}  {abs(r['error_pct']):.1f}% {direction}")
    else:
        print("  Not found in cost-only dataset (may be Custom/Standard profit adj)")
    
    # Worst 10
    print("\n── Worst 10 Rows ──")
    worst = sorted(clean, key=lambda r: r["abs_error_pct"], reverse=True)[:10]
    for r in worst:
        direction = "OVER" if r["error_pct"] > 0 else "UNDER"
        print(f"  Est {str(r['est_no']):>5s} @ {r['quantity']:>7,}  "
              f"LT: ${r['lt_price']:.5f}  Calc: ${r['calc_price']:.5f}  "
              f"{r['abs_error_pct']:.1f}% {direction}  "
              f"({r['substrate']}, {r['finish']}, {r['seal_type']}, {r['zipper']})")


def print_stats(label, rows):
    """Print summary statistics for a set of results."""
    if not rows:
        return
    
    errors = [r["abs_error_pct"] for r in rows]
    signed = [r["error_pct"] for r in rows]
    
    mape = sum(errors) / len(errors)
    median = sorted(errors)[len(errors) // 2]
    within_5 = sum(1 for e in errors if e <= 5) / len(errors) * 100
    within_10 = sum(1 for e in errors if e <= 10) / len(errors) * 100
    within_15 = sum(1 for e in errors if e <= 15) / len(errors) * 100
    within_20 = sum(1 for e in errors if e <= 20) / len(errors) * 100
    over = sum(1 for e in signed if e > 0) / len(signed) * 100
    under = sum(1 for e in signed if e < 0) / len(signed) * 100
    
    print(f"\n  {label} ({len(rows)} rows)")
    print(f"    MAPE:       {mape:.1f}%")
    print(f"    Median:     {median:.1f}%")
    print(f"    Within 5%:  {within_5:.0f}%")
    print(f"    Within 10%: {within_10:.0f}%")
    print(f"    Within 15%: {within_15:.0f}%")
    print(f"    Within 20%: {within_20:.0f}%")
    print(f"    Over/Under: {over:.0f}% / {under:.0f}%")


def load_local_csv():
    """Fallback: load from local CSV if no Google credentials."""
    paths = [
        "data/internal_training.csv",
        "data/internal_training_costonly.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            print(f"  Loading from {p}")
            if HAS_PANDAS:
                df = pd.read_csv(p)
                return df.to_dict("records")
            else:
                with open(p) as f:
                    reader = csv.DictReader(f)
                    return list(reader)
    print("  No local CSV found!")
    return []


if __name__ == "__main__":
    run_validation()
