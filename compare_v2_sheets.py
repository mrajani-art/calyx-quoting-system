#!/usr/bin/env python3
"""
Deterministic Internal Calculator v2 — Validation from Google Sheet
====================================================================
Pulls directly from the Label Traxx export Google Sheet, filters to
"Costs only" estimates, and compares against the deterministic calculator.

Usage:
    python compare_v2_sheets.py

Requires:
    pip install gspread
    config/google_service_account.json must exist
"""

import math
import csv
import json
import sys
from collections import Counter

try:
    import gspread
except ImportError:
    print("ERROR: pip install gspread")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — All values from Label Traxx screenshots
# ═══════════════════════════════════════════════════════════════

HP_EST_RATE = 125.00
HP_STOCK_WIDTH = 13.0
HP_PITCH = 0.125
HP_MAX_REPEAT = 38.0
HP_MIN_REPEAT = 0.5
HP_SETUP_HOURS = 0.25
HP_SETUP_LENGTH_FT = 100
HP_COPY_CHANGE_HOURS = 0.10
HP_COPY_CHANGE_LENGTH_FT = 30
HP_SPOILAGE_PCT = 2.0
HP_INLINE_PRIMING = 0.04
HP_CLICK_CHARGE_CMYKOVG = 0.0107
HP_CLICK_CHARGE_WHITE = 0.0095
HP_CLICK_MULTIPLIER = 2

THERMO_EST_RATE = 45.00
THERMO_STOCK_WIDTH = 13.0
THERMO_SETUP_LENGTH_FT = 25
THERMO_FIRST_COLOR_MR = 0.30
THERMO_STOCK_MR = 0.16
THERMO_INK_COST_MSI = 0.0001
THERMO_SPEED_SPOILAGE = [
    (0, 500, 3, 80),
    (501, 2500, 1, 80),
    (2501, 5000, 1, 85),
    (5001, None, 1, 120),
]

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
    "Stand Up Pouch":   (0.65, 0, 0.0, 0.0, 300),
    "3 Side Seal":      (0.60, 0, 0.0, 0.0, 200),
    "2 Side Seal":      (0.50, 0, 0.0, 0.0, 150),
    "CR Zipper":        (0.08, 0, 0.0, 0.0, 0),
    "Non-CR Zipper":    (1.00, 0, 0.0, 0.0, 0),
    "No Zipper":        (0.03, 0, 5.0, 0.0, 0),
    "Hole Punch":       (0.10, 0, 0.0, 0.0, 0),
    "Tear Notch":       (0.10, 0, 0.0, 0.0, 50),
    "Rounded Corners":  (0.12, 0, 0.0, 0.0, 25),
    "Second Web":       (0.33, 0, 0.0, 2.5, 100),
    "Insert Gusset":    (0.25, 0, 0.0, 2.5, 100),
    "Die Cut Station":  (1.00, 0, -25.0, 5.0, 250),
    "Calyx Cube":       (1.00, 0.25, -25.0, 0.0, 250),
    "Eco - 100% Recyc": (0.00, 0, -10.0, 0.0, 0),
    "Non-Calyx Dieline": (0.00, 0, 0.0, 0.0, 200),
}

SUBSTRATES = {
    "CLR PET":     0.4150,
    "MET PET":     0.4350,
    "WHT MET PET": 0.4350,
    "ALOX PET":    0.4890,
    "HB CLR PET":  0.5460,
}

LAMINATES = {
    "Matte":      0.1790,
    "Gloss":      0.1600,
    "Soft Touch":  0.3500,
    "None":       0.0,
}

ZIPPERS = {
    "CR Zipper":     (5.2587, 0.95),
    "Non-CR Zipper": (2.6734, 0.394),
    "None":          (0.0, 0.0),
}


# ═══════════════════════════════════════════════════════════════
# FIELD MAPPING — Label Traxx descriptions → calculator keys
# ═══════════════════════════════════════════════════════════════

def map_substrate(stock_descr2: str) -> str:
    s = (stock_descr2 or "").upper()
    if "ALOX" in s:
        return "ALOX PET"
    if "WHITE METPET" in s or "WHITE MET" in s:
        return "WHT MET PET"
    if "CLEAR PET" in s:
        return "CLR PET"
    if "METPET" in s or "MET PET" in s:
        return "MET PET"
    if "EVOH" in s or "3.5 MIL" in s:
        return "HB CLR PET"
    # Fallback: check for partial matches
    if "CLR" in s or "CLEAR" in s:
        return "CLR PET"
    if "MET" in s:
        return "MET PET"
    return "MET PET"


