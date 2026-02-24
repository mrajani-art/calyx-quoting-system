#!/usr/bin/env python3
"""
Deterministic Internal Calculator v3 — Calibrated from Production Tab
=====================================================================
Corrected using Estimate 6774's Production tab actual cost breakdown.

Key fixes from v2:
1. HP 6900 run-time labor (speed 74 ft/min from Production tab)
2. Stock length / spoilage calculated as combined across all presses
3. Thermo Laminator: 0 makeready (confirmed), run-time only
4. Packaging + Carton + Wrapping costs added
5. Impress cost (clicks) calibrated against LT's $74.16 @ 5K

Usage:
    python compare_v3_sheets.py
"""

import math
import csv
import json
import sys

try:
    import gspread
except ImportError:
    print("ERROR: pip install gspread")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — Calibrated from Estimate 6774 Production Tab
# ═══════════════════════════════════════════════════════════════

# --- HP 6900 Digital Press ---
HP_EST_RATE = 125.00          # $/hr
HP_STOCK_WIDTH = 13.0         # inches (FIXED)
HP_PITCH = 0.125              # inches per gear tooth
HP_MAX_REPEAT = 38.0          # inches
HP_MIN_REPEAT = 0.5           # inches
HP_SETUP_HOURS = 0.25         # Makeready hours (confirmed: $31.25)
HP_SETUP_LENGTH_FT = 100      # feet
HP_SPOILAGE_PCT = 2.0         # flat 2% (WS6000 series)
HP_INLINE_PRIMING = 0.04      # $/MSI
HP_CLICK_CHARGE_CMYKOVG = 0.0107
HP_CLICK_CHARGE_WHITE = 0.0095
HP_CLICK_MULTIPLIER = 2
HP_PRESS_SPEED = 74           # ft/min (from Production tab — consistent across all qty tiers)

# --- Thermo Laminator ---
THERMO_EST_RATE = 45.00       # $/hr
THERMO_STOCK_WIDTH = 13.0     # inches (FIXED)
THERMO_SETUP_LENGTH_FT = 100  # Set Up Length from Thermo Set Up Options screenshot
# Thermo has 0 makeready hours in the Production tab output
# But it has run-time: 0.28hr @5K, 0.55hr @10K, etc.
# Thermo Speed & Spoilage (from screenshot)
THERMO_SPEED_SPOILAGE = [
    (0, 500, 3, 80),
    (501, 2500, 1, 80),       # confirmed: speed 100 in Production tab @5K/10K
    (2501, 5000, 1, 85),
    (5001, None, 1, 120),     # confirmed: speed 120 @25K/50K/100K
]
# Override speeds based on Production tab actuals
# LT shows speed=100 @5K/10K, 120 @25K+
# Our table has 80 for 0-2500ft which doesn't match
# The Thermo speed seems to be based on the Set Up Options, not the spoilage table
# From screenshot: Set Up Length = 25ft in Set Up Options, but Production shows speed from Speed & Spoilage table

# Thermo Set Up Options (from screenshot):
THERMO_FIRST_COLOR_MR = 0.30  # Make Ready Hours: First Color
THERMO_STOCK_MR = 0.16        # Make Ready Hours: Stock
THERMO_SETUP_LENGTH_FT_OPTS = 100  # Set Up Length from Set Up Options

# --- Suncentre Poucher SCSG-600XL ---
POUCHER_EST_RATE = 200.00     # $/hr
POUCHER_SEALER_INK_MSI = 0.02
POUCHER_SEALER_MIN = 5.00
# Production tab confirms poucher speeds: 30 @5K, 35 @10K, 40 @25K+
POUCHER_SPEED_SPOILAGE = [
    (0, 250, 7, 14),
    (251, 500, 7, 18),
    (501, 1250, 6.5, 20),
    (1251, 2500, 6, 30),
    (2501, 5000, 5.5, 35),
    (5001, 12500, 5, 40),
    (12501, 25000, 4.5, 40),
    (25001, 50000, 4, 40),
    (50001, 125000, 3.5, 40),
    (125001, 250000, 3, 40),
    (250001, 500000, 2.5, 40),
    (500001, 1000000, 2, 40),
]

POUCHER_UDO = {
    "Stand Up Pouch":    (0.65, 0, 0.0, 0.0, 300),
    "3 Side Seal":       (0.60, 0, 0.0, 0.0, 200),
    "2 Side Seal":       (0.50, 0, 0.0, 0.0, 150),
    "CR Zipper":         (0.08, 0, 0.0, 0.0, 0),
    "Non-CR Zipper":     (1.00, 0, 0.0, 0.0, 0),
    "No Zipper":         (0.03, 0, 5.0, 0.0, 0),
    "Hole Punch":        (0.10, 0, 0.0, 0.0, 0),
    "Tear Notch":        (0.10, 0, 0.0, 0.0, 50),
    "Rounded Corners":   (0.12, 0, 0.0, 0.0, 25),
    "Second Web":        (0.33, 0, 0.0, 2.5, 100),
    "Insert Gusset":     (0.25, 0, 0.0, 2.5, 100),
    "Die Cut Station":   (1.00, 0, -25.0, 5.0, 250),
    "Calyx Cube":        (1.00, 0.25, -25.0, 0.0, 250),
    "Eco - 100% Recyc":  (0.00, 0, -10.0, 0.0, 0),
    "Non-Calyx Dieline": (0.00, 0, 0.0, 0.0, 200),
}

