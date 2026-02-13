#!/usr/bin/env python3
"""
Ingest internal estimating data from the Cerm system Google Sheet
into Supabase for ML training.

Data source: Google Sheet with 846 columns from Cerm estimating software.
This script extracts the relevant fields and normalizes them into the
same quote/quote_prices schema used by Dazpak and Ross data.

Usage:
    python scripts/ingest_internal.py                          # From Google Sheet
    python scripts/ingest_internal.py --xlsx path/to/file.xlsx # From local xlsx
    python scripts/ingest_internal.py --dry-run                # Preview only
"""
import sys
import argparse
import logging
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ── Column Mapping from Cerm Export ──────────────────────────────
# The Cerm system exports 846 columns. We only need these:
CERM_COLUMNS = {
    # Identity
    "AdditionalDescr": "fl_number_raw",      # e.g. "FL-DL-1651 Cost Only"
    "Application": "description",             # Full spec description
    "Number": "estimate_number",              # Cerm estimate number
    "CustName": "customer_name",

    # Dimensions
    "SizeAround": "width",                    # Bag width (inches)
    "FlexPack_Height": "height",              # Bag height (inches)
    "FlexPack_Gusset": "gusset",              # Gusset depth (inches)
    "SizeAcross": "web_width",                # Web width (should be ≤ 12.25")

    # Material
    "StockDescr1": "lamination",              # Lamination layer
    "StockDescr2": "base_film",               # Base film structure
    "FaceStockMSI": "face_stock_msi",         # Material cost per MSI

    # Bag specifications (FPUD popups from Cerm)
    "FPUD_Popup1": "bag_type",                # Stand Up Pouch, 2 Side Seal, 3 Side Bottom Fill
    "FPUD_Popup2": "zipper_raw",              # CR Zipper, Single Profile, Double Profile
    "FPUD_Popup3": "tear_notch_raw",          # Standard, Custom Double
    "FPUD_Popup4": "hole_punch_raw",          # Euro, Round
    "FPUD_Popup5": "seal_type_raw",           # K-Seal, Plow Bottom
    "FPUD_Popup6": "corner_raw",              # Rounded, Straight

    # Equipment
    "Equip_ID": "equipment",                  # Thermo, etc.
    "PressNum": "press",                      # HP 6900
    "NoColors": "num_colors",                 # Number of print colors

    # Quantities (up to 6 tiers)
    "Quantity1": "qty1", "Quantity2": "qty2", "Quantity3": "qty3",
    "Quantity4": "qty4", "Quantity5": "qty5", "Quantity6": "qty6",

    # Unit prices per tier (PricePerM = price per each, verified)
    "PricePerM1": "price1", "PricePerM2": "price2", "PricePerM3": "price3",
    "PricePerM4": "price4", "PricePerM5": "price5", "PricePerM6": "price6",

    # Total estimates per tier
    "TotalEst1": "total1", "TotalEst2": "total2", "TotalEst3": "total3",
    "TotalEst4": "total4", "TotalEst5": "total5", "TotalEst6": "total6",

    # Press speeds per tier
    "PressSP1": "speed1", "PressSP2": "speed2", "PressSP3": "speed3",
    "PressSP4": "speed4", "PressSP5": "speed5", "PressSP6": "speed6",

    # Margin
    "Margin": "margin",

    # Date
    "EnteredDate": "entered_date",
}


def normalize_substrate(base_film: str, lamination: str) -> str:
    """Map Cerm base_film / lamination to canonical substrate codes."""
    bf = str(base_film or "").upper()
    if "METPET" in bf or "MET PET" in bf:
        if "WHITE" in bf or "WHT" in bf:
            return "WHT_MET_PET"
        return "MET_PET"
    if "ALOX" in bf:
        return "HB_CLR_PET"
    if "CLEAR" in bf or "CLR" in bf:
        return "CLR_PET"
    if "BOPP" in bf:
        return "CLR_PET"
    if "COMPOSTABLE" in bf:
        return "CUSTOM"
    return "MET_PET"  # Default for internal — most common


def normalize_finish(lamination: str, description: str) -> str:
    """Map Cerm lamination to canonical finish."""
    lam = str(lamination or "").lower()
    desc = str(description or "").lower()
    if "soft touch" in lam or "karess" in lam or "soft touch" in desc:
        return "Soft Touch Laminate"
    if "gloss" in lam or "gloss" in desc:
        return "Gloss Laminate"
    if "matte" in lam or "matte" in desc:
        return "Matte Laminate"
    if "holografik" in lam:
        return "Holographic"
    return "Matte Laminate"  # Default


