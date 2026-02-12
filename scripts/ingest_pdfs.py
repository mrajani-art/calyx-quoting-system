#!/usr/bin/env python3
"""
Extract pricing data from Dazpak/Ross PDF quotes and insert into Supabase.

Usage:
    python scripts/ingest_pdfs.py --vendor dazpak --folder ./data/dazpak_pdfs/
    python scripts/ingest_pdfs.py --vendor ross --folder ./data/ross_pdfs/
    python scripts/ingest_pdfs.py --vendor dazpak --file ./data/quote_13572.pdf
"""
import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

from src.data.pdf_extraction import (
    extract_dazpak_pdf, extract_ross_pdf,
    extract_all_pdfs, pdfs_to_dataframes,
)


def main():
    parser = argparse.ArgumentParser(description="Extract and ingest PDF quote data")
    parser.add_argument("--vendor", required=True, choices=["dazpak", "ross"])
    parser.add_argument("--folder", type=str, help="Folder containing PDFs")
    parser.add_argument("--file", type=str, help="Single PDF file")
    parser.add_argument("--dry-run", action="store_true", help="Extract only, don't insert")
    args = parser.parse_args()

    extractor = extract_dazpak_pdf if args.vendor == "dazpak" else extract_ross_pdf

    if args.file:
        print(f"Extracting single PDF: {args.file}")
        result = extractor(args.file)
        if result:
            _print_extracted(result)
            extracted = [result]
        else:
            print("❌ Failed to extract data from PDF")
            return
    elif args.folder:
        print(f"Extracting all PDFs from: {args.folder}")
        extracted = extract_all_pdfs(args.folder, args.vendor)
        print(f"\nExtracted {len(extracted)} quotes with pricing")
        for r in extracted:
            _print_extracted(r)
            print()
    else:
        parser.error("Must specify --folder or --file")
        return

    if args.dry_run or not extracted:
        print("\n[DRY RUN or no data] — skipping DB insertion")
        return

    # Convert to DataFrames
    quotes_df, prices_df = pdfs_to_dataframes(extracted)
    print(f"\nQuotes: {len(quotes_df)} rows")
    print(f"Prices: {len(prices_df)} rows")

    # Insert into Supabase
    try:
        from src.data.supabase_client import insert_quote
        inserted = 0
        for i, q_row in quotes_df.iterrows():
            q_data = q_row.dropna().to_dict()
            # Get prices for this quote
            q_prices = prices_df[prices_df["_temp_quote_idx"] == i].copy()
            q_prices = q_prices.drop(columns=["_temp_quote_idx"]).to_dict("records")

            qid = insert_quote(q_data, q_prices)
            if qid:
                inserted += 1

        print(f"\n✅ Inserted {inserted} quotes into Supabase")
    except Exception as e:
        print(f"\n❌ Supabase insertion failed: {e}")
        # Save locally instead
        out_dir = Path("data")
        out_dir.mkdir(exist_ok=True)
        quotes_df.to_csv(out_dir / f"{args.vendor}_quotes.csv", index=False)
        prices_df.to_csv(out_dir / f"{args.vendor}_prices.csv", index=False)
        print(f"   Saved CSVs to data/{args.vendor}_*.csv")


def _print_extracted(result: dict):
    """Pretty-print an extracted quote."""
    print(f"  FL#: {result.get('fl_number', '?')}")
    print(f"  Quote#: {result.get('quote_number', '?')} | Date: {result.get('quote_date', '?')}")
    print(f"  Dims: {result.get('width', '?')}W × {result.get('height', '?')}H × {result.get('gusset', 0)}G")
    print(f"  Vendor: {result.get('vendor')} | Print: {result.get('print_method')}")
    if result.get("prices"):
        print(f"  Pricing ({len(result['prices'])} tiers):")
        for p in result["prices"]:
            up = p.get("unit_price", 0)
            print(f"    {p['quantity']:>10,}  →  ${up:.5f}/ea")


if __name__ == "__main__":
    main()
