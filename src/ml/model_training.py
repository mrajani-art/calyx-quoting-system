"""
ML Model Training Pipeline.

Trains separate models for Dazpak (flexographic), Ross (digital), and Internal (HP 6900):
  - GradientBoostingRegressor for point predictions
  - Quantile regression (10th/90th percentile) for confidence intervals
  - Cross-validated performance metrics
  - Feature importance extraction for cost-factor breakdown
  - Recency weighting: quotes from the last 90 days get 3× training weight
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import (
    cross_val_score, train_test_split, GroupShuffleSplit,
)
from sklearn.metrics import (
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
    make_scorer,
)

from config.settings import (
    MODEL_DIR, RANDOM_STATE, TEST_SIZE, CV_FOLDS,
    CONFIDENCE_LOWER, CONFIDENCE_UPPER,
    RECENCY_RECENT_DAYS, RECENCY_RECENT_WEIGHT,
    RECENCY_DECAY_HALF_LIFE, RECENCY_MIN_WEIGHT,
)

# Tedpack settings may not exist in older settings.py
try:
    from config.settings import TEDPACK_CONFIDENCE_LOWER, TEDPACK_CONFIDENCE_UPPER
except ImportError:
    TEDPACK_CONFIDENCE_LOWER = 0.05
    TEDPACK_CONFIDENCE_UPPER = 0.95

try:
    from config.settings import TEDPACK_OUTLIER_SIGMA
except ImportError:
    TEDPACK_OUTLIER_SIGMA = 2.5
from src.ml.feature_engineering import (
    prepare_features, build_preprocessor, get_feature_names,
    save_preprocessor,
)
from src.ml.recency_weights import compute_recency_weights_from_df

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
        self.is_ratio_model = False
        self.preprocessor = build_preprocessor(vendor=vendor)
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

        # ── Compute recency weights BEFORE prepare_features ──────────
        # Prefer quote_date (actual date the vendor quoted) over created_at
        # (date we ingested it). Falls back to created_at if quote_date missing.
        date_col = "quote_date"
        if date_col not in df.columns or df[date_col].isna().all():
            date_col = "created_at"
        sample_weights = compute_recency_weights_from_df(
            df,
            date_column=date_col,
            recent_days=RECENCY_RECENT_DAYS,
            recent_weight=RECENCY_RECENT_WEIGHT,
            decay_half_life=RECENCY_DECAY_HALF_LIFE,
            min_weight=RECENCY_MIN_WEIGHT,
        )

        # ── Preserve FL numbers for group-based splitting ────────────
        # All quantity tiers for the same FL number must stay in the same
        # split — otherwise the model "cheats" by seeing the same bag's
        # cost at 5K in training and predicting it at 25K in test.
        if "fl_number" in df.columns:
            fallback = "no_fl_" + df.index.astype(str)
            groups = df["fl_number"].where(df["fl_number"].notna(), fallback)
        else:
            groups = pd.Series("no_fl_" + df.index.astype(str), index=df.index)

        # Prepare features
        df = prepare_features(df)

        # ── Ratio model setup for tedpack_ocean ──────────────────────
        # Must be set before outlier filters so they can adapt behavior
        if self.vendor == "tedpack_ocean" and target_col == "ocean_air_ratio":
            self.is_ratio_model = True
            self.use_log_target = False  # ratio is bounded (0.3–0.9), no log needed

        # Drop rows with missing target
        valid_mask = df[target_col].notna()
        df = df[valid_mask]
        sample_weights = sample_weights[valid_mask.values]
        groups = groups[valid_mask]

        # ── Outlier removal: drop extreme prices ──────────────────
        prices = df[target_col].values
        if len(prices) > 20:
            sigma_threshold = (TEDPACK_OUTLIER_SIGMA
                               if self.vendor.startswith("tedpack")
                               else 3.0)
            log_prices = np.log(np.clip(prices, 1e-6, None))
            mu, sigma = log_prices.mean(), log_prices.std()
            if sigma > 0:
                z_scores = np.abs((log_prices - mu) / sigma)
                inlier_mask = z_scores <= sigma_threshold
                n_outliers = (~inlier_mask).sum()
                if n_outliers > 0:
                    logger.info(f"  Removed {n_outliers} price outliers "
                                f"(>{sigma_threshold}σ in log-space) for {self.vendor}")
                    df = df[inlier_mask]
                    sample_weights = sample_weights[inlier_mask]
                    groups = groups[inlier_mask]

        # ── TedPack secondary filter: price-per-sqin IQR ────────
        # Skip for ratio models — ratio is not a price, dividing by area is meaningless
        if self.vendor.startswith("tedpack") and not self.is_ratio_model and len(df) > 20:
            if "width" in df.columns and "height" in df.columns:
                area = (df["width"] * df["height"]).clip(lower=1)
                psi = df[target_col] / area
                q1, q3 = psi.quantile(0.25), psi.quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    psi_mask = (psi >= q1 - 2.5 * iqr) & (psi <= q3 + 2.5 * iqr)
                    n_psi_outliers = (~psi_mask).sum()
                    if n_psi_outliers > 0:
                        logger.info(f"  Removed {n_psi_outliers} price-per-sqin outliers "
                                    f"(IQR method) for {self.vendor}")
                        df = df[psi_mask]
                        sample_weights = sample_weights[psi_mask.values]
                        groups = groups[psi_mask]

        if len(df) < 10:
            logger.warning(f"Only {len(df)} samples for {self.vendor} — model may be unreliable")

        # Preserve air prices and actual ocean prices for ratio→price back-conversion
        if self.is_ratio_model:
            _air_prices = df["ddp_air_price"].values.copy() if "ddp_air_price" in df.columns else None
            _actual_ocean_prices = df["unit_price"].values.copy()
        else:
            _air_prices = None

        X = df.drop(columns=[target_col, "unit_price", "total_price",
                             "price_per_m_imps", "price_per_msi",
                             "price_per_ea_imp", "tolerance_pct",
                             "adder_per_m_imps", "adder_per_msi",
                             "adder_per_ea_imp",
                             "ocean_air_ratio", "ddp_air_price"],
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

        # ── Group-based train/test split ─────────────────────────────
        # All tiers for the same FL number stay together — prevents
        # data leakage from the model seeing the same bag in both sets.
        n_unique_groups = groups.nunique()
        if n_unique_groups >= 5:
            gss = GroupShuffleSplit(
                n_splits=1, test_size=TEST_SIZE, random_state=RANDOM_STATE
            )
            train_idx, test_idx = next(gss.split(X_transformed, y, groups=groups.values))
            X_train, X_test = X_transformed[train_idx], X_transformed[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            w_train, w_test = sample_weights[train_idx], sample_weights[test_idx]
            if self.use_log_target:
                y_raw_test = y_raw[test_idx]
            if self.is_ratio_model and _air_prices is not None:
                _air_prices_test = _air_prices[test_idx]
                _actual_ocean_test = _actual_ocean_prices[test_idx]
        else:
            # Too few groups for group split — fall back to random
            logger.warning(f"  Only {n_unique_groups} unique FL groups — using random split")
            X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
                X_transformed, y, sample_weights,
                test_size=TEST_SIZE, random_state=RANDOM_STATE
            )
            if self.use_log_target:
                _, _, _, y_raw_test, _, _ = train_test_split(
                    X_transformed, y_raw, sample_weights,
                    test_size=TEST_SIZE, random_state=RANDOM_STATE
                )
            if self.is_ratio_model and _air_prices is not None:
                _, _air_prices_test = train_test_split(
                    _air_prices, test_size=TEST_SIZE, random_state=RANDOM_STATE
                )
                _, _actual_ocean_test = train_test_split(
                    _actual_ocean_prices, test_size=TEST_SIZE, random_state=RANDOM_STATE
                )

        # ── Point prediction model ─────────────────────────────────
        if self.vendor == "internal":
            n_est, depth, lr, min_leaf = 500, 6, 0.03, 3
        elif self.vendor == "ross":
            # Grid search winner (320 combos × 5 splits):
            # depth=3/200 → 13.5% ± 0.7% (lowest variance, tied best MAPE)
            n_est, depth, lr, min_leaf = 200, 3, 0.05, 8
        elif self.vendor == "tedpack_air":
            # Grid search winner (256 combos × 5 splits):
            # depth=2/200/lr=0.03 → 14.5% ± 2.3% (best mean for 52-bag dataset)
            n_est, depth, lr, min_leaf = 200, 2, 0.03, 12
        elif self.vendor == "tedpack_ocean":
            # Ratio-based model: predicts ocean/air ratio (~0.3–0.9)
            # More estimators + larger leaves for stable ratio predictions
            n_est, depth, lr, min_leaf = 200, 2, 0.03, 10
        else:  # dazpak
            n_est, depth, lr, min_leaf = 400, 5, 0.03, 4

        # Huber loss for all vendors — robust to remaining outliers
        self.model_point = GradientBoostingRegressor(
            n_estimators=n_est,
            max_depth=depth,
            learning_rate=lr,
            subsample=0.8,
            min_samples_leaf=min_leaf,
            loss="huber",
            random_state=RANDOM_STATE,
        )
        self.model_point.fit(X_train, y_train, sample_weight=w_train)

        # ── Confidence interval models (quantile regression) ───────
        # Dazpak gets wider bounds (5th/95th) due to small dataset
        if self.vendor.startswith("tedpack"):
            ci_lower_alpha = TEDPACK_CONFIDENCE_LOWER
            ci_upper_alpha = TEDPACK_CONFIDENCE_UPPER
        elif self.vendor == "dazpak":
            ci_lower_alpha = 0.05
            ci_upper_alpha = 0.95
        else:
            ci_lower_alpha = CONFIDENCE_LOWER
            ci_upper_alpha = CONFIDENCE_UPPER

        # Simpler CI models to avoid overfitting — fewer estimators, shallower
        ci_n_est = min(n_est, 250)
        ci_depth = min(depth, 3)

        self.model_lower = GradientBoostingRegressor(
            n_estimators=ci_n_est,
            max_depth=ci_depth,
            learning_rate=lr,
            subsample=0.8,
            min_samples_leaf=min_leaf,
            loss="quantile",
            alpha=ci_lower_alpha,
            random_state=RANDOM_STATE,
        )
        self.model_lower.fit(X_train, y_train, sample_weight=w_train)

        self.model_upper = GradientBoostingRegressor(
            n_estimators=ci_n_est,
            max_depth=ci_depth,
            learning_rate=lr,
            subsample=0.8,
            min_samples_leaf=min_leaf,
            loss="quantile",
            alpha=ci_upper_alpha,
            random_state=RANDOM_STATE,
        )
        self.model_upper.fit(X_train, y_train, sample_weight=w_train)

        # ── Evaluate ───────────────────────────────────────────────
        y_pred_raw = self.model_point.predict(X_test)
        y_pred_lower_raw = self.model_lower.predict(X_test)
        y_pred_upper_raw = self.model_upper.predict(X_test)

        # Back-transform if using log target
        if self.use_log_target:
            y_pred = np.exp(y_pred_raw)
            y_pred_lower = np.exp(y_pred_lower_raw)
            y_pred_upper = np.exp(y_pred_upper_raw)
            y_eval = y_raw_test
        else:
            y_pred = y_pred_raw
            y_pred_lower = y_pred_lower_raw
            y_pred_upper = y_pred_upper_raw
            y_eval = y_test

        # ── Convert ratio predictions to absolute prices for metrics ──
        # For ratio models, report metrics in absolute price scale so they
        # are comparable with the old baseline (direct price prediction).
        if self.is_ratio_model and _air_prices is not None:
            # ratio predictions → absolute ocean price = ratio * air_price
            y_pred_abs = y_pred * _air_prices_test
            y_pred_lower_abs = y_pred_lower * _air_prices_test
            y_pred_upper_abs = y_pred_upper * _air_prices_test
            y_eval_abs = _actual_ocean_test
            # Also store ratio-level metrics for diagnostics
            ratio_mape = float(mean_absolute_percentage_error(y_eval, y_pred) * 100)
            ratio_rmse = float(np.sqrt(mean_squared_error(y_eval, y_pred)))
            ratio_r2 = float(r2_score(y_eval, y_pred))
        else:
            y_pred_abs = y_pred
            y_pred_lower_abs = y_pred_lower
            y_pred_upper_abs = y_pred_upper
            y_eval_abs = y_eval

        # Metrics (always in original price scale for comparability)
        self.metrics = {
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_groups_train": int(groups.iloc[train_idx].nunique()) if n_unique_groups >= 5 else "N/A",
            "n_groups_test": int(groups.iloc[test_idx].nunique()) if n_unique_groups >= 5 else "N/A",
            "group_split": n_unique_groups >= 5,
            "mape": float(mean_absolute_percentage_error(y_eval_abs, y_pred_abs) * 100),
            "rmse": float(np.sqrt(mean_squared_error(y_eval_abs, y_pred_abs))),
            "r2": float(r2_score(y_eval_abs, y_pred_abs)),
            "coverage_90": float(
                np.mean((y_eval_abs >= y_pred_lower_abs) & (y_eval_abs <= y_pred_upper_abs)) * 100
            ),
            "ci_bounds": f"{ci_lower_alpha:.0%}/{ci_upper_alpha:.0%}",
            "use_log_target": self.use_log_target,
            "is_ratio_model": self.is_ratio_model,
            "recency_weighting": True,
            "recency_date_column": date_col,
            "recency_recent_days": RECENCY_RECENT_DAYS,
            "recency_recent_weight": RECENCY_RECENT_WEIGHT,
            "n_recent_train": int((w_train >= RECENCY_RECENT_WEIGHT * 0.99).sum()),
        }

        # Add ratio-level diagnostics for ratio models
        if self.is_ratio_model and _air_prices is not None:
            self.metrics["ratio_mape"] = ratio_mape
            self.metrics["ratio_rmse"] = ratio_rmse
            self.metrics["ratio_r2"] = ratio_r2

        # ── Cross-validation ───────────────────────────────────────
        # For log-target models, use a custom scorer that back-transforms
        # predictions before computing MAPE — avoids the meaningless
        # "MAPE on log values" problem.
        n_cv = min(CV_FOLDS, n_unique_groups // 2) if n_unique_groups >= 5 else min(CV_FOLDS, len(df) // 2)
        n_cv = max(n_cv, 2)

        if self.use_log_target:
            def _mape_log_scorer(estimator, X_cv, y_cv):
                """Score in original price scale for log-target models."""
                y_pred_log = estimator.predict(X_cv)
                y_pred_orig = np.exp(y_pred_log)
                y_orig = np.exp(y_cv)
                return -mean_absolute_percentage_error(y_orig, y_pred_orig)

            cv_scores = cross_val_score(
                self.model_point, X_transformed, y,
                cv=n_cv, scoring=_mape_log_scorer,
            )
        else:
            cv_scores = cross_val_score(
                self.model_point, X_transformed, y,
                cv=n_cv, scoring="neg_mean_absolute_percentage_error",
            )
        self.metrics["cv_mape_mean"] = float(-cv_scores.mean() * 100)
        self.metrics["cv_mape_std"] = float(cv_scores.std() * 100)

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
            f"CI coverage={self.metrics['coverage_90']:.1f}% "
            f"(group_split={self.metrics['group_split']})"
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
        joblib.dump(self.is_ratio_model, model_dir / f"{tag}_is_ratio_model.joblib")

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

        # Load ratio model flag (backwards-compatible: defaults to False for old models)
        ratio_flag_path = model_dir / f"{tag}_is_ratio_model.joblib"
        trainer.is_ratio_model = joblib.load(ratio_flag_path) if ratio_flag_path.exists() else False

        logger.info(f"Loaded {vendor} model (MAPE={trainer.metrics.get('mape', '?')}%, log_target={use_log}, ratio_model={trainer.is_ratio_model})")
        return trainer


def train_all_models(training_df: pd.DataFrame) -> dict:
    """
    Train models for both vendors from a combined training DataFrame.
    Returns dict with metrics per vendor.
    """
    results = {}

    for vendor in ["dazpak", "ross", "tedpack_air", "tedpack_ocean"]:
        vendor_df = training_df[training_df["vendor"] == vendor].copy()
        if len(vendor_df) == 0:
            logger.warning(f"No data for {vendor} — skipping")
            continue

        # All vendors use log-target except tedpack_ocean (ratio target is bounded 0.3–0.9)
        use_log = vendor in ("internal", "ross", "dazpak", "tedpack_air")
        target_col = "ocean_air_ratio" if vendor == "tedpack_ocean" else "unit_price"
        trainer = QuoteModelTrainer(vendor, use_log_target=use_log)
        metrics = trainer.train(vendor_df, target_col=target_col)
        trainer.save()
        results[vendor] = metrics

    return results