def normalize_seal_type(bag_type: str) -> str:
    """Map FPUD_Popup1 bag type to canonical seal_type."""
    bt = str(bag_type or "").lower()
    if "stand up" in bt:
        return "Stand Up"
    if "3 side" in bt:
        return "3 Side Seal"
    if "2 side" in bt:
        return "2 Side Seal"
    return "Stand Up"


def normalize_zipper(zipper_raw: str) -> str:
    """Map FPUD_Popup2 zipper to canonical value."""
    z = str(zipper_raw or "").lower()
    if "cr zipper" in z and "non" not in z:
        return "CR Zipper"
    if "double profile" in z:
        return "Double Profile Non-CR"
    if "single profile" in z or "non cr" in z:
        return "Single Profile Non-CR"
    return "No Zipper"


def normalize_tear_notch(raw: str) -> str:
    tn = str(raw or "").lower()
    if "double" in tn or "custom" in tn:
        return "Double (2)"
    if "standard" in tn:
        return "Standard"
    return "None"


def normalize_hole_punch(raw: str) -> str:
    hp = str(raw or "").lower()
    if "euro" in hp:
        return "Euro Slot"
    if "round" in hp:
        return "Round (Butterfly)"
    return "None"


def normalize_gusset_type(seal_raw: str) -> str:
    """Map FPUD_Popup5 to gusset type."""
    s = str(seal_raw or "").lower().strip()
    if not s or s in ("none", "0", "0.0", "nan"):
        return "None"
    if "k-seal" in s or "k seal" in s:
        return "K Seal"
    if "plow" in s:
        return "Plow Bottom"
    return "None"


def normalize_corner(raw: str) -> str:
    c = str(raw or "").lower()
    if "round" in c:
        return "Rounded"
    return "Straight"


def extract_fl_number(desc: str) -> str:
    """Extract FL-XX-NNNN from the description field."""
    import re
    m = re.search(r'(FL-[A-Z]{2}-\d+)', str(desc or ""))
    return m.group(1) if m else ""


def load_from_google_sheet() -> pd.DataFrame:
    """Fetch the internal estimates Google Sheet."""
    from config.settings import INTERNAL_SHEET_ID
    import gspread
    from google.oauth2.service_account import Credentials
    from config.settings import GOOGLE_CREDENTIALS

    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(INTERNAL_SHEET_ID)
    ws = sh.sheet1
    data = ws.get_all_records()
    return pd.DataFrame(data)


def load_from_xlsx(path: str) -> pd.DataFrame:
    """Load from a local xlsx export."""
    return pd.read_excel(path)


def process_internal_data(raw_df: pd.DataFrame) -> list[dict]:
    """
    Process raw Cerm data into normalized quote records.
    Returns list of dicts ready for Supabase insertion.
    """
    # Rename columns using our mapping
    rename_map = {}
    for cerm_col, our_col in CERM_COLUMNS.items():
        if cerm_col in raw_df.columns:
            rename_map[cerm_col] = our_col
    df = raw_df.rename(columns=rename_map)

    records = []
    skipped = 0

    for _, row in df.iterrows():
        # Extract dimensions
        width = float(row.get("width", 0) or 0)
        height = float(row.get("height", 0) or 0)
        gusset = float(row.get("gusset", 0) or 0)

        if width <= 0 or height <= 0:
            skipped += 1
            continue

        # FL number
        fl_number = extract_fl_number(row.get("fl_number_raw", ""))
        if not fl_number:
            fl_number = extract_fl_number(row.get("description", ""))

        # Normalize specs
        substrate = normalize_substrate(
            row.get("base_film", ""), row.get("lamination", ""))
        finish = normalize_finish(
            row.get("lamination", ""), row.get("description", ""))
        seal_type = normalize_seal_type(row.get("bag_type", ""))
        zipper = normalize_zipper(row.get("zipper_raw", ""))
        tear_notch = normalize_tear_notch(row.get("tear_notch_raw", ""))
        hole_punch = normalize_hole_punch(row.get("hole_punch_raw", ""))
        gusset_type = normalize_gusset_type(row.get("seal_type_raw", ""))
        corner = normalize_corner(row.get("corner_raw", ""))

        # Extract quantity/price tiers
        prices = []
        for i in range(1, 7):
            qty = float(row.get(f"qty{i}", 0) or 0)
            price = float(row.get(f"price{i}", 0) or 0)
            total = float(row.get(f"total{i}", 0) or 0)

            if qty > 0 and price > 0:
                # Sanity check: price should be reasonable per-unit ($0.001 - $50)
                if price < 0.001 or price > 50:
                    continue
                prices.append({
                    "quantity": int(qty),
                    "unit_price": round(price, 5),
                    "total_price": round(total, 2) if total > 0 else round(qty * price, 2),
                    "tier_index": i,
                })

        if not prices:
            skipped += 1
            continue

        record = {
            "vendor": "internal",
            "print_method": "digital",
            "fl_number": fl_number,
            "source_type": "spreadsheet",
            "source_file": "cerm_estimates",
            "width": round(width, 3),
            "height": round(height, 3),
            "gusset": round(gusset, 3),
            "substrate": substrate,
            "finish": finish,
            "seal_type": seal_type,
            "gusset_type": gusset_type,
            "zipper": zipper,
            "tear_notch": tear_notch,
            "hole_punch": hole_punch,
            "corner_treatment": corner,
            "embellishment": "None",
            "fill_style": "Top" if "top" in str(row.get("bag_type", "")).lower() else "Bottom",
            "prices": prices,
        }
        records.append(record)

    logger.info(f"Processed {len(records)} valid estimates, skipped {skipped}")
    return records


