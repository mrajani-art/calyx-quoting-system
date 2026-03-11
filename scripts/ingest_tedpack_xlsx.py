#!/usr/bin/env python3
"""
Parse TedPack Excel pricing data into ML training CSV format.

Input:  TedPack_Quotes_Specs_Pricing.xlsx
Output: data/tedpack_training.csv (combined Air + Ocean rows)

Usage:
    python scripts/ingest_tedpack_xlsx.py [path_to_xlsx]
"""
import re
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_XLSX = Path.home() / "Downloads" / "TedPack_Quotes_Specs_Pricing_2.xlsx"


# ── Exclusion Rules ──────────────────────────────────────────────────

EXCLUDED_SUBSTRATES = {
    "PET/AL/NY/PE",
    "MOPP/PET/PE 25% PCR",
    "PCR METPET",
    "High Barrier Compostable",
    "Matte Oil+PET/PE-4MIL",
    "PET/VMPET/PE-4MIL",
    "MBOPP/VMPET/PE-4MIL",
}

EXCLUDED_FINISHES = {"Holographic Lam"}

EXCLUDED_EMBELLISHMENTS = {"Gold Foil"}

EXCLUDED_BAG_TYPES = {
    "Quad Seal (Flat Bottom)",
    "Stand Up (Flat Bottom)",
    "Corner Spout Pouch",
}

EXCLUDED_GUSSET_TYPES = {"Side Gusset"}


# ── Mapping Tables ───────────────────────────────────────────────────

SUBSTRATE_MAP = {
    "MET PET": "MET_PET",
    "METPET": "MET_PET",
    "MET PET / CLR Gusset": "MET_PET",
    "CLR PET": "CLR_PET",
    "Clear PET": "CLR_PET",
    "WHT PET": "WHT_MET_PET",
    "WHT MET PET": "WHT_MET_PET",
    "High Barrier Clear PET": "HB_CLR_PET",
    "High Barrier CLR PET": "HB_CLR_PET",
    "Alox Clear PET": "HB_CLR_PET",
    "PET/Alox-PET/PE-4MIL": "HB_CLR_PET",
}

FINISH_MAP = {
    "Soft Touch": "Soft Touch Laminate",
    "Matte": "Matte Laminate",
    "Full Matte": "Matte Laminate",
    "Gloss": "Gloss Laminate",
}

EMBELLISHMENT_MAP = {
    "Flat Spot UV": "Spot UV",
    "Spot UV": "Spot UV",
    "Holographic": "None",
    "Gold Foil": "Foil",
    "Silver Foil": "Foil",
    "Embossing": "Foil",
    "Hot Stamp (Gold)": "Foil",
    "Hot Stamp (Silver)": "Foil",
}

BAG_TYPE_TO_SEAL = {
    "Stand Up Pouch": "Stand Up Pouch",
    "Stand Up": "Stand Up Pouch",
    "3 Side Seal": "3 Side Seal - Bottom Fill",
    "3 Side Bottom Fill": "3 Side Seal - Bottom Fill",
    "3 Side Top Fill": "3 Side Seal - Top Fill",
    "2 Side Seal": "2 Side Seal - Top Fill",
}

BAG_TYPE_TO_FILL = {
    "3 Side Bottom Fill": "Bottom",
    "3 Side Top Fill": "Top",
    "3 Side Seal": "Bottom",  # default for ambiguous 3-side
    "2 Side Seal": "Top",
}

GUSSET_MAP = {
    "K Seal": "K Seal & Skirt Seal",
    "Doyen": "K Seal & Skirt Seal",
    "Doyen Seal": "K Seal & Skirt Seal",
    "K Seal & Skirt Seal": "K Seal & Skirt Seal",
    "Plow Bottom": "Plow Bottom",
    "Flat Bottom / Side Gusset": "Plow Bottom",
}

ZIPPER_MAP = {
    "CR Zipper": "CR Zipper",
    "Standard Zipper (Non-CR)": "Non-CR Zipper",
    "2-3 Track Zipper": "Non-CR Zipper",
}

CORNER_MAP = {
    "Rounded": "Rounded",
    "Round": "Rounded",
    "Straight": "Straight",
    "Per Artwork": "Straight",
}