def map_finish(stock_descr1: str) -> str:
    s = (stock_descr1 or "").lower()
    if not s or s.strip() == "":
        return "None"
    if "matte" in s:
        return "Matte"
    if "soft touch" in s or "karess" in s:
        return "Soft Touch"
    if "gloss" in s:
        return "Gloss"
    return "None"


def map_seal_type(fpud1: str) -> str:
    s = (fpud1 or "").strip()
    if "Stand Up" in s:
        return "Stand Up Pouch"
    if "3 Side" in s:
        return "3 Side Seal"
    if "2 Side" in s:
        return "2 Side Seal"
    if "Cube" in s:
        return "Stand Up Pouch"
    if s == "":
        return "Stand Up Pouch"
    return "Stand Up Pouch"


def map_zipper(fpud2: str) -> str:
    s = (fpud2 or "").strip()
    if s in ("", "None"):
        return "None"
    if "CR" in s and "Non" not in s:
        return "CR Zipper"
    if "Non" in s or "Single" in s or "Double" in s:
        return "Non-CR Zipper"
    return "None"


def map_tear_notch(fpud3: str) -> str:
    s = (fpud3 or "").strip()
    if s in ("", "None"):
        return "None"
    return s  # "Standard", "Perforated", "Scored", etc.


def map_hole_punch(fpud4: str) -> str:
    s = (fpud4 or "").strip()
    if s in ("", "None"):
        return "None"
    return s


def map_corners(fpud6: str) -> str:
    s = (fpud6 or "").strip()
    if s == "Rounded":
        return "Rounded"
    if s == "Straight" or s == "":
        return "Straight"
    return "Straight"