def insert_to_supabase(records: list[dict]) -> int:
    """Insert processed records into Supabase."""
    from src.data.supabase_client import get_client
    client = get_client()
    inserted = 0

    for rec in records:
        prices = rec.pop("prices")
        try:
            res = client.table("quotes").insert(rec).execute()
            quote_id = res.data[0]["id"]
            for p in prices:
                p["quote_id"] = quote_id
            if prices:
                client.table("quote_prices").insert(prices).execute()
            inserted += 1
        except Exception as e:
            logger.error(f"Insert failed for {rec.get('fl_number')}: {e}")

    return inserted


def main():
    parser = argparse.ArgumentParser(description="Ingest internal Cerm estimates")
    parser.add_argument("--xlsx", type=str, help="Path to local xlsx file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")
    parser.add_argument("--csv-out", type=str, help="Save processed data as CSV")
    args = parser.parse_args()

    # Load data
    if args.xlsx:
        print(f"Loading from xlsx: {args.xlsx}")
        raw_df = load_from_xlsx(args.xlsx)
    else:
        print("Fetching from Google Sheet...")
        try:
            raw_df = load_from_google_sheet()
        except Exception as e:
            print(f"❌ Google Sheet fetch failed: {e}")
            print("   Use --xlsx path/to/file.xlsx instead")
            return

    print(f"Raw data: {len(raw_df)} rows × {len(raw_df.columns)} columns")

    # Process
    records = process_internal_data(raw_df)
    print(f"\n✅ Processed {len(records)} valid estimates")

    # Stats
    total_tiers = sum(len(r["prices"]) for r in records)
    all_prices = [p["unit_price"] for r in records for p in r["prices"]]
    all_qtys = [p["quantity"] for r in records for p in r["prices"]]

    print(f"   Total price tiers: {total_tiers}")
    if all_prices:
        print(f"   Price range: ${min(all_prices):.5f} – ${max(all_prices):.5f}")
        print(f"   Quantity range: {min(all_qtys):,} – {max(all_qtys):,}")

    # Preview
    if args.dry_run or True:
        print(f"\n{'─'*70}")
        print("SAMPLE RECORDS:")
        print(f"{'─'*70}")
        for r in records[:5]:
            print(f"\n  {r['fl_number']} | {r['width']}W × {r['height']}H × {r['gusset']}G")
            print(f"    Substrate: {r['substrate']} | Finish: {r['finish']}")
            print(f"    Seal: {r['seal_type']} | Zipper: {r['zipper']} | Gusset: {r['gusset_type']}")
            for p in r["prices"]:
                print(f"    Tier {p['tier_index']}: {p['quantity']:>8,} × ${p['unit_price']:.5f} = ${p['total_price']:>10,.2f}")

    # Save CSV
    if args.csv_out:
        flat_rows = []
        for r in records:
            base = {k: v for k, v in r.items() if k != "prices"}
            for p in r["prices"]:
                flat_rows.append({**base, **p})
        csv_df = pd.DataFrame(flat_rows)
        csv_df.to_csv(args.csv_out, index=False)
        print(f"\n💾 Saved to {args.csv_out}")

    # Insert
    if not args.dry_run:
        print("\nInserting into Supabase...")
        try:
            count = insert_to_supabase(records)
            print(f"✅ Inserted {count} estimates into Supabase")
        except Exception as e:
            print(f"❌ Supabase insertion failed: {e}")
            # Fallback: save as CSV
            fallback = "data/internal_estimates.csv"
            flat_rows = []
            for r in records:
                base = {k: v for k, v in r.items() if k != "prices"}
                for p in r["prices"]:
                    flat_rows.append({**base, **p})
            pd.DataFrame(flat_rows).to_csv(fallback, index=False)
            print(f"   Saved as CSV instead: {fallback}")


if __name__ == "__main__":
    main()
