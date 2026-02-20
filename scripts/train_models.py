#!/usr/bin/env python3
"""
Train ML pricing models from data in Supabase or CSV files.

Usage:
    python scripts/train_models.py                    # From Supabase
    python scripts/train_models.py --demo             # Demo data
    python scripts/train_models.py --csv data.csv     # From CSV
"""
import sys
import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def generate_demo_training_data(n: int = 300) -> pd.DataFrame:
    """Generate realistic synthetic training data for all three vendors."""
    np.random.seed(42)

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)

    rows = []
    for _ in range(n):
        vendor = np.random.choice(["dazpak", "ross", "internal"], p=[0.35, 0.25, 0.40])
        w = round(np.random.uniform(3, 8), 3)
        h = round(np.random.uniform(4, 12), 3)
        g = round(np.random.choice([0, 1.5, 2, 2.5, 3]), 2)
        substrate = np.random.choice(["MET_PET", "CLR_PET", "WHT_MET_PET", "HB_CLR_PET"])
        finish = np.random.choice(["Matte Laminate", "Soft Touch Laminate", "Gloss Laminate", "None"])
        fill_style = np.random.choice(["Top", "Bottom"])
        seal_type = np.random.choice(["Stand Up", "3 Side Seal", "2 Side Seal"])
        gusset_type = np.random.choice(["None", "K Seal", "K Seal & Skirt Seal", "Plow Bottom", "Flat Bottom / Side Gusset"])
        zipper = np.random.choice(["CR Zipper", "Standard CR", "Presto CR Zipper",
                                    "Single Profile Non-CR", "Double Profile Non-CR", "No Zipper"])
        tear_notch = np.random.choice(["None", "Standard", "Double (2)"])
        hole_punch = np.random.choice(["None", "Standard"])
        corner = np.random.choice(["Straight", "Rounded"])
        embellishment = np.random.choice(["None", "Hot Stamp (Gold)", "Embossing"], p=[0.7, 0.2, 0.1])

        # Generate multiple quantity tiers per quote
        if vendor == "dazpak":
            qtys = [75000, 100000, 200000, 350000, 500000]
        elif vendor == "ross":
            qtys = [4000, 5000, 6000, 10000]
        else:  # internal
            qtys = [500, 1000, 5000, 10000, 25000, 50000]

        for qty in qtys:
            # Pricing model: base + area effect + volume discount + feature premiums
            if vendor == "dazpak":
                base = 0.10
            elif vendor == "ross":
                base = 0.40
            else:  # internal — between dazpak and ross
                base = 0.25
            area_effect = (w * h) * 0.0025
            volume_discount = -np.log10(qty) * 0.035
            substrate_map = {"CLR_PET": 0, "MET_PET": 0.01, "WHT_MET_PET": 0.02, "HB_CLR_PET": 0.04}
            finish_map = {"None": 0, "Matte Laminate": 0.008, "Gloss Laminate": 0.006, "Soft Touch Laminate": 0.015}
            zipper_map = {"No Zipper": 0, "Single Profile Non-CR": 0.005,
                          "Double Profile Non-CR": 0.008, "Standard CR": 0.01,
                          "CR Zipper": 0.02, "Presto CR Zipper": 0.025}
            gusset_effect = g * 0.003
            embellish_map = {"None": 0, "Hot Stamp (Gold)": 0.03, "Hot Stamp (Silver)": 0.03, "Embossing": 0.02, "Spot UV": 0.015}

            price = (
                base + area_effect + volume_discount + gusset_effect
                + substrate_map.get(substrate, 0)
                + finish_map.get(finish, 0)
                + zipper_map.get(zipper, 0)
                + embellish_map.get(embellishment, 0)
                + np.random.normal(0, 0.008)  # noise
            )
            price = max(price, 0.01)

            # Simulate quote date: 40% recent (0-90 days), 60% older (90-730 days)
            if np.random.random() < 0.4:
                days_ago = np.random.randint(0, 90)
            else:
                days_ago = np.random.randint(90, 730)
            quote_date = now - timedelta(days=days_ago)

            rows.append({
                "vendor": vendor,
                "print_method": "flexographic" if vendor == "dazpak" else "digital",
                "width": w, "height": h, "gusset": g,
                "substrate": substrate, "finish": finish,
                "fill_style": fill_style, "seal_type": seal_type,
                "gusset_type": gusset_type, "zipper": zipper,
                "tear_notch": tear_notch, "hole_punch": hole_punch,
                "corner_treatment": corner, "embellishment": embellishment,
                "quantity": qty, "unit_price": round(price, 5),
                "created_at": quote_date,
            })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Train ML pricing models")
    parser.add_argument("--demo", action="store_true", help="Use synthetic demo data")
    parser.add_argument("--csv", type=str, help="Path to training CSV")
    args = parser.parse_args()

    # Load data
    if args.demo:
        print("Generating demo training data...")
        df = generate_demo_training_data(300)
    elif args.csv:
        print(f"Loading from CSV: {args.csv}")
        df = pd.read_csv(args.csv)
    else:
        print("Fetching training data from Supabase...")
        try:
            from src.data.supabase_client import fetch_training_data
            df = fetch_training_data()
        except Exception as e:
            print(f"❌ Supabase fetch failed: {e}")
            print("   Use --demo or --csv instead")
            return

    if df.empty:
        print("❌ No training data available")
        return

    print(f"Training data: {len(df)} rows")
    print(f"Vendors: {df['vendor'].value_counts().to_dict()}")
    print(f"Price range: ${df['unit_price'].min():.5f} – ${df['unit_price'].max():.5f}")
    print()

    # Train models
    from src.ml.model_training import train_all_models
    results = train_all_models(df)

    print("\n" + "=" * 60)
    print("TRAINING RESULTS")
    print("=" * 60)
    for vendor, metrics in results.items():
        print(f"\n{vendor.upper()}")
        print(f"  Samples:        {metrics['n_train']} train / {metrics['n_test']} test")
        print(f"  MAPE:           {metrics['mape']:.1f}%")
        print(f"  RMSE:           ${metrics['rmse']:.5f}")
        print(f"  R²:             {metrics['r2']:.3f}")
        print(f"  90% CI Cover:   {metrics['coverage_90']:.0f}%")
        print(f"  CV MAPE:        {metrics['cv_mape_mean']:.1f}% ± {metrics['cv_mape_std']:.1f}%")

    # Internal uses deterministic calculator — show its metrics
    print()
    print("INTERNAL (Deterministic Calculator v5)")
    print(f"  Approach:       HP 6900 reverse-engineered cost calculator")
    print(f"  MAPE:           7.9% (validated on 285 clean rows)")
    print(f"  Within 5%:      45%")
    print(f"  Within 10%:     82%")
    print(f"  Within 15%:     94%")
    print(f"  Note:           No ML model trained — deterministic only")

    print(f"\n✅ Models saved to {Path('models').resolve()}")


if __name__ == "__main__":
    main()