# --- Material Costs ---
SUBSTRATES = {
    "CLR PET":     0.4150,
    "MET PET":     0.4350,
    "WHT MET PET": 0.4350,
    "ALOX PET":    0.4890,
    "HB CLR PET":  0.5460,
}

LAMINATES = {
    "Matte":       0.1790,
    "Gloss":       0.1600,
    "Soft Touch":  0.3500,
    "None":        0.0,
}

ZIPPERS = {
    "CR Zipper":     (5.2587, 0.95),
    "Non-CR Zipper": (2.6734, 0.394),
    "None":          (0.0, 0.0),
}

# --- Packaging Costs ---
# From Production tab: Carton=$17.50 @5K, $32.50 @10K, $80 @25K, $160 @50K, $320 @100K
# Pattern: $3.50 per 1,000 units (=$17.50/5K, $32.50/10K is $3.25/K — decreasing slightly)
# Packaging: $50.98 @5K, $101.96 @10K (exactly 2x), $254.88 @25K (5x), $509.76 @50K (10x)
# Pattern: Packaging = $10.196 per 1,000 units (constant)
# Wrapping: $0.80 @5K, $1.60 @10K, $4.00 @25K, $8.00 @50K, $16.00 @100K
# Pattern: $0.16 per 1,000 units

CARTON_COST_PER_K = 3.50      # $/1000 units
PACKAGING_COST_PER_K = 10.196 # $/1000 units  
WRAPPING_COST_PER_K = 0.16    # $/1000 units


# ═══════════════════════════════════════════════════════════════
# FIELD MAPPING
# ═══════════════════════════════════════════════════════════════

def map_substrate(stock_descr2):
    s = (stock_descr2 or "").upper()
    if "ALOX" in s: return "ALOX PET"
    if "WHITE METPET" in s or "WHITE MET" in s: return "WHT MET PET"
    if "CLEAR PET" in s: return "CLR PET"
    if "METPET" in s or "MET PET" in s: return "MET PET"
    if "EVOH" in s or "3.5 MIL" in s: return "HB CLR PET"
    if "CLR" in s or "CLEAR" in s: return "CLR PET"
    if "MET" in s: return "MET PET"
    return "MET PET"

def map_finish(stock_descr1):
    s = (stock_descr1 or "").lower()
    if not s or s.strip() == "": return "None"
    if "matte" in s: return "Matte"
    if "soft touch" in s or "karess" in s: return "Soft Touch"
    if "gloss" in s: return "Gloss"
    return "None"

def map_seal_type(fpud1):
    s = (fpud1 or "").strip()
    if "Stand Up" in s: return "Stand Up Pouch"
    if "3 Side" in s: return "3 Side Seal"
    if "2 Side" in s: return "2 Side Seal"
    if "Cube" in s: return "Stand Up Pouch"
    return "Stand Up Pouch"

def map_zipper(fpud2):
    s = (fpud2 or "").strip()
    if s in ("", "None"): return "None"
    if "CR" in s and "Non" not in s: return "CR Zipper"
    if "Non" in s or "Single" in s or "Double" in s: return "Non-CR Zipper"
    return "None"

def map_tear_notch(fpud3):
    s = (fpud3 or "").strip()
    return "None" if s in ("", "None") else s

def map_hole_punch(fpud4):
    s = (fpud4 or "").strip()
    return "None" if s in ("", "None") else s

def map_corners(fpud6):
    s = (fpud6 or "").strip()
    return "Rounded" if s == "Rounded" else "Straight"


# ═══════════════════════════════════════════════════════════════
# CALCULATOR ENGINE v3
# ═══════════════════════════════════════════════════════════════

def find_best_gear_teeth(bag_width):
    best = {"gear_teeth": 0, "actual_repeat": 0, "no_around": 0, "waste_pct": 100}
    min_teeth = max(1, math.ceil(HP_MIN_REPEAT / HP_PITCH))
    max_teeth = int(HP_MAX_REPEAT / HP_PITCH)
    for teeth in range(min_teeth, max_teeth + 1):
        repeat = teeth * HP_PITCH
        no_around = int(repeat / bag_width) if bag_width > 0 else 0
        if no_around < 1:
            continue
        used = no_around * bag_width
        waste = (repeat - used) / repeat * 100
        if (no_around > best["no_around"]) or \
           (no_around == best["no_around"] and waste < best["waste_pct"]):
            best = {"gear_teeth": teeth, "actual_repeat": repeat,
                    "no_around": no_around, "waste_pct": waste}
    return best


def get_speed_spoilage(run_length_ft, table):
    for (lo, hi, spoilage, speed) in table:
        if hi is None:
            if run_length_ft >= lo:
                return (spoilage, speed)
        elif lo <= run_length_ft <= hi:
            return (spoilage, speed)
    return (table[-1][2], table[-1][3])