def parse_size(size_str: str) -> tuple[float, float, float]:
    """Parse '4.25W×5.5H×1.38G' → (width, height, gusset)."""
    if not isinstance(size_str, str):
        return (0, 0, 0)
    # Normalize unicode multiplication sign
    s = size_str.replace("×", "x").replace("X", "x")
    w_match = re.search(r"([\d.]+)\s*W", s, re.IGNORECASE)
    h_match = re.search(r"([\d.]+)\s*H", s, re.IGNORECASE)
    g_match = re.search(r"([\d.]+)\s*G", s, re.IGNORECASE)
    width = float(w_match.group(1)) if w_match else 0
    height = float(h_match.group(1)) if h_match else 0
    gusset = float(g_match.group(1)) if g_match else 0
    return (width, height, gusset)


def parse_price(val) -> float:
    """Convert price value to float, handling '–' dashes and strings."""
    if isinstance(val, (int, float)) and not np.isnan(val):
        return float(val)
    if isinstance(val, str):
        v = val.strip()
        if v in ("–", "-", "—", ""):
            return np.nan
        try:
            return float(v.replace("$", "").replace(",", ""))
        except ValueError:
            return np.nan
    return np.nan


def ingest_tedpack(xlsx_path: str) -> pd.DataFrame:
    """Parse TedPack Excel into training DataFrame."""
    logger.info(f"Reading {xlsx_path}")
    df = pd.read_excel(xlsx_path, sheet_name="Quotes – Specs & DDP Pricing")
    logger.info(f"Raw rows: {len(df)}, unique quotes: {df['Bag ID'].nunique()}")

    # ── Step 1a: Exclusions ───────────────────────────────────────────
    before = len(df)
    mask_exclude = (
        df["Substrate"].isin(EXCLUDED_SUBSTRATES)
        | df["Finish"].isin(EXCLUDED_FINISHES)
        | df["Embellishment"].isin(EXCLUDED_EMBELLISHMENTS)
        | df["Bag Type"].isin(EXCLUDED_BAG_TYPES)
        | df["Gusset"].isin(EXCLUDED_GUSSET_TYPES)
    )
    df = df[~mask_exclude].copy()
    logger.info(f"Excluded {before - len(df)} rows → {len(df)} remaining "
                f"({df['Bag ID'].nunique()} quotes)")

    # ── Step 1b: Parse dimensions ─────────────────────────────────────
    dims = df["Size (W×H×G in.)"].apply(parse_size)
    df["width"] = dims.apply(lambda x: x[0])
    df["height"] = dims.apply(lambda x: x[1])
    df["gusset"] = dims.apply(lambda x: x[2])

    # ── Quantities: K pcs → actual units ──────────────────────────────
    df["quantity"] = (df["Qty (K pcs)"] * 1000).astype(int)

    # ── Parse prices ──────────────────────────────────────────────────
    df["ddp_air_price"] = df["DDP Air $/pc"].apply(parse_price)
    df["ddp_ocean_price"] = df["DDP Ocean $/pc"].apply(parse_price)

    # ── Map substrates ────────────────────────────────────────────────
    df["substrate"] = df["Substrate"].map(SUBSTRATE_MAP)
    unmapped = df["substrate"].isna()
    if unmapped.any():
        logger.warning(f"Unmapped substrates: {df.loc[unmapped, 'Substrate'].unique()}")
        df = df[~unmapped]

    # ── Map finishes ──────────────────────────────────────────────────
    df["finish"] = df["Finish"].map(FINISH_MAP).fillna("None")

    # ── Map embellishments ────────────────────────────────────────────
    df["embellishment"] = df["Embellishment"].map(EMBELLISHMENT_MAP).fillna("None")

    # ── Map bag type → seal_type + fill_style ─────────────────────────
    df["seal_type"] = df["Bag Type"].map(BAG_TYPE_TO_SEAL).fillna("Stand Up")
    df["fill_style"] = df["Bag Type"].map(BAG_TYPE_TO_FILL).fillna("Top")

    # ── Map gusset types ──────────────────────────────────────────────
    df["gusset_type"] = df["Gusset"].map(GUSSET_MAP).fillna("None")

    # ── Map zippers ───────────────────────────────────────────────────
    df["zipper"] = df["Zipper"].map(ZIPPER_MAP).fillna("No Zipper")

    # ── Map corners ───────────────────────────────────────────────────
    df["corner_treatment"] = df["Corners"].map(CORNER_MAP).fillna("Straight")

    # ── Fixed fields ──────────────────────────────────────────────────
    df["print_method"] = "gravure"
    df["tear_notch"] = "None"
    df["hole_punch"] = "None"
    df["created_at"] = pd.to_datetime(df["Quote Date"], errors="coerce")
    # Fall back to now for missing dates
    df["created_at"] = df["created_at"].fillna(pd.Timestamp.now(tz="UTC"))

    # ── Build output rows (one per vendor×price) ──────────────────────
    keep_cols = [
        "Bag ID", "width", "height", "gusset", "quantity",
        "substrate", "finish", "embellishment", "fill_style",
        "seal_type", "gusset_type", "zipper", "tear_notch",
        "hole_punch", "corner_treatment", "print_method", "created_at",
        "ddp_air_price", "ddp_ocean_price",
    ]
    out = df[keep_cols].copy()

    # Create Air rows
    air_df = out[out["ddp_air_price"].notna()].copy()
    air_df["vendor"] = "tedpack_air"
    air_df["unit_price"] = air_df["ddp_air_price"]

    # Create Ocean rows
    ocean_df = out[out["ddp_ocean_price"].notna()].copy()
    ocean_df["vendor"] = "tedpack_ocean"
    ocean_df["unit_price"] = ocean_df["ddp_ocean_price"]

    # Combine
    combined = pd.concat([air_df, ocean_df], ignore_index=True)
    combined = combined.drop(columns=["ddp_air_price", "ddp_ocean_price"])

    logger.info(f"Output: {len(combined)} training rows "
                f"({len(air_df)} air + {len(ocean_df)} ocean)")
    logger.info(f"Air price range: ${air_df['unit_price'].min():.4f} – "
                f"${air_df['unit_price'].max():.4f}")
    logger.info(f"Ocean price range: ${ocean_df['unit_price'].min():.4f} – "
                f"${ocean_df['unit_price'].max():.4f}")

    return combined


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest TedPack Excel into training CSV")
    parser.add_argument("xlsx_path", nargs="?", default=str(DEFAULT_XLSX),
                        help="Path to TedPack Excel file")
    parser.add_argument("--merge-existing", action="store_true",
                        help="Merge with existing tedpack_training.csv, deduplicating by (Bag ID, quantity, vendor)")
    args = parser.parse_args()

    df = ingest_tedpack(args.xlsx_path)

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "tedpack_training.csv"

    if args.merge_existing and out_path.exists():
        existing = pd.read_csv(out_path)
        logger.info(f"Merging with existing {out_path}: {len(existing)} rows")
        combined = pd.concat([existing, df], ignore_index=True)
        # Deduplicate: keep last occurrence (new data takes priority)
        combined = combined.drop_duplicates(
            subset=["Bag ID", "quantity", "vendor"],
            keep="last"
        )
        logger.info(f"After dedup: {len(combined)} rows (was {len(existing)} + {len(df)})")
        df = combined

    df.to_csv(out_path, index=False)
    logger.info(f"Saved to {out_path}")

    # Summary
    print(f"\n{'=' * 60}")
    print("TEDPACK INGESTION SUMMARY")
    print(f"{'=' * 60}")
    for vendor in ["tedpack_air", "tedpack_ocean"]:
        vdf = df[df["vendor"] == vendor]
        print(f"\n{vendor.upper()}")
        print(f"  Rows:       {len(vdf)}")
        print(f"  Quotes:     {vdf['Bag ID'].nunique()}")
        print(f"  Price:      ${vdf['unit_price'].min():.4f} – ${vdf['unit_price'].max():.4f}")
        print(f"  Qty range:  {vdf['quantity'].min():,} – {vdf['quantity'].max():,}")
    print(f"\nSubstrate dist:")
    print(df["substrate"].value_counts().to_string())
    print(f"\nSeal type dist:")
    print(df["seal_type"].value_counts().to_string())
    print(f"\nZipper dist:")
    print(df["zipper"].value_counts().to_string())


if __name__ == "__main__":
    main()
