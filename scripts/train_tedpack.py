#!/usr/bin/env python3
"""
Train TedPack Air and Ocean models from ingested CSV,
then simulate predictions against all training data and report accuracy.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from src.ml.model_training import QuoteModelTrainer
from src.ml.feature_engineering import prepare_features

CSV_PATH = ROOT / "data" / "tedpack_training.csv"


def train_models():
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows from {CSV_PATH}")

    results = {}
    for vendor in ["tedpack_air", "tedpack_ocean"]:
        vdf = df[df["vendor"] == vendor].copy()
        if vdf.empty:
            print(f"No data for {vendor} — skipping")
            continue

        print(f"\n{'='*60}")
        print(f"Training {vendor}: {len(vdf)} samples")
        print(f"Price range: ${vdf['unit_price'].min():.4f} – ${vdf['unit_price'].max():.4f}")
        print(f"{'='*60}")

        trainer = QuoteModelTrainer(vendor, use_log_target=True)
        metrics = trainer.train(vdf)
        trainer.save()
        results[vendor] = (trainer, metrics)

        print(f"\nMetrics:")
        print(f"  MAPE:          {metrics['mape']:.1f}%")
        print(f"  RMSE:          ${metrics['rmse']:.5f}")
        print(f"  R²:            {metrics['r2']:.3f}")
        print(f"  90% CI Cover:  {metrics['coverage_90']:.1f}%")
        print(f"  CV MAPE:       {metrics['cv_mape_mean']:.1f}% ± {metrics['cv_mape_std']:.1f}%")
        print(f"  Train/Test:    {metrics['n_train']}/{metrics['n_test']}")

    return results


def simulate_accuracy(results):
    """Predict on every row in the training CSV and compare vs actual."""
    df = pd.read_csv(CSV_PATH)
    print(f"\n{'='*60}")
    print("SIMULATION: Predicting on all training data")
    print(f"{'='*60}")

    sim_rows = []
    for vendor, (trainer, _) in results.items():
        vdf = df[df["vendor"] == vendor].copy()
        if vdf.empty:
            continue

        vdf_feat = prepare_features(vdf.copy())
        X = trainer.preprocessor.transform(vdf_feat)

        pred_raw = trainer.model_point.predict(X)
        lower_raw = trainer.model_lower.predict(X)
        upper_raw = trainer.model_upper.predict(X)

        if trainer.use_log_target:
            pred = np.exp(pred_raw)
            lower = np.exp(lower_raw)
            upper = np.exp(upper_raw)
        else:
            pred = pred_raw
            lower = lower_raw
            upper = upper_raw

        actual = vdf["unit_price"].values
        error_pct = np.abs(pred - actual) / np.clip(actual, 1e-6, None) * 100

        for i, (_, row) in enumerate(vdf.iterrows()):
            sim_rows.append({
                "vendor": vendor,
                "bag_id": row.get("fl_number", ""),
                "substrate": row.get("substrate", ""),
                "width": row.get("width"),
                "height": row.get("height"),
                "gusset": row.get("gusset"),
                "quantity": row.get("quantity"),
                "actual_price": actual[i],
                "predicted_price": round(pred[i], 5),
                "lower_bound": round(lower[i], 5),
                "upper_bound": round(upper[i], 5),
                "error_pct": round(error_pct[i], 2),
                "in_ci": bool(actual[i] >= lower[i] and actual[i] <= upper[i]),
            })

    sim_df = pd.DataFrame(sim_rows)
    out_path = ROOT / "data" / "tedpack_simulation.csv"
    sim_df.to_csv(out_path, index=False)
    print(f"\nSaved simulation to {out_path}")

    # Summary stats per vendor
    for vendor in sim_df["vendor"].unique():
        vsim = sim_df[sim_df["vendor"] == vendor]
        print(f"\n--- {vendor} ({len(vsim)} rows) ---")
        print(f"  Mean error:     {vsim['error_pct'].mean():.1f}%")
        print(f"  Median error:   {vsim['error_pct'].median():.1f}%")
        print(f"  Within 5%:      {(vsim['error_pct'] <= 5).mean()*100:.0f}%")
        print(f"  Within 10%:     {(vsim['error_pct'] <= 10).mean()*100:.0f}%")
        print(f"  Within 15%:     {(vsim['error_pct'] <= 15).mean()*100:.0f}%")
        print(f"  Within 20%:     {(vsim['error_pct'] <= 20).mean()*100:.0f}%")
        print(f"  90% CI cover:   {vsim['in_ci'].mean()*100:.0f}%")
        print(f"  Max error:      {vsim['error_pct'].max():.1f}%")
        worst = vsim.nlargest(5, "error_pct")[["bag_id", "quantity", "actual_price", "predicted_price", "error_pct"]]
        print(f"  Worst 5:\n{worst.to_string(index=False)}")

    return sim_df


if __name__ == "__main__":
    results = train_models()
    if results:
        simulate_accuracy(results)