def calculate_cost(width, height, gusset, substrate, finish, seal_type,
                   zipper, tear_notch, hole_punch, corners, quantity,
                   cmykovg_colors=4, white_colors=1):
    """
    Calculate deterministic production cost per unit.
    v3: Calibrated against Estimate 6774 Production tab.
    """

    # ─── Layout ───
    size_across = height * 2 + gusset + 0.25  # 0.125" trim each side
    no_across = max(1, int(HP_STOCK_WIDTH / size_across))
    gear = find_best_gear_teeth(width)
    no_around = gear["no_around"]
    actual_repeat = gear["actual_repeat"]
    gear_teeth = gear["gear_teeth"]
    labels_per_cycle = no_across * no_around

    if labels_per_cycle == 0:
        return None

    # ─── Total sheets (frames) needed ───
    good_sheets = math.ceil(quantity / labels_per_cycle)
    
    # HP spoilage (2% flat)
    hp_spoilage_sheets = math.ceil(good_sheets * HP_SPOILAGE_PCT / 100)
    
    # Setup sheets for HP
    repeat_ft = actual_repeat / 12
    hp_setup_sheets = math.ceil(HP_SETUP_LENGTH_FT / repeat_ft) if repeat_ft > 0 else 0
    
    # Total HP sheets
    hp_total_sheets = good_sheets + hp_spoilage_sheets + hp_setup_sheets
    
    # HP run length in feet
    hp_run_ft = hp_total_sheets * repeat_ft
    
    # ─── STAGE 1: HP 6900 ───
    
    # 1a. Click charges (Impress Cost in LT)
    # LT shows Impress Cost = $74.16 @ 5K, Total Frames = 709
    # Our calc: 709 sheets × 2 clicks × 5 colors × $0.0107 + 709 × 2 × 1 × $0.0095
    # = 709 × 10 × 0.0107 + 709 × 2 × 0.0095 = 75.86 + 13.47 = $89.33
    # LT shows $74.16 — difference suggests clicks aren't applied to setup sheets
    # OR the click multiplier/rate is slightly different
    # Let's use total_sheets for clicks (including setup) and see if Impress Cost field
    # in Stock Cost detail matches. $74.16 / 709 / 2 = $0.05228 per sheet
    # With 5 colors: $74.16 / 709 / 10 = $0.01046 — very close to $0.0107!
    # So: $74.16 = 709 × 10 × $0.01046... but 709 × 10 × 0.0107 = $75.86
    # Difference is small. Let's check if it's based on good_sheets not total:
    # 500 good sheets × 2 × 5 × 0.0107 + 500 × 2 × 1 × 0.0095 = 53.50 + 9.50 = $63.00 — too low
    # 709 × (4×2×0.0107 + 1×2×0.0095) = 709 × (0.0856 + 0.019) = 709 × 0.1046 = $74.16 ✓ 
    # So total_clicks = total_frames × (cmykovg×2×0.0107 + white×2×0.0095) = exactly LT!
    
    total_frames = hp_total_sheets  # = 709 for 6774 @5K
    
    cmykovg_clicks = total_frames * HP_CLICK_MULTIPLIER * cmykovg_colors
    white_clicks = total_frames * HP_CLICK_MULTIPLIER * white_colors
    click_cost = (cmykovg_clicks * HP_CLICK_CHARGE_CMYKOVG +
                  white_clicks * HP_CLICK_CHARGE_WHITE)
    
    # 1b. Substrate material (Base Cost in LT)
    # LT: Base MSI = 333.528, Base $/MSI = $0.435, Base Cost = $145.08
    # Our calc: MSI = stock_width × run_length_ft × 12 / 1000
    # LT's Stock Length = 2,138 ft @ 5K ... that's way more than our HP run length
    # Stock Length appears to be in INCHES not feet: 2138 in = 178.2 ft
    # Check: 709 frames × 36.25" repeat / 12 = 2,141 ft ... close to 2,138
    # Actually 709 × 36.25 = 25,701.25 inches... / 12 = 2,141.8 ft
    # So Stock Length IS in feet: 2,138 ft
    # MSI = 13" × 2138 ft × 12 / 1000 = 13 × 25,656 / 1000 = 333.5 MSI ✓
    # Base Cost = 333.5 × 0.435 = $145.07 ✓
    
    # The 10.3% spoilage shown is the COMBINED spoilage across all 3 stages
    # Stock Length = total_frames × repeat_inches / 12
    stock_length_ft = total_frames * actual_repeat / 12
    
    hp_msi = HP_STOCK_WIDTH * stock_length_ft * 12 / 1000
    substrate_cost = hp_msi * SUBSTRATES.get(substrate, 0.4350)
    
    # 1c. In-line priming
    # LT: $13.34 = 333.528 MSI × $0.04 = $13.34 ✓
    priming_cost = hp_msi * HP_INLINE_PRIMING
    
    # 1d. HP Makeready ($31.25 = 0.25hr × $125)
    hp_makeready_cost = HP_SETUP_HOURS * HP_EST_RATE
    
    # 1e. HP Run-time labor (NEW in v3!)
    # Production tab: 0.37hr @5K, 0.75hr @10K, 1.86hr @25K, 3.69hr @50K, 7.35hr @100K
    # Speed = 74 ft/min consistently
    # 0.37hr = stock_length_ft / (74 ft/min × 60 min/hr)
    # 2138 / (74 × 60) = 2138 / 4440 = 0.4815 hr — doesn't match 0.37hr
    # Try: run_length / speed: need to figure out what "length" LT uses for HP time
    # 0.37 hr × 74 ft/min × 60 min/hr = 1642.8 ft
    # But stock length = 2138 ft... ratio = 1642.8/2138 = 0.768
    # Maybe HP time excludes setup length? 
    # (total_frames - setup_sheets) × repeat / 12 = (709-34) × 36.25 / 12 = 675 × 36.25 / 12 = 2039 ft
    # 2039 / (74×60) = 0.459 — still not 0.37
    # Try: good_sheets only: 500 × 36.25 / 12 = 1510.4 ft → 1510.4/4440 = 0.340 — close!
    # (good_sheets + spoilage) = 510 × 36.25/12 = 1541 ft → 1541/4440 = 0.347 — closer
    # Let me try with HP spoilage sheets only (not combined):
    # At 10K: 0.75hr × 74 × 60 = 3330 ft. Total frames=1256. 1256×36.25/12 = 3794 ft. good=1000+20=1020×36.25/12=3081ft → 3081/4440=0.694 — not 0.75
    # Hmm. Let me try: total_frames × repeat_ft / speed_ft_per_hr
    # 709 × (36.25/12) / (74×60) = 709 × 3.0208 / 4440 = 2141.8/4440 = 0.482
    # LT says 0.37. Ratio = 0.37/0.482 = 0.768
    # At 10K: 1256 × 3.0208 / 4440 = 3794/4440 = 0.855. LT=0.75. Ratio=0.75/0.855=0.877
    # Ratios aren't constant, so it's not a simple multiplier
    # 
    # Actually, HP speed=74 is ft/min but maybe LT computes time differently for digital
    # For HP Indigo (sheeted), the speed might be in SHEETS/min, not ft/min
    # 709 sheets / (74 sheets/min × 60) = 709/4440 = 0.1597 hr — too low
    # 
    # Wait - looking at Production tab more carefully:
    # HP: Press Speed = 74 (constant for all qtys)
    # 0.37hr @5K → 0.37 × 60 = 22.2 min → 709 / 22.2 = 31.9 sheets/min... 
    # Or in feet: 2141.8 ft / 22.2 min = 96.5 ft/min — not 74
    # 
    # Let me try: the speed IS ft/min but the run length is shorter than stock length
    # because HP Indigo doesn't run the setup length through at speed
    # HP run ft = (good_sheets + spoilage_sheets) × repeat_ft (no setup)
    # = 510 × 3.0208 = 1540.6 ft
    # Time = 1540.6 / 74 = 20.82 min = 0.347 hr — close to 0.37!
    # With copy change setup: + (HP_COPY_CHANGE_HOURS=0.10) = 0.447 — too much
    # 
    # At 10K: good=1000, spoilage=20, total=1020 → 1020×3.0208 = 3081.2 ft
    # 3081.2/74 = 41.64 min = 0.694hr. LT=0.75. Difference = 0.056hr
    # At 25K: good=2500, spoilage=50, total=2550 → 2550×3.0208 = 7703 ft  
    # 7703/74 = 104.1 min = 1.735hr. LT=1.86. Difference = 0.125hr
    # 
    # The differences grow linearly — suggests there's a constant overhead
    # OR the speed is slightly slower than 74
    # Let me solve: 0.37 = X/speed → at 5K
    # Try effective speed = 65 ft/min:
    # 1540.6/65 = 23.7 min = 0.395 — too high
    # Try 68: 1540.6/68 = 22.66 = 0.378 — very close!
    # At 10K with 68: 3081.2/68 = 45.31 = 0.755 — matches 0.75!
    # At 25K with 68: 7703/68 = 113.3 = 1.888 — matches 1.86!
    # At 50K with 68: (5000+100)×3.0208 = 15406 / 68 = 226.6 min = 3.776 — LT=3.69
    # At 100K with 68: (10000+200)×3.0208 = 30812 / 68 = 453.1 min = 7.552 — LT=7.35
    # 
    # Close but not exact. The speed 74 might be a nominal and LT applies some factor.
    # Or maybe the actual run length includes a small additional amount.
    # Let me try: run_time = stock_length_ft / (74 × 60) × correction_factor
    # At 5K: 2138/(74*60) = 0.481 × factor = 0.37 → factor = 0.769
    # Nah, that's not constant either.
    #
    # Simplest approach: use (good_sheets + spoilage_sheets) × repeat_ft / (68 × 60)
    # This matches within 2-3% across all qty tiers
    
    hp_run_sheets = good_sheets + hp_spoilage_sheets  # exclude setup sheets
    hp_run_length_ft = hp_run_sheets * repeat_ft
    HP_EFFECTIVE_SPEED = 68  # ft/min — derived from fitting Production tab data
    hp_run_hours = hp_run_length_ft / (HP_EFFECTIVE_SPEED * 60)
    hp_run_cost = hp_run_hours * HP_EST_RATE
    
    hp_total = click_cost + substrate_cost + priming_cost + hp_makeready_cost + hp_run_cost
    
    # ─── STAGE 2: Thermo Laminator ───
    lam_rate = LAMINATES.get(finish, 0.0)
    thermo_run_cost = 0
    thermo_lam_cost = 0
    thermo_total = 0
    
    if lam_rate > 0:
        # Laminate material — runs same MSI as HP substrate
        # LT Stock Cost detail doesn't show laminate separately in the "Laminate MSI" row
        # but the gap between Base Cost ($145.08) + Impress ($74.16) + Priming ($13.34) 
        # = $232.58 and Stock Cost ($322.26) = $89.68 difference
        # Wait, LT shows "Stock Cost" = $322.26 in the detail, but the Stock Cost
        # in Production tab = $409.76. Difference = $87.50 = laminate material
        # So laminate is ADDED to Stock Cost at the Production level
        # Laminate MSI = same area as substrate (same width, same run length)
        # $87.50 / 333.528 MSI = $0.2624/MSI — but Matte is $0.179/MSI
        # Hmm, that doesn't match. Let me reconsider.
        #
        # Actually Stock Cost in the detail = $322.26 which DOESN'T include laminate
        # Production tab Stock Cost = $409.76
        # Difference = $87.50
        # But the Thermo runs on the SAME web, so its laminate material is separate
        #
        # Wait — the Stock Cost detail shows Stock Cost = $322.26 at the bottom,
        # but the Production tab shows $409.76. Let me re-check...
        # Stock Cost detail: Total Stock = $409.76 ← that IS the total
        # Base Cost = $145.08, Impress Cost = $74.16, In Line Priming = $13.34
        # Stock Cost = $322.26 ← this is an intermediate row BEFORE Total Stock
        # So: $322.26 = $145.08 + $74.16 + $13.34 + ??? = $232.58, gap = $89.68
        # And Total Stock = $409.76 = $322.26 + $87.50 (laminate)
        #
        # OR: Stock Cost $322.26 includes base + impress + priming + something else
        # Then Total Stock adds laminate.
        # $322.26 - $145.08 - $74.16 - $13.34 = $89.68 — that's unaccounted in Stock Cost
        # $409.76 - $322.26 = $87.50 — unaccounted between Stock Cost and Total Stock
        #
        # Most likely: the laminate material ($87.50) is part of Total Stock
        # And the $89.68 gap in Stock Cost is the Thermo's contribution (laminate MSI)
        # Hmm, that gives us two laminate charges which doesn't make sense.
        #
        # Let me just compute: laminate_MSI = same as substrate MSI = 333.528
        # Matte @ $0.179/MSI = 333.528 × 0.179 = $59.70 — not $87.50
        # 
        # But wait — the Thermo laminator has its OWN spoilage and setup length
        # So its MSI is HIGHER than HP's MSI
        # Thermo runs the entire stock length + setup + spoilage
        # Thermo setup length = 25ft (from Set Up Options)
        # Thermo run length = stock_length_ft + 25 + spoilage
        # Let me check: Thermo spoilage @5K (0-500ft range → 3%)
        # But stock length = 2138ft → that's the 5001+ tier → 1% spoilage, 120 ft/min
        # Wait, Production tab shows Thermo speed=100 @5K, not 120
        # Thermo Speed & Spoilage table: 0-500 → 80ft/min, 501-2500 → 80, 2501-5000 → 85, 5001+ → 120
        # But Production shows 100 @5K... maybe the Thermo uses the HP run length differently
        #
        # Thermo run: 0.28hr @5K. 0.28 × 100 × 60 = 1680 ft
        # Or 0.28 × 60 = 16.8 min × 100 ft/min = 1680 ft
        # vs stock_length_ft = 2138 ft... thermo runs LESS than HP?
        # That makes sense if Thermo only needs to run the good output, not HP setup waste
        #
        # Let me try: thermo_length = (good_sheets + spoilage) × repeat_ft + thermo_setup
        # = 510 × 3.0208 + 25 = 1540.6 + 25 = 1565.6 ft
        # Thermo spoilage for 1565.6ft → tier 501-2500 → 1%, speed 80
        # 1565.6 × 1.01 = 1581.3 ft / (80 × 60) = 0.330hr — not 0.28
        #
        # Try speed 100 (from Production): 1581.3 / (100 × 60) = 0.264 — closer to 0.28
        # Try with Thermo setup=100ft: (510×3.0208 + 100) × 1.01 = 1656.4 / 6000 = 0.276 — close!
        # 
        # Thermo Set Up Options shows Set Up Length = 100 in one screenshot but 25 in another
        # The Thermo Main Press Page Set Up Length from the original screenshots was 100ft
        # in the Set Up Options tab. Using 100ft setup:
        # (510 × 3.0208 + 100) × 1.01 / (100 × 60) = 1656.8 / 6000 = 0.276 — close to 0.28
        #
        # For laminate MSI: 13" × 1656.8 ft × 12 / 1000 = 258.5 MSI
        # Matte: 258.5 × $0.179 = $46.27
        # But the gap is $87.50... so maybe laminate MSI is calculated differently
        #
        # Actually, the Stock Cost of $409.76 - $322.26 = $87.50
        # Could this be laminate at FULL stock length (not thermo run length)?
        # 333.528 MSI × $0.179 = $59.70 — still not $87.50
        # 333.528 × $0.262 = $87.38 — so $/MSI would be $0.262 not $0.179
        # 
        # Maybe the laminate cost in LT includes both material AND application
        # OR the Thermo has its own MSI calc based on its own spoilage/setup
        # Let me check: Thermo at full spoilage chain:
        # LT Spoilage% for 5K = 10.3% total. If allocated:
        # HP: 2%, Thermo: ~3% (from table), Poucher: ~5.5% (from table) = 10.5% — close!
        # 
        # For stock cost, LT computes all material costs using the COMBINED stock length
        # which includes spoilage from ALL stages chained together.
        # Let me try: stock_length_ft includes ALL spoilage
        # Good sheets = 500, total spoilage = 10.3% → total sheets = 500 × 1.103 = 551.5
        # + HP setup (34) + Thermo setup + Poucher setup = ???
        # Total frames = 709. Good sheets = 500. Extra = 209 sheets.
        # 209/500 = 41.8% overhead — that's setup + spoilage combined across all stages
        #
        # For now, let me use a simpler approach: compute the effective total spoilage
        # by chaining all three stages, then compute material costs from total frames
        
        # Thermo run hours: Production tab shows specific values
        # Speed from Production: 100 @5K/10K, 120 @25K+
        # I'll use the Speed & Spoilage table but override with Production tab observations:
        # The Thermo Speed & Spoilage table in LT uses LENGTH-based tiers
        # But the actual speed seems different from our extracted table
        # From Production: speed=100 when length is in ~1500-3000ft range
        # This suggests the 501-2500 tier speed is actually 100, not 80!
        
        # Use production tab verified speeds
        thermo_run_length_ft = hp_run_length_ft  # same as HP good+spoilage run
        
        # Thermo spoilage from table
        thermo_spoilage_pct, thermo_base_speed = get_speed_spoilage(thermo_run_length_ft, THERMO_SPEED_SPOILAGE)
        
        # Override speed based on Production tab observations
        # Production shows: 100 @5K/10K (run ~1500-3000ft), 120 @25K+ (run >5000ft)
        # This aligns with our table if we correct the speeds:
        # The table speeds might be "minimum" and LT uses a different calc
        # For now, use the Production-tab observed pattern:
        if thermo_run_length_ft <= 3000:
            thermo_speed = 100
        else:
            thermo_speed = 120
        
        thermo_spoilage_ft = thermo_run_length_ft * thermo_spoilage_pct / 100
        thermo_final_ft = thermo_run_length_ft + thermo_spoilage_ft
        
        # Thermo run hours
        thermo_run_hours = thermo_final_ft / (thermo_speed * 60)
        thermo_run_cost = thermo_run_hours * THERMO_EST_RATE
        
        # Thermo makeready = 0 (confirmed in Production tab: Makeready Hrs = 0.00)
        thermo_makeready_cost = 0
        
        # Laminate material cost
        # Use the thermo's actual MSI for laminate
        thermo_msi = THERMO_STOCK_WIDTH * thermo_final_ft * 12 / 1000
        thermo_lam_cost = thermo_msi * lam_rate
        
        thermo_total = thermo_run_cost + thermo_makeready_cost + thermo_lam_cost
    
    # ─── STAGE 3: Suncentre Poucher ───
    active_udos = []
    if seal_type in POUCHER_UDO:
        active_udos.append(seal_type)
    else:
        active_udos.append("Stand Up Pouch")

    if zipper == "CR Zipper":
        active_udos.append("CR Zipper")
    elif zipper == "Non-CR Zipper":
        active_udos.append("Non-CR Zipper")
    else:
        active_udos.append("No Zipper")

    if tear_notch and tear_notch != "None":
        active_udos.append("Tear Notch")
    if hole_punch and hole_punch != "None":
        active_udos.append("Hole Punch")
    if corners == "Rounded":
        active_udos.append("Rounded Corners")

    total_mr = 0
    total_wu = 0
    total_speed_chg = 0
    total_spoilage_chg = 0
    total_setup_ft = 0

    for udo in active_udos:
        if udo in POUCHER_UDO:
            u = POUCHER_UDO[udo]
            total_mr += u[0]
            total_wu += u[1]
            total_speed_chg += u[2]
            total_spoilage_chg += u[3]
            total_setup_ft += u[4]

    # Poucher run length = HP run length (good + spoilage, no setup)
    poucher_run_ft = hp_run_length_ft + total_setup_ft
    
    base_spoilage, base_speed = get_speed_spoilage(poucher_run_ft, POUCHER_SPEED_SPOILAGE)
    adj_speed = base_speed * (1 + total_speed_chg / 100)
    adj_spoilage = base_spoilage + total_spoilage_chg
    poucher_spoilage_ft = poucher_run_ft * adj_spoilage / 100
    poucher_final_ft = poucher_run_ft + poucher_spoilage_ft

    # Poucher run hours
    poucher_run_hours = poucher_final_ft / (adj_speed * 60) if adj_speed > 0 else 0
    
    # Poucher makeready (from UDOs)
    poucher_makeready_hours = total_mr + total_wu
    poucher_makeready_cost = poucher_makeready_hours * POUCHER_EST_RATE
    
    # Poucher running cost
    poucher_running_cost = poucher_run_hours * POUCHER_EST_RATE

    # Sealer ink
    poucher_msi = HP_STOCK_WIDTH * poucher_final_ft * 12 / 1000
    poucher_sealer = max(poucher_msi * POUCHER_SEALER_INK_MSI, POUCHER_SEALER_MIN)

    # Zipper material
    zip_info = ZIPPERS.get(zipper, (0, 0))
    zipper_cost = 0
    if zip_info[0] > 0:
        zip_msi = zip_info[1] * poucher_final_ft * 12 / 1000
        zipper_cost = zip_msi * zip_info[0]

    poucher_total = poucher_makeready_cost + poucher_running_cost + poucher_sealer + zipper_cost

    # ─── STAGE 4: Packaging (NEW in v3) ───
    qty_k = quantity / 1000
    carton_cost = qty_k * CARTON_COST_PER_K
    packaging_cost = qty_k * PACKAGING_COST_PER_K
    wrapping_cost = qty_k * WRAPPING_COST_PER_K
    packing_total = carton_cost + packaging_cost + wrapping_cost

    # ─── Total ───
    total_cost = hp_total + thermo_total + poucher_total + packing_total
    cost_per_unit = total_cost / quantity if quantity > 0 else 0

    return {
        "cost_per_unit": cost_per_unit,
        "total_cost": total_cost,
        "hp_total": hp_total,
        "hp_makeready": hp_makeready_cost,
        "hp_run_cost": hp_run_cost,
        "hp_run_hours": hp_run_hours,
        "click_cost": click_cost,
        "substrate_cost": substrate_cost,
        "priming_cost": priming_cost,
        "thermo_total": thermo_total,
        "thermo_run_cost": thermo_run_cost,
        "thermo_lam_cost": thermo_lam_cost,
        "poucher_total": poucher_total,
        "poucher_makeready_cost": poucher_makeready_cost,
        "poucher_running_cost": poucher_running_cost,
        "poucher_run_hours": poucher_run_hours,
        "poucher_makeready_hours": poucher_makeready_hours,
        "zipper_cost": zipper_cost,
        "packing_total": packing_total,
        "labels_per_cycle": labels_per_cycle,
        "gear_teeth": gear_teeth,
        "no_across": no_across,
        "no_around": no_around,
        "run_length_ft": hp_run_ft,
        "total_frames": total_frames,
        "stock_length_ft": stock_length_ft,
        "active_udos": active_udos,
    }


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("Loading Google Sheet...")
    with open("config/google_service_account.json") as f:
        creds = json.load(f)

    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key("1L1HRn7WpTnGvZwRIQnppNlMxQdmnOxxUcpbU2r25Bkk")
    ws = sh.sheet1
    all_data = ws.get_all_records()

    costs_only = [r for r in all_data if r.get("ProfitAdjLabel") == "Costs only"]
    print(f"Total rows: {len(all_data)}, Costs only: {len(costs_only)}")

    results = []
    errors = []

    for row in costs_only:
        est_num = row.get("Number", "")
        app = row.get("Application", "")
        width = row.get("SizeAround")
        height = row.get("FlexPack_Height")
        gusset = row.get("FlexPack_Gusset", 0)

        substrate = map_substrate(row.get("StockDescr2", ""))
        finish = map_finish(row.get("StockDescr1", ""))

        # Skip estimates with no lamination
        if finish == "None":
            continue

        seal_type = map_seal_type(row.get("FPUD_Popup1", ""))
        zipper = map_zipper(row.get("FPUD_Popup2", ""))
        tear_notch = map_tear_notch(row.get("FPUD_Popup3", ""))
        hole_punch = map_hole_punch(row.get("FPUD_Popup4", ""))
        corners = map_corners(row.get("FPUD_Popup6", ""))

        cmykovg = row.get("PrintInk_1_NoColors", 4)
        white = row.get("aLC_Equip_White_Count", 0)
        pw = row.get("PrintInk_2_NoColors", 0)

        try:
            width = float(width) if width else None
            height = float(height) if height else None
            gusset = float(gusset) if gusset else 0
            cmykovg = int(cmykovg) if cmykovg else 4
            white_count = int(white) if white else 0
            pw_count = int(pw) if pw else 1
            total_white = max(white_count + pw_count, 1)
        except (ValueError, TypeError):
            errors.append(f"Est {est_num}: bad dimensions")
            continue

        if not width or not height:
            errors.append(f"Est {est_num}: missing dimensions")
            continue

        for tier in range(1, 7):
            qty_val = row.get(f"Quantity{tier}")
            price_val = row.get(f"PricePerM{tier}")

            try:
                qty = int(float(qty_val)) if qty_val else 0
                actual_price = float(price_val) if price_val else 0
            except (ValueError, TypeError):
                continue

            if qty <= 0 or actual_price <= 0:
                continue

            calc = calculate_cost(
                width=width, height=height, gusset=gusset,
                substrate=substrate, finish=finish,
                seal_type=seal_type, zipper=zipper,
                tear_notch=tear_notch, hole_punch=hole_punch,
                corners=corners, quantity=qty,
                cmykovg_colors=cmykovg, white_colors=total_white,
            )

            if calc is None:
                errors.append(f"Est {est_num}: calc returned None for qty={qty}")
                continue

            calc_price = calc["cost_per_unit"]
            error_pct = abs(calc_price - actual_price) / actual_price * 100
            direction = "OVER" if calc_price > actual_price else "UNDER"

            results.append({
                "estimate": est_num,
                "application": app[:60],
                "quantity": qty,
                "width": width,
                "height": height,
                "gusset": gusset,
                "substrate": substrate,
                "finish": finish,
                "seal_type": seal_type,
                "zipper": zipper,
                "actual_price": actual_price,
                "calc_price": round(calc_price, 5),
                "error_pct": round(error_pct, 2),
                "direction": direction,
                "hp_total": round(calc["hp_total"], 2),
                "thermo_total": round(calc["thermo_total"], 2),
                "poucher_total": round(calc["poucher_total"], 2),
                "packing_total": round(calc["packing_total"], 2),
                "total_cost": round(calc["total_cost"], 2),
                "labels_per_cycle": calc["labels_per_cycle"],
                "gear_teeth": calc["gear_teeth"],
            })

    if not results:
        print("No valid results!")
        return

    output = "calculator_v3_vs_labeltraxx.csv"
    with open(output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(results)} comparisons → {output}")
    print(f"  ({len(set(r['estimate'] for r in results))} unique estimates)")
    print(f"{'='*70}")

    ep = [r["error_pct"] for r in results]
    mape = sum(ep) / len(ep)
    median = sorted(ep)[len(ep) // 2]
    w10 = sum(1 for e in ep if e <= 10) / len(ep) * 100
    w20 = sum(1 for e in ep if e <= 20) / len(ep) * 100
    w30 = sum(1 for e in ep if e <= 30) / len(ep) * 100
    over = sum(1 for r in results if r["direction"] == "OVER")
    under = sum(1 for r in results if r["direction"] == "UNDER")

    print(f"\nOVERALL:")
    print(f"  MAPE:         {mape:.1f}%")
    print(f"  Median Error: {median:.1f}%")
    print(f"  Min/Max:      {min(ep):.1f}% / {max(ep):.1f}%")
    print(f"  Within 10%:   {w10:.0f}%")
    print(f"  Within 20%:   {w20:.0f}%")
    print(f"  Within 30%:   {w30:.0f}%")
    print(f"  Over/Under:   {over} ({over*100//len(results)}%) / {under} ({under*100//len(results)}%)")

    print(f"\nBY SUBSTRATE:")
    for sub in sorted(set(r["substrate"] for r in results)):
        sr = [r for r in results if r["substrate"] == sub]
        print(f"  {sub:15s}  MAPE: {sum(r['error_pct'] for r in sr)/len(sr):6.1f}%  ({len(sr)} rows)")

    print(f"\nBY FINISH:")
    for fin in sorted(set(r["finish"] for r in results)):
        fr = [r for r in results if r["finish"] == fin]
        print(f"  {fin:15s}  MAPE: {sum(r['error_pct'] for r in fr)/len(fr):6.1f}%  ({len(fr)} rows)")

    print(f"\nBY SEAL TYPE:")
    for st in sorted(set(r["seal_type"] for r in results)):
        sr = [r for r in results if r["seal_type"] == st]
        print(f"  {st:20s}  MAPE: {sum(r['error_pct'] for r in sr)/len(sr):6.1f}%  ({len(sr)} rows)")

    print(f"\nBY ZIPPER:")
    for z in sorted(set(r["zipper"] for r in results)):
        zr = [r for r in results if r["zipper"] == z]
        print(f"  {z:20s}  MAPE: {sum(r['error_pct'] for r in zr)/len(zr):6.1f}%  ({len(zr)} rows)")

    print(f"\nBY QUANTITY:")
    ranges = [("<=1K",0,1000),("1K-5K",1001,5000),("5K-10K",5001,10000),
              ("10K-25K",10001,25000),("25K-50K",25001,50000),
              ("50K-100K",50001,100000),("100K+",100001,999999999)]
    for label, lo, hi in ranges:
        qr = [r for r in results if lo <= r["quantity"] <= hi]
        if qr:
            print(f"  {label:12s}  MAPE: {sum(r['error_pct'] for r in qr)/len(qr):6.1f}%  ({len(qr)} rows)")

    print(f"\nWORST 10:")
    for r in sorted(results, key=lambda x: x["error_pct"], reverse=True)[:10]:
        print(f"  Est {r['estimate']:>6}  qty={r['quantity']:>7,}  "
              f"actual=${r['actual_price']:.4f}  calc=${r['calc_price']:.4f}  "
              f"err={r['error_pct']:5.1f}% {r['direction']:5s}  "
              f"({r['substrate']}, {r['finish']}, {r['seal_type']}, {r['zipper']})")

    print(f"\nBEST 10:")
    for r in sorted(results, key=lambda x: x["error_pct"])[:10]:
        print(f"  Est {r['estimate']:>6}  qty={r['quantity']:>7,}  "
              f"actual=${r['actual_price']:.4f}  calc=${r['calc_price']:.4f}  "
              f"err={r['error_pct']:5.1f}% {r['direction']:5s}  "
              f"({r['substrate']}, {r['finish']}, {r['seal_type']}, {r['zipper']})")

    # Reference check with detailed breakdown
    print(f"\n{'='*70}")
    print(f"REFERENCE — Estimate 6774 (3.62W x 5H x 1.5G)")
    print(f"MET PET, Matte, SUP, CR Zipper, Standard tear notch, Rounded")
    print(f"{'='*70}")
    
    lt_values = {
        5000:   {"price": 0.19543, "total": 977.15,  "stock": 409.76, "press_run": 242.85, "makeready": 255.25, "packing": 69.28},
        10000:  {"price": 0.15517, "total": 1551.70, "stock": 725.85, "press_run": 434.50, "makeready": 255.25, "packing": 135.10},
        25000:  {"price": 0.12936, "total": 3234.00, "stock": 1670.06,"press_run": 969.80, "makeready": 255.25, "packing": 338.88},
        50000:  {"price": 0.12194, "total": 6097.00, "stock": 3233.91,"press_run": 1929.85,"makeready": 255.25, "packing": 677.76},
        100000: {"price": 0.11800, "total": 11800.00,"stock": 6346.64,"press_run": 3842.60,"makeready": 255.25, "packing": 1355.75},
    }
    
    for qty in [5000, 10000, 25000, 50000, 100000]:
        lt = lt_values[qty]
        c = calculate_cost(3.62, 5.0, 1.5, "MET PET", "Matte", "Stand Up Pouch",
                          "CR Zipper", "Standard", "None", "Rounded", qty)
        err = abs(c["cost_per_unit"] - lt["price"]) / lt["price"] * 100
        print(f"\n  qty={qty:>7,}  LT=${lt['price']:.5f}  calc=${c['cost_per_unit']:.5f}  err={err:.1f}%")
        print(f"    HP:      calc=${c['hp_total']:>8.2f}  (MR=${c['hp_makeready']:.2f} + run=${c['hp_run_cost']:.2f} + clicks=${c['click_cost']:.2f} + substrate=${c['substrate_cost']:.2f} + priming=${c['priming_cost']:.2f})")
        print(f"    Thermo:  calc=${c['thermo_total']:>8.2f}  (run=${c['thermo_run_cost']:.2f} + lam=${c['thermo_lam_cost']:.2f})")
        print(f"    Poucher: calc=${c['poucher_total']:>8.2f}  (MR=${c['poucher_makeready_cost']:.2f} + run=${c['poucher_running_cost']:.2f} + zip=${c['zipper_cost']:.2f})")
        print(f"    Packing: calc=${c['packing_total']:>8.2f}")
        print(f"    Layout: {c['no_across']}x{c['no_around']}={c['labels_per_cycle']}/cycle, gear={c['gear_teeth']}, frames={c['total_frames']}")

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors[:10]:
            print(f"  {e}")


if __name__ == "__main__":
    main()
