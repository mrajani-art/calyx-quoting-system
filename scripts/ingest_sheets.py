#!/usr/bin/env python3
"""
Ingest historical quote requests from Google Sheets into Supabase.

Usage:
    python scripts/ingest_sheets.py
    python scripts/ingest_sheets.py --csv path/to/export.csv
"""
import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

from src.data.sheets_ingestion import load_from_gspread, load_from_csv, clean_sheet_data


def main():
    parser = argparse.ArgumentParser(description="Ingest Google Sheets quote data")
    parser.add_argument("--csv", type=str, help="Path to exported CSV (skip Google API)")
    parser.add_argument("--dry-run", action="store_true", help="Print data without inserting")
    args = parser.parse_args()

    # Load data
    if args.csv:
        print(f"Loading from CSV: {args.csv}")
        raw_df = load_from_csv(args.csv)
    else:
        print("Fetching from Google Sheets...")
        raw_df = load_from_gspread()

    print(f"Raw rows: {len(raw_df)}")
    print(f"Columns: {list(raw_df.columns)}")

    # Clean and normalize
    clean_df = clean_sheet_data(raw_df)
    print(f"\nCleaned rows: {len(clean_df)}")
    print(f"Vendors: {clean_df['vendor'].value_counts().to_dict()}")
    print(f"\nSample:")
    print(clean_df[["vendor", "fl_number", "width", "height", "gusset",
                     "substrate", "finish", "seal_type", "zipper"]].head(10).to_string())

    if args.dry_run:
        print("\n[DRY RUN] — no data inserted")
        return

    # Insert into Supabase
    try:
        from src.data.supabase_client import get_client
        client = get_client()

        # Note: The spreadsheet has specs but NOT prices.
        # Prices come from the PDF quotes.
        # We insert these as quote records without pricing tiers.
        records = clean_df.to_dict("records")
        # Remove non-schema columns
        schema_cols = [
            "vendor", "print_method", "fl_number", "source_type",
            "width", "height", "gusset",
            "substrate", "finish", "embellishment", "fill_style",
            "seal_type", "gusset_type", "zipper", "tear_notch",
            "hole_punch", "corner_treatment",
        ]
        clean_records = [{k: r.get(k) for k in schema_cols} for r in records]

        inserted = 0
        for i in range(0, len(clean_records), 100):
            batch = clean_records[i:i + 100]
            client.table("quotes").insert(batch).execute()
            inserted += len(batch)
            print(f"  Inserted {inserted}/{len(clean_records)}...")

        print(f"\n✅ Inserted {inserted} quote requests into Supabase")
    except Exception as e:
        print(f"\n❌ Supabase insertion failed: {e}")
        print("   Save as CSV instead:")
        out_path = "data/cleaned_sheet_data.csv"
        Path("data").mkdir(exist_ok=True)
        clean_df.to_csv(out_path, index=False)
        print(f"   Saved to {out_path}")


if __name__ == "__main__":
    main()