# ═══════════════════════════════════════════════════════════════
# CALCULATOR ENGINE
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
    """Calculate deterministic production cost per unit."""

    # Layout
    size_across = height * 2 + gusset + 0.25
    no_across = max(1, int(HP_STOCK_WIDTH / size_across))
    gear = find_best_gear_teeth(width)
    no_around = gear["no_around"]
    actual_repeat = gear["actual_repeat"]
    labels_per_cycle = no_across * no_around

    if labels_per_cycle == 0:
        return None

    # Sheets
    good_sheets = math.ceil(quantity / labels_per_cycle)
    spoilage_sheets = math.ceil(good_sheets * HP_SPOILAGE_PCT / 100)
    total_sheets = good_sheets + spoilage_sheets
    repeat_ft = actual_repeat / 12
    setup_sheets = math.ceil(HP_SETUP_LENGTH_FT / repeat_ft) if repeat_ft > 0 else 0
    total_sheets_all = total_sheets + setup_sheets
    run_length_ft = total_sheets_all * repeat_ft

    # ─── STAGE 1: HP 6900 ───
    cmykovg_clicks = total_sheets_all * HP_CLICK_MULTIPLIER * cmykovg_colors
    white_clicks = total_sheets_all * HP_CLICK_MULTIPLIER * white_colors
    click_cost = (cmykovg_clicks * HP_CLICK_CHARGE_CMYKOVG +
                  white_clicks * HP_CLICK_CHARGE_WHITE)

    hp_msi = HP_STOCK_WIDTH * run_length_ft * 12 / 1000
    substrate_cost = hp_msi * SUBSTRATES.get(substrate, 0.4350)
    priming_cost = hp_msi * HP_INLINE_PRIMING
    hp_labor = HP_SETUP_HOURS * HP_EST_RATE

    hp_total = click_cost + substrate_cost + priming_cost + hp_labor

    # ─── STAGE 2: Thermo Laminator ───
    lam_rate = LAMINATES.get(finish, 0.0)
    if lam_rate > 0:
        thermo_total_ft = run_length_ft + THERMO_SETUP_LENGTH_FT
        thermo_spoilage_pct, thermo_speed = get_speed_spoilage(thermo_total_ft, THERMO_SPEED_SPOILAGE)
        thermo_final_ft = thermo_total_ft * (1 + thermo_spoilage_pct / 100)
        thermo_msi = THERMO_STOCK_WIDTH * thermo_final_ft * 12 / 1000
        lam_material = thermo_msi * lam_rate
        thermo_ink = thermo_msi * THERMO_INK_COST_MSI
        thermo_mr = THERMO_FIRST_COLOR_MR + THERMO_STOCK_MR
        thermo_run_hrs = thermo_final_ft / thermo_speed / 60 if thermo_speed > 0 else 0
        thermo_labor = (thermo_mr + thermo_run_hrs) * THERMO_EST_RATE
        thermo_total = lam_material + thermo_ink + thermo_labor
    else:
        thermo_total = 0

    # ─── STAGE 3: Suncentre Poucher ───
    active_udos = []
    # Seal type
    if seal_type in POUCHER_UDO:
        active_udos.append(seal_type)
    else:
        active_udos.append("Stand Up Pouch")

    # Zipper
    if zipper == "CR Zipper":
        active_udos.append("CR Zipper")
    elif zipper == "Non-CR Zipper":
        active_udos.append("Non-CR Zipper")
    else:
        active_udos.append("No Zipper")

    # Features
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

    poucher_total_ft = run_length_ft + total_setup_ft
    base_spoilage, base_speed = get_speed_spoilage(poucher_total_ft, POUCHER_SPEED_SPOILAGE)
    adj_speed = base_speed * (1 + total_speed_chg / 100)
    adj_spoilage = base_spoilage + total_spoilage_chg
    poucher_final_ft = poucher_total_ft * (1 + adj_spoilage / 100)

    poucher_run_hrs = poucher_final_ft / adj_speed / 60 if adj_speed > 0 else 0
    poucher_labor = (total_mr + total_wu + poucher_run_hrs) * POUCHER_EST_RATE

    poucher_msi = HP_STOCK_WIDTH * poucher_final_ft * 12 / 1000
    poucher_sealer = max(poucher_msi * POUCHER_SEALER_INK_MSI, POUCHER_SEALER_MIN)

    zip_info = ZIPPERS.get(zipper, (0, 0))
    zipper_cost = 0
    if zip_info[0] > 0:
        zip_msi = zip_info[1] * poucher_final_ft * 12 / 1000
        zipper_cost = zip_msi * zip_info[0]

    poucher_total = poucher_labor + poucher_sealer + zipper_cost

    # ─── Total ───
    total_cost = hp_total + thermo_total + poucher_total
    cost_per_unit = total_cost / quantity if quantity > 0 else 0

    return {
        "cost_per_unit": cost_per_unit,
        "total_cost": total_cost,
        "hp_total": hp_total,
        "thermo_total": thermo_total,
        "poucher_total": poucher_total,
        "click_cost": click_cost,
        "substrate_cost": substrate_cost,
        "lam_material": thermo_total if lam_rate > 0 else 0,
        "zipper_cost": zipper_cost,
        "labels_per_cycle": labels_per_cycle,
        "gear_teeth": gear["gear_teeth"],
        "no_across": no_across,
        "no_around": no_around,
        "run_length_ft": run_length_ft,
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

    # Filter to Costs only
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
        gusset_detail = row.get("FPUD_Popup5", "")

        # Get color config from the sheet
        cmykovg = row.get("PrintInk_1_NoColors", 4)
        white = row.get("Eq_PrintInk_1_NoColors", 0)  # or aLC_Equip_White_Count
        if not white:
            white = row.get("aLC_Equip_White_Count", 0)
        # Premium White from Colors tab
        pw = row.get("PrintInk_2_NoColors", 0)
        if not pw:
            pw = 1  # default 1 premium white

        try:
            width = float(width) if width else None
            height = float(height) if height else None
            gusset = float(gusset) if gusset else 0
            cmykovg = int(cmykovg) if cmykovg else 4
            white_count = int(white) if white else 0
            pw_count = int(pw) if pw else 1
            total_white = max(white_count + pw_count, 1)
        except (ValueError, TypeError):
            errors.append(f"Est {est_num}: bad dimensions w={width} h={height}")
            continue

        if not width or not height:
            errors.append(f"Est {est_num}: missing dimensions")
            continue

        # Process up to 6 quantity tiers
        for tier in range(1, 7):
            qty_val = row.get(f"Quantity{tier}")
            price_val = row.get(f"PricePerM{tier}")
            total_val = row.get(f"TotalEst{tier}")

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
                "tear_notch": tear_notch,
                "corners": corners,
                "cmykovg_colors": cmykovg,
                "white_colors": total_white,
                "actual_price": actual_price,
                "calc_price": round(calc_price, 5),
                "error_pct": round(error_pct, 2),
                "direction": direction,
                "hp_cost": round(calc["hp_total"], 2),
                "thermo_cost": round(calc["thermo_total"], 2),
                "poucher_cost": round(calc["poucher_total"], 2),
                "total_cost": round(calc["total_cost"], 2),
                "labels_per_cycle": calc["labels_per_cycle"],
                "gear_teeth": calc["gear_teeth"],
                "no_across": calc["no_across"],
                "no_around": calc["no_around"],
                "run_ft": round(calc["run_length_ft"], 1),
            })

    if not results:
        print("No valid results!")
        if errors:
            for e in errors:
                print(f"  {e}")
        return

    # Write CSV
    output = "calculator_vs_labeltraxx_costsonly.csv"
    with open(output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(results)} comparisons → {output}")
    print(f"  ({len(set(r['estimate'] for r in results))} unique estimates)")
    print(f"{'='*70}")

    # ─── Summary ───
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

    # By substrate
    print(f"\nBY SUBSTRATE:")
    for sub in sorted(set(r["substrate"] for r in results)):
        sr = [r for r in results if r["substrate"] == sub]
        print(f"  {sub:15s}  MAPE: {sum(r['error_pct'] for r in sr)/len(sr):6.1f}%  ({len(sr)} rows)")

    # By finish
    print(f"\nBY FINISH:")
    for fin in sorted(set(r["finish"] for r in results)):
        fr = [r for r in results if r["finish"] == fin]
        print(f"  {fin:15s}  MAPE: {sum(r['error_pct'] for r in fr)/len(fr):6.1f}%  ({len(fr)} rows)")

    # By seal type
    print(f"\nBY SEAL TYPE:")
    for st in sorted(set(r["seal_type"] for r in results)):
        sr = [r for r in results if r["seal_type"] == st]
        print(f"  {st:20s}  MAPE: {sum(r['error_pct'] for r in sr)/len(sr):6.1f}%  ({len(sr)} rows)")

    # By zipper
    print(f"\nBY ZIPPER:")
    for z in sorted(set(r["zipper"] for r in results)):
        zr = [r for r in results if r["zipper"] == z]
        print(f"  {z:20s}  MAPE: {sum(r['error_pct'] for r in zr)/len(zr):6.1f}%  ({len(zr)} rows)")

    # By quantity range
    print(f"\nBY QUANTITY:")
    ranges = [("≤1K",0,1000),("1K-5K",1001,5000),("5K-10K",5001,10000),
              ("10K-25K",10001,25000),("25K-50K",25001,50000),
              ("50K-100K",50001,100000),("100K+",100001,999999999)]
    for label, lo, hi in ranges:
        qr = [r for r in results if lo <= r["quantity"] <= hi]
        if qr:
            print(f"  {label:12s}  MAPE: {sum(r['error_pct'] for r in qr)/len(qr):6.1f}%  ({len(qr)} rows)")

    # Worst 10
    print(f"\nWORST 10:")
    for r in sorted(results, key=lambda x: x["error_pct"], reverse=True)[:10]:
        print(f"  Est {r['estimate']:>6}  qty={r['quantity']:>7,}  "
              f"actual=${r['actual_price']:.4f}  calc=${r['calc_price']:.4f}  "
              f"err={r['error_pct']:5.1f}% {r['direction']:5s}  "
              f"({r['substrate']}, {r['finish']}, {r['seal_type']}, {r['zipper']})")

    # Best 10
    print(f"\nBEST 10:")
    for r in sorted(results, key=lambda x: x["error_pct"])[:10]:
        print(f"  Est {r['estimate']:>6}  qty={r['quantity']:>7,}  "
              f"actual=${r['actual_price']:.4f}  calc=${r['calc_price']:.4f}  "
              f"err={r['error_pct']:5.1f}% {r['direction']:5s}  "
              f"({r['substrate']}, {r['finish']}, {r['seal_type']}, {r['zipper']})")

    # Reference check
    print(f"\n{'='*70}")
    print(f"REFERENCE — Estimate 6774 (FL-DL-1670, 3.62W×5H×1.5G)")
    print(f"{'='*70}")
    for qty, target in [(5000, 0.19543), (10000, 0.15517), (25000, 0.12936),
                         (50000, 0.12194), (100000, 0.11800)]:
        c = calculate_cost(3.62, 5.0, 1.5, "MET PET", "Matte", "Stand Up Pouch",
                          "CR Zipper", "Standard", "None", "Rounded", qty)
        print(f"  qty={qty:>7,}  LT=${target:.5f}  calc=${c['cost_per_unit']:.5f}  "
              f"err={abs(c['cost_per_unit']-target)/target*100:.1f}%")

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors[:10]:
            print(f"  {e}")


if __name__ == "__main__":
    main()
