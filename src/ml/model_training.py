"""
ML Model Training Pipeline.

Trains separate models for Dazpak (flexographic) and Ross (digital):
  - GradientBoostingRegressor for point predictions
  - Quantile regression (10th/90th percentile) for confidence intervals
  - Cross-validated performance metrics
  - Feature importance extraction for cost-factor breakdown
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import (
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)

from config.settings import (
    MODEL_DIR, RANDOM_STATE, TEST_SIZE, CV_FOLDS,
    CONFIDENCE_LOWER, CONFIDENCE_UPPER,
)
from src.ml.feature_engineering import (
    prepare_features, build_preprocessor, get_feature_names,
    save_preprocessor,
)

logger = logging.getLogger(__name__)


class QuoteModelTrainer:
    """Trains and evaluates quote-prediction models per vendor."""

    def __init__(self, vendor: str, use_log_target: bool = False):
        """
        vendor: 'dazpak', 'ross', or 'internal'
        use_log_target: If True, train on log(price) for better fit on
                        data with wide price ranges (e.g., internal estimates)
        """
        self.vendor = vendor
        self.use_log_target = use_log_target
        self.preprocessor = build_preprocessor()
        self.model_point = None       # Main prediction model (squared error)
        self.model_lower = None       # 10th percentile
        self.model_upper = None       # 90th percentile
        self.metrics = {}
        self.feature_importances = {}
        self.feature_names = []

    def train(self, df: pd.DataFrame, target_col: str = "unit_price") -> dict:
        """
        Train models on the provided data.

        df: Must contain all spec columns + 'quantity' + target_col.
            Should already be filtered to this vendor.

        Returns dict of performance metrics.
        """
        logger.info(f"Training {self.vendor} model on {len(df)} samples "
                     f"(log_target={self.use_log_target})...")

        # Prepare features
        df = prepare_features(df)

        # Drop rows with missing target
        df = df.dropna(subset=[target_col])
        if len(df) < 10:
            logger.warning(f"Only {len(df)} samples for {self.vendor} — model may be unreliable")

        X = df.drop(columns=[target_col, "unit_price", "total_price",
                             "price_per_m_imps", "price_per_msi",
                             "price_per_ea_imp", "tolerance_pct",
                             "adder_per_m_imps", "adder_per_msi",
                             "adder_per_ea_imp"],
                    errors="ignore")
        y_raw = df[target_col].values

        # Log-transform target if configured
        if self.use_log_target:
            y = np.log(np.clip(y_raw, 1e-6, None))
        else:
            y = y_raw

        # Fit preprocessor and transform
        self.preprocessor.fit(X)
        X_transformed = self.preprocessor.transform(X)
        self.feature_names = get_feature_names(self.preprocessor)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_transformed, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
        )
        # Keep raw y_test for evaluation in original scale
        if self.use_log_target:
            _, _, y_raw_train, y_raw_test = train_test_split(
                X_transformed, y_raw, test_size=TEST_SIZE, random_state=RANDOM_STATE
            )

        # ── Point prediction model ─────────────────────────────────
        # Tuned for internal vendor's smaller dataset (498 rows):
        # more estimators + lower learning rate = better generalization
        n_est = 500 if self.vendor == "internal" else 300
        depth = 6 if self.vendor == "internal" else 5
        lr = 0.03 if self.vendor == "internal" else 0.05
        min_leaf = 3 if self.vendor == "internal" else 5

        self.model_point = GradientBoostingRegressor(
            n_estimators=n_est,
            max_depth=depth,
            learning_rate=lr,
            subsample=0.8,
            min_samples_leaf=min_leaf,
            loss="squared_error",
            random_state=RANDOM_STATE,
        )
        self.model_point.fit(X_train, y_train)

        # ── Confidence interval models (quantile regression) ───────
        self.model_lower = GradientBoostingRegressor(
            n_estimators=min(n_est, 300),
            max_depth=min(depth, 4),
            learning_rate=lr,
            subsample=0.8,
            min_samples_leaf=min_leaf,
            loss="quantile",
            alpha=CONFIDENCE_LOWER,
            random_state=RANDOM_STATE,
        )
        self.model_lower.fit(X_train, y_train)

        self.model_upper = GradientBoostingRegressor(
            n_estimators=min(n_est, 300),
            max_depth=min(depth, 4),
            learning_rate=lr,
            subsample=0.8,
            min_samples_leaf=min_leaf,
            loss="quantile",
            alpha=CONFIDENCE_UPPER,
            random_state=RANDOM_STATE,
        )
        self.model_upper.fit(X_train, y_train)

        # ── Evaluate ───────────────────────────────────────────────
        y_pred_raw = self.model_point.predict(X_test)
        y_pred_lower_raw = self.model_lower.predict(X_test)
        y_pred_upper_raw = self.model_upper.predict(X_test)

        # Back-transform if using log target
        if self.use_log_target:
            y_pred = np.exp(y_pred_raw)
            y_pred_lower = np.exp(y_pred_lower_raw)
            y_pred_upper = np.exp(y_pred_upper_raw)
            y_eval = y_raw_test  # Compare against original scale
        else:
            y_pred = y_pred_raw
            y_pred_lower = y_pred_lower_raw
            y_pred_upper = y_pred_upper_raw
            y_eval = y_test

        # Metrics (always in original price scale)
        self.metrics = {
            "n_train": len(X_train),
            "n_test": len(X_test),
            "mape": float(mean_absolute_percentage_error(y_eval, y_pred) * 100),
            "rmse": float(np.sqrt(mean_squared_error(y_eval, y_pred))),
            "r2": float(r2_score(y_eval, y_pred)),
            "coverage_90": float(
                np.mean((y_eval >= y_pred_lower) & (y_eval <= y_pred_upper)) * 100
            ),
            "use_log_target": self.use_log_target,
        }

        # Cross-validation on full data (in transformed space)
        cv_scores = cross_val_score(
            self.model_point, X_transformed, y,
            cv=min(CV_FOLDS, len(df) // 2),
            scoring="neg_mean_absolute_percentage_error",
        )
        self.metrics["cv_mape_mean"] = float(-cv_scores.mean() * 100)
        self.metrics["cv_mape_std"] = float(cv_scores.std() * 100)
        if self.use_log_target:
            self.metrics["cv_note"] = "CV MAPE is in log-space; actual MAPE reported above is in original scale"

        # Feature importances
        importances = self.model_point.feature_importances_
        self.feature_importances = {
            name: float(imp)
            for name, imp in sorted(
                zip(self.feature_names, importances),
                key=lambda x: x[1], reverse=True,
            )
        }

        logger.info(
            f"{self.vendor} model: MAPE={self.metrics['mape']:.1f}%, "
            f"R²={self.metrics['r2']:.3f}, "
            f"90% CI coverage={self.metrics['coverage_90']:.1f}%"
        )
        return self.metrics

    def save(self, suffix: str = ""):
        """Save all model artifacts to MODEL_DIR."""
        tag = f"{self.vendor}{suffix}"
        model_dir = Path(MODEL_DIR)
        model_dir.mkdir(exist_ok=True)

        joblib.dump(self.model_point, model_dir / f"{tag}_point.joblib")
        joblib.dump(self.model_lower, model_dir / f"{tag}_lower.joblib")
        joblib.dump(self.model_upper, model_dir / f"{tag}_upper.joblib")
        save_preprocessor(self.preprocessor, model_dir / f"{tag}_preprocessor.joblib")
        joblib.dump(self.feature_names, model_dir / f"{tag}_features.joblib")
        joblib.dump(self.metrics, model_dir / f"{tag}_metrics.joblib")
        joblib.dump(self.feature_importances, model_dir / f"{tag}_importances.joblib")
        joblib.dump(self.use_log_target, model_dir / f"{tag}_log_target.joblib")

        logger.info(f"Saved {self.vendor} models to {model_dir}")

    @classmethod
    def load(cls, vendor: str, suffix: str = "") -> "QuoteModelTrainer":
        """Load a trained model from disk."""
        tag = f"{vendor}{suffix}"
        model_dir = Path(MODEL_DIR)

        # Check if log_target flag exists
        log_target_path = model_dir / f"{tag}_log_target.joblib"
        use_log = joblib.load(log_target_path) if log_target_path.exists() else False

        trainer = cls(vendor, use_log_target=use_log)
        trainer.model_point = joblib.load(model_dir / f"{tag}_point.joblib")
        trainer.model_lower = joblib.load(model_dir / f"{tag}_lower.joblib")
        trainer.model_upper = joblib.load(model_dir / f"{tag}_upper.joblib")
        trainer.preprocessor = joblib.load(model_dir / f"{tag}_preprocessor.joblib")
        trainer.feature_names = joblib.load(model_dir / f"{tag}_features.joblib")
        trainer.metrics = joblib.load(model_dir / f"{tag}_metrics.joblib")
        trainer.feature_importances = joblib.load(model_dir / f"{tag}_importances.joblib")

        logger.info(f"Loaded {vendor} model (MAPE={trainer.metrics.get('mape', '?')}%, log_target={use_log})")
        return trainer


def train_all_models(training_df: pd.DataFrame) -> dict:
    """
    Train models for both vendors from a combined training DataFrame.
    Returns dict with metrics per vendor.
    """
    results = {}

    for vendor in ["dazpak", "ross", "internal"]:
        vendor_df = training_df[training_df["vendor"] == vendor].copy()
        if len(vendor_df) == 0:
            logger.warning(f"No data for {vendor} — skipping")
            continue

        # Internal model uses log-target for better fit across wide qty range
        use_log = (vendor == "internal")
        trainer = QuoteModelTrainer(vendor, use_log_target=use_log)
        metrics = trainer.train(vendor_df)
        trainer.save()
        results[vendor] = metrics

    return results
