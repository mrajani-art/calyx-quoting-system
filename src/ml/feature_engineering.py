"""
Feature engineering for the packaging quote ML models.

Transforms raw quote specifications into numeric feature vectors
suitable for gradient boosting models.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import OrdinalEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib

logger = logging.getLogger(__name__)


# ── Feature Definitions ────────────────────────────────────────────
# These match the actual spreadsheet + PDF data fields.

NUMERIC_FEATURES = [
    "width",           # inches
    "height",          # inches
    "gusset",          # inches (0 if none)
    "print_width",     # calculated: height × 2 + gusset
    "bag_area_sqin",   # calculated: width × height
    "quantity",        # order quantity for this tier
    "log_quantity",    # log10(quantity) — captures volume discount curve
    "inv_quantity",    # 1/quantity — captures fixed-cost amortization
]

CATEGORICAL_FEATURES = [
    "substrate",
    "finish",
    "fill_style",
    "seal_type",
    "gusset_type",
    "zipper",
    "tear_notch",
    "hole_punch",
    "corner_treatment",
    "embellishment",
]

# Ordinal encoding order (from least to most "complex/expensive")
CATEGORY_ORDERS = {
    "substrate": ["CLR_PET", "MET_PET", "WHT_MET_PET", "HB_CLR_PET", "CUSTOM"],
    "finish": ["None", "Matte Laminate", "Gloss Laminate", "Soft Touch Laminate", "Holographic"],
    "fill_style": ["Top", "Bottom"],
    "seal_type": ["Stand Up", "2 Side Seal", "3 Side Seal", "3 Side Top Fill"],
    "gusset_type": ["None", "K Seal", "K Seal & Skirt Seal", "Plow Bottom", "Flat Bottom / Side Gusset"],
    "zipper": ["No Zipper", "Single Profile Non-CR", "Double Profile Non-CR",
               "Standard CR", "CR Zipper", "Presto CR Zipper"],
    "tear_notch": ["None", "Standard", "Double (2)"],
    "hole_punch": ["None", "Standard", "Round (Butterfly)", "Euro Slot", "Sombrero"],
    "corner_treatment": ["Straight", "Rounded"],
    "embellishment": ["None", "Hot Stamp (Gold)", "Hot Stamp (Silver)", "Embossing", "Spot UV"],
}


def normalize_substrate(val: str) -> str:
    """Map raw substrate names to canonical keys."""
    if not isinstance(val, str):
        return "CUSTOM"
    v = val.strip().upper().replace(' ', '_')
    if 'HB' in v or 'HIGH_BARRIER' in v:
        return "HB_CLR_PET"
    if 'WHT' in v or 'WHITE' in v:
        return "WHT_MET_PET"
    if 'CLR' in v or 'CLEAR' in v:
        return "CLR_PET"
    if 'MET' in v:
        return "MET_PET"
    return "CUSTOM"


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw quote data into ML-ready features.

    Input df must have columns: width, height, gusset, quantity,
    plus the categorical spec columns.
    """
    df = df.copy()

    # ── Computed numeric features ───────────────────────────────────
    df["gusset"] = pd.to_numeric(df.get("gusset", 0), errors="coerce").fillna(0)
    df["width"] = pd.to_numeric(df["width"], errors="coerce")
    df["height"] = pd.to_numeric(df["height"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

    df["print_width"] = df["height"] * 2 + df["gusset"]
    df["bag_area_sqin"] = df["width"] * df["height"]
    df["log_quantity"] = np.log10(df["quantity"].clip(lower=1))
    df["inv_quantity"] = 1.0 / df["quantity"].clip(lower=1)  # Fixed-cost amortization

    # ── Normalize substrate to canonical ────────────────────────────
    if "substrate" in df.columns:
        df["substrate"] = df["substrate"].apply(normalize_substrate)

    # ── Fill missing categoricals with safe defaults ────────────────
    defaults = {
        "substrate": "CUSTOM",
        "finish": "None",
        "fill_style": "Top",
        "seal_type": "Stand Up",
        "gusset_type": "None",
        "zipper": "No Zipper",
        "tear_notch": "None",
        "hole_punch": "None",
        "corner_treatment": "Straight",
        "embellishment": "None",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default)

    # ── Interaction features ────────────────────────────────────────
    # Area × quantity — captures how material cost scales
    df["area_x_logqty"] = df["bag_area_sqin"] * df["log_quantity"]

    # Gusset presence (binary) — simplifies gusset impact
    df["has_gusset"] = (df["gusset"] > 0).astype(int)

    # Zipper complexity score (0-3)
    zipper_score = {"No Zipper": 0, "Single Profile Non-CR": 1,
                    "Double Profile Non-CR": 1.5, "Standard CR": 2,
                    "CR Zipper": 3, "Presto CR Zipper": 3.5}
    df["zipper_score"] = df["zipper"].map(zipper_score).fillna(0)

    return df


def build_preprocessor() -> ColumnTransformer:
    """
    Build a sklearn ColumnTransformer that handles both numeric
    scaling and ordinal encoding of categoricals.
    """
    # Numeric pipeline: just scale
    numeric_pipe = Pipeline([
        ("scaler", StandardScaler()),
    ])

    # Categorical pipeline: ordinal encode (tree models handle ordinals well)
    cat_pipe = Pipeline([
        ("encoder", OrdinalEncoder(
            categories=[CATEGORY_ORDERS.get(f, ["unknown"]) for f in CATEGORICAL_FEATURES],
            handle_unknown="use_encoded_value",
            unknown_value=-1,
        )),
    ])

    all_numeric = NUMERIC_FEATURES + ["area_x_logqty", "has_gusset", "zipper_score"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, all_numeric),
            ("cat", cat_pipe, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return preprocessor


def get_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    """Get human-readable feature names after transformation."""
    all_numeric = NUMERIC_FEATURES + ["area_x_logqty", "has_gusset", "zipper_score"]
    return all_numeric + CATEGORICAL_FEATURES


def save_preprocessor(preprocessor: ColumnTransformer, path: str):
    """Persist fitted preprocessor."""
    joblib.dump(preprocessor, path)
    logger.info(f"Saved preprocessor to {path}")


def load_preprocessor(path: str) -> ColumnTransformer:
    """Load a fitted preprocessor."""
    return joblib.load(path)
