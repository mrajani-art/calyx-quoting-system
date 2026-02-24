#!/usr/bin/env python3
"""
Deterministic Internal Calculator v4 — Multi-Estimate Calibrated
================================================================
Calibrated from Production tabs of Estimates 6774, 4984, 4996, 2201.

Key fixes from v3:
1. HP speed = 24.5 sheets/min × repeat_ft (not fixed 68 ft/min)
2. HP run_hours = (stock_length - HP_setup - poucher_setup) / (speed × 60)
3. Combined spoilage from fixed LT table (length-based tiers)
4. total_frames = ceil(good_sheets × (1 + spoilage%/100)) + setup_sheets
5. Zipper material in Stock Cost as 3rd Stock (same MSI basis as substrate)
6. Exclude estimates with Additional Cost > 0
7. Laminate $/MSI verified: Gloss=$0.16, Matte=$0.179 (4984 shows $0.22 but may be outlier)
8. Packaging costs refined from multiple estimates
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
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# --- HP 6900 Digital Press ---
HP_EST_RATE = 125.00
HP_STOCK_WIDTH = 13.0         # inches (FIXED)
HP_PITCH = 0.125              # inches per gear tooth
HP_MAX_REPEAT = 38.0          # inches
HP_MIN_REPEAT = 0.5
HP_SETUP_HOURS = 0.25         # Makeready hours ($31.25)
HP_SETUP_LENGTH_FT = 100      # feet
HP_SPOILAGE_PCT = 2.0         # flat 2%
HP_INLINE_PRIMING = 0.04      # $/MSI
HP_CLICK_CHARGE_CMYKOVG = 0.0107
HP_CLICK_CHARGE_WHITE = 0.0095
HP_CLICK_MULTIPLIER = 2
HP_SHEETS_PER_MIN = 24.5      # Fixed Indigo throughput (derived from 3 estimates)

# --- Thermo Laminator ---
THERMO_EST_RATE = 45.00
THERMO_STOCK_WIDTH = 13.0     # FIXED
# Thermo has 0 makeready in Production output
# Speed: 100 ft/min for stock_length <~3500ft, 120 for longer runs
# Thermo spoilage: 1% for runs >500ft (from Speed & Spoilage table)
THERMO_SPOILAGE_PCT = 1.0     # flat 1% (runs are always >500ft for our estimates)

# --- Suncentre Poucher SCSG-600XL ---
POUCHER_EST_RATE = 200.00
POUCHER_SEALER_INK_MSI = 0.02
POUCHER_SEALER_MIN = 5.00

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
    "Stand Up Pouch":    {"mr": 0.65, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 300},
    "3 Side Seal":       {"mr": 0.60, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 200},
    "2 Side Seal":       {"mr": 0.50, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 150},
    "CR Zipper":         {"mr": 0.08, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 0},
    "Non-CR Zipper":     {"mr": 1.00, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 0},
    "No Zipper":         {"mr": 0.03, "wu": 0, "speed": 5.0, "spoilage": 0.0, "setup": 0},
    "Hole Punch":        {"mr": 0.10, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 0},
    "Tear Notch":        {"mr": 0.10, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 50},
    "Rounded Corners":   {"mr": 0.12, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 25},
    "Second Web":        {"mr": 0.33, "wu": 0, "speed": 0.0, "spoilage": 2.5, "setup": 100},
    "Insert Gusset":     {"mr": 0.25, "wu": 0, "speed": 0.0, "spoilage": 2.5, "setup": 100},
    "Die Cut Station":   {"mr": 1.00, "wu": 0, "speed": -25.0, "spoilage": 5.0, "setup": 250},
    "Calyx Cube":        {"mr": 1.00, "wu": 0.25, "speed": -25.0, "spoilage": 0.0, "setup": 250},
    "Eco - 100% Recyc":  {"mr": 0.00, "wu": 0, "speed": -10.0, "spoilage": 0.0, "setup": 0},
    "Non-Calyx Dieline": {"mr": 0.00, "wu": 0, "speed": 0.0, "spoilage": 0.0, "setup": 200},
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
    "CR Zipper":     (5.2587, 0.95),    # $/MSI, width in inches
    "Non-CR Zipper": (2.6734, 0.394),
    "None":          (0.0, 0.0),
}

# --- Combined Spoilage Table (from Stock Cost across multiple estimates) ---
# This is LT's combined spoilage %, keyed by stock_length_ft
# Derived from: 6774, 4984, 4996 Production tabs
COMBINED_SPOILAGE_TABLE = [
    (0, 2000, 10.8),
    (2001, 3500, 10.3),
    (3501, 7000, 9.8),
    (7001, 15000, 9.2),
    (15001, 30000, 8.7),
    (30001, 55000, 8.2),
    (55001, 999999999, 7.7),
]

# --- Packaging Costs ---
# Verified across 6774, 4984, 4996
# Carton: ~$3.50-$4.00/K (varies slightly by bag size/weight)
# Packaging: ~$10.20-$11.91/K
# Wrapping: $0.16/K
# These scale linearly with quantity
CARTON_COST_PER_K = 3.75       # avg across estimates
PACKAGING_COST_PER_K = 10.70   # avg across estimates
WRAPPING_COST_PER_K = 0.16


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
    if "soft touch" in s or "karess" in s or "platinum" in s: return "Soft Touch"
    if "gloss" in s: return "Gloss"
    return "None"

def map_seal_type(fpud1):
    s = (fpud1 or "").strip()
    if "Stand Up" in s: return "Stand Up Pouch"
    if "3 Side Bottom" in s: return "3 Side Seal"
    if "3 Side Top" in s: return "3 Side Seal"
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
# CALCULATOR ENGINE v4
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


def get_poucher_speed_spoilage(run_length_ft):
    for (lo, hi, spoilage, speed) in POUCHER_SPEED_SPOILAGE:
        if lo <= run_length_ft <= hi:
            return (spoilage, speed)
    return (POUCHER_SPEED_SPOILAGE[-1][2], POUCHER_SPEED_SPOILAGE[-1][3])


def get_combined_spoilage(stock_length_ft):
    for (lo, hi, spoilage) in COMBINED_SPOILAGE_TABLE:
        if lo <= stock_length_ft <= hi:
            return spoilage
    return COMBINED_SPOILAGE_TABLE[-1][2]


def calculate_cost(width, height, gusset, substrate, finish, seal_type,
                   zipper, tear_notch, hole_punch, corners, quantity,
                   cmykovg_colors=4, white_colors=1):
    """v4 deterministic cost calculator."""

    # ─── Layout ───
    size_across = height * 2 + gusset + 0.25
    no_across = max(1, int(HP_STOCK_WIDTH / size_across))
    gear = find_best_gear_teeth(width)
    no_around = gear["no_around"]
    actual_repeat = gear["actual_repeat"]
    gear_teeth = gear["gear_teeth"]
    labels_per_cycle = no_across * no_around

    if labels_per_cycle == 0:
        return None

    repeat_ft = actual_repeat / 12
    good_sheets = math.ceil(quantity / labels_per_cycle)

    # ─── Collect Poucher UDOs ───
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

    total_mr = sum(POUCHER_UDO[u]["mr"] for u in active_udos if u in POUCHER_UDO)
    total_wu = sum(POUCHER_UDO[u]["wu"] for u in active_udos if u in POUCHER_UDO)
    total_speed_chg = sum(POUCHER_UDO[u]["speed"] for u in active_udos if u in POUCHER_UDO)
    total_spoilage_chg = sum(POUCHER_UDO[u]["spoilage"] for u in active_udos if u in POUCHER_UDO)
    poucher_setup_ft = sum(POUCHER_UDO[u]["setup"] for u in active_udos if u in POUCHER_UDO)

    # ─── Setup sheets ───
    hp_setup_sheets = math.ceil(HP_SETUP_LENGTH_FT / repeat_ft)
    poucher_setup_sheets = math.ceil(poucher_setup_ft / repeat_ft)
    total_setup_sheets = hp_setup_sheets + poucher_setup_sheets

    # ─── Combined spoilage (iterative: spoilage depends on stock_length) ───
    # Initial estimate of stock length to determine spoilage tier
    est_run_sheets = math.ceil(good_sheets * 1.10)  # initial 10% guess
    est_stock_length = (est_run_sheets + total_setup_sheets) * repeat_ft
    combined_spoilage_pct = get_combined_spoilage(est_stock_length)

    # Compute total frames using combined spoilage
    # total_frames = good_sheets × (1 + spoilage/100) + setup_sheets
    spoilage_sheets = math.ceil(good_sheets * combined_spoilage_pct / 100)
    total_frames = good_sheets + spoilage_sheets + total_setup_sheets

    # Recheck spoilage tier with actual stock length
    stock_length_ft = total_frames * repeat_ft
    new_spoilage_pct = get_combined_spoilage(stock_length_ft)
    if new_spoilage_pct != combined_spoilage_pct:
        combined_spoilage_pct = new_spoilage_pct
        spoilage_sheets = math.ceil(good_sheets * combined_spoilage_pct / 100)
        total_frames = good_sheets + spoilage_sheets + total_setup_sheets
        stock_length_ft = total_frames * repeat_ft

    # ─── HP Speed (ft/min) = 24.5 sheets/min × repeat_ft ───
    hp_speed_ftmin = HP_SHEETS_PER_MIN * repeat_ft

    # ─── STAGE 1: HP 6900 ───
    
    # Click charges (applied to total frames)
    cmykovg_clicks = total_frames * HP_CLICK_MULTIPLIER * cmykovg_colors
    white_clicks = total_frames * HP_CLICK_MULTIPLIER * white_colors
    click_cost = (cmykovg_clicks * HP_CLICK_CHARGE_CMYKOVG +
                  white_clicks * HP_CLICK_CHARGE_WHITE)

    # Substrate material
    hp_msi = HP_STOCK_WIDTH * stock_length_ft * 12 / 1000
    substrate_cost = hp_msi * SUBSTRATES.get(substrate, 0.4350)

    # In-line priming
    priming_cost = hp_msi * HP_INLINE_PRIMING

    # HP Makeready
    hp_makeready_cost = HP_SETUP_HOURS * HP_EST_RATE

    # HP Run-time labor: (stock_length - hp_setup - poucher_setup) / (speed × 60)
    hp_run_length_ft = stock_length_ft - HP_SETUP_LENGTH_FT - poucher_setup_ft
    hp_run_hours = max(0, hp_run_length_ft / (hp_speed_ftmin * 60))
    hp_run_cost = hp_run_hours * HP_EST_RATE

    hp_total = click_cost + substrate_cost + priming_cost + hp_makeready_cost + hp_run_cost

    # ─── STAGE 2: Thermo Laminator ───
    lam_rate = LAMINATES.get(finish, 0.0)
    thermo_run_cost = 0
    thermo_lam_cost = 0
    thermo_total = 0

    if lam_rate > 0:
        # Thermo runs on same stock as HP, its MSI is same as HP
        thermo_lam_cost = hp_msi * lam_rate

        # Thermo run hours: speed is 100 ft/min for short runs, 120 for longer
        thermo_speed = 100 if stock_length_ft <= 3500 else 120
        # Thermo run length ≈ stock_length - hp_setup (thermo processes everything HP outputs)
        thermo_run_ft = stock_length_ft - HP_SETUP_LENGTH_FT
        thermo_run_hours = thermo_run_ft / (thermo_speed * 60)
        thermo_run_cost = thermo_run_hours * THERMO_EST_RATE

        thermo_total = thermo_run_cost + thermo_lam_cost

    # ─── STAGE 3: Suncentre Poucher ───
    
    # Poucher run length and speed
    poucher_good_ft = good_sheets * repeat_ft
    poucher_run_ft = poucher_good_ft + poucher_setup_ft
    # Add spoilage from poucher table for accurate speed tier
    base_spoilage, base_speed = get_poucher_speed_spoilage(poucher_run_ft)
    adj_speed = base_speed * (1 + total_speed_chg / 100)
    
    # Poucher run hours (using the actual poucher length including spoilage)
    adj_spoilage = base_spoilage + total_spoilage_chg
    poucher_spoilage_ft = poucher_run_ft * adj_spoilage / 100
    poucher_total_ft = poucher_run_ft + poucher_spoilage_ft
    poucher_run_hours = poucher_total_ft / (adj_speed * 60) if adj_speed > 0 else 0

    # Poucher makeready
    poucher_makeready_hours = total_mr + total_wu
    poucher_makeready_cost = poucher_makeready_hours * POUCHER_EST_RATE
    poucher_running_cost = poucher_run_hours * POUCHER_EST_RATE

    # Sealer ink
    poucher_msi = HP_STOCK_WIDTH * poucher_total_ft * 12 / 1000
    poucher_sealer = max(poucher_msi * POUCHER_SEALER_INK_MSI, POUCHER_SEALER_MIN)

    # Zipper material — computed on stock MSI basis (3rd Stock in LT)
    # LT puts zipper cost in Stock Cost, using the full stock_length_ft
    # MSI = zipper_width × stock_length_ft × 12 / 1000
    zip_info = ZIPPERS.get(zipper, (0, 0))
    zipper_cost = 0
    if zip_info[0] > 0:
        zip_msi = zip_info[1] * stock_length_ft * 12 / 1000
        zipper_cost = zip_msi * zip_info[0]

    poucher_total = poucher_makeready_cost + poucher_running_cost + poucher_sealer + zipper_cost

    # ─── Packaging ───
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
        "hp_speed": hp_speed_ftmin,
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
        "total_frames": total_frames,
        "stock_length_ft": stock_length_ft,
        "combined_spoilage_pct": combined_spoilage_pct,
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
    skipped = {"no_finish": 0, "bad_dims": 0, "calc_fail": 0}

    for row in costs_only:
        est_num = row.get("Number", "")
        app = row.get("Application", "")
        width = row.get("SizeAround")
        height = row.get("FlexPack_Height")
        gusset = row.get("FlexPack_Gusset", 0)

        substrate = map_substrate(row.get("StockDescr2", ""))
        finish = map_finish(row.get("StockDescr1", ""))

        if finish == "None":
            skipped["no_finish"] += 1
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
            skipped["bad_dims"] += 1
            continue

        if not width or not height:
            skipped["bad_dims"] += 1
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
                skipped["calc_fail"] += 1
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
                "combined_spoilage": calc["combined_spoilage_pct"],
                "hp_speed": round(calc["hp_speed"], 1),
                "labels_per_cycle": calc["labels_per_cycle"],
                "gear_teeth": calc["gear_teeth"],
                "total_frames": calc["total_frames"],
            })

    if not results:
        print("No valid results!")
        return

    output = "calculator_v4_vs_labeltraxx.csv"
    with open(output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(results)} comparisons → {output}")
    print(f"  ({len(set(r['estimate'] for r in results))} unique estimates)")
    print(f"  Skipped: {skipped}")
    print(f"{'='*70}")

    ep = [r["error_pct"] for r in results]
    mape = sum(ep) / len(ep)
    median = sorted(ep)[len(ep) // 2]
    w5 = sum(1 for e in ep if e <= 5) / len(ep) * 100
    w10 = sum(1 for e in ep if e <= 10) / len(ep) * 100
    w15 = sum(1 for e in ep if e <= 15) / len(ep) * 100
    w20 = sum(1 for e in ep if e <= 20) / len(ep) * 100
    over = sum(1 for r in results if r["direction"] == "OVER")
    under = sum(1 for r in results if r["direction"] == "UNDER")

    print(f"\nOVERALL:")
    print(f"  MAPE:         {mape:.1f}%")
    print(f"  Median Error: {median:.1f}%")
    print(f"  Min/Max:      {min(ep):.1f}% / {max(ep):.1f}%")
    print(f"  Within  5%:   {w5:.0f}%")
    print(f"  Within 10%:   {w10:.0f}%")
    print(f"  Within 15%:   {w15:.0f}%")
    print(f"  Within 20%:   {w20:.0f}%")
    print(f"  Over/Under:   {over} ({over*100//len(results)}%) / {under} ({under*100//len(results)}%)")

    for label, key in [("SUBSTRATE", "substrate"), ("FINISH", "finish"),
                       ("SEAL TYPE", "seal_type"), ("ZIPPER", "zipper")]:
        print(f"\nBY {label}:")
        for val in sorted(set(r[key] for r in results)):
            sr = [r for r in results if r[key] == val]
            m = sum(r["error_pct"] for r in sr) / len(sr)
            print(f"  {val:20s}  MAPE: {m:6.1f}%  ({len(sr)} rows)")

    print(f"\nBY QUANTITY:")
    ranges = [("<=1K",0,1000),("1K-5K",1001,5000),("5K-10K",5001,10000),
              ("10K-25K",10001,25000),("25K-50K",25001,50000),
              ("50K-100K",50001,100000),("100K+",100001,999999999)]
    for label, lo, hi in ranges:
        qr = [r for r in results if lo <= r["quantity"] <= hi]
        if qr:
            m = sum(r["error_pct"] for r in qr) / len(qr)
            print(f"  {label:12s}  MAPE: {m:6.1f}%  ({len(qr)} rows)")

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

    # Reference checks
    print(f"\n{'='*70}")
    print(f"REFERENCE ESTIMATES")
    print(f"{'='*70}")

    refs = [
        ("6774", 3.62, 5.0, 1.5, "MET PET", "Matte", "Stand Up Pouch",
         "CR Zipper", "Standard", "None", "Rounded",
         {5000: 0.19543, 10000: 0.15517, 25000: 0.12936, 50000: 0.12194, 100000: 0.11800}),
    ]
    for name, w, h, g, sub, fin, st, zip_, tn, hp_, cor, prices in refs:
        print(f"\n--- Est {name} ({w}W×{h}H×{g}G, {sub}, {fin}, {st}, {zip_}) ---")
        for qty, lt_price in sorted(prices.items()):
            c = calculate_cost(w, h, g, sub, fin, st, zip_, tn, hp_, cor, qty)
            err = abs(c["cost_per_unit"] - lt_price) / lt_price * 100
            d = "OVER" if c["cost_per_unit"] > lt_price else "UNDER"
            print(f"  qty={qty:>7,}  LT=${lt_price:.5f}  calc=${c['cost_per_unit']:.5f}  "
                  f"err={err:.1f}% {d}  frames={c['total_frames']} spg={c['combined_spoilage_pct']}%")


if __name__ == "__main__":
    main()
