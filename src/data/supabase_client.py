"""
Supabase database client — schema + CRUD for the Calyx quoting system.

Schema is designed around the actual data observed in the Dazpak/Ross PDFs
and the Google Sheets quote-request tracker.
"""
import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


def get_client():
    """Lazy-initialize Supabase client."""
    from supabase import create_client
    from config.settings import SUPABASE_URL, SUPABASE_KEY
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise EnvironmentError("Set SUPABASE_URL and SUPABASE_KEY in .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Run this SQL in the Supabase SQL Editor ────────────────────────
SCHEMA_SQL = """
-- =================================================================
-- Calyx Containers ML Quoting System — Database Schema
-- =================================================================

-- Historical quotes ingested from PDFs and spreadsheet
CREATE TABLE IF NOT EXISTS quotes (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at      TIMESTAMPTZ DEFAULT now(),

    -- Source tracking
    vendor          TEXT NOT NULL CHECK (vendor IN ('dazpak','ross','internal','tedpack')),
    print_method    TEXT NOT NULL CHECK (print_method IN ('digital','flexographic','gravure')),
    fl_number       TEXT,                 -- e.g. FL-DL-1495, FL-CQ-0855
    quote_number    TEXT,                 -- Dazpak Quote # or Ross Estimate No.
    quote_date      DATE,
    source_type     TEXT CHECK (source_type IN ('spreadsheet','pdf','manual')),
    source_file     TEXT,

    -- Dimensions (inches)
    width           NUMERIC(8,3) NOT NULL,
    height          NUMERIC(8,3) NOT NULL,
    gusset          NUMERIC(8,3) DEFAULT 0,

    -- Calculated: print width for Ross routing rule (H × 2 + G)
    print_width     NUMERIC(8,3) GENERATED ALWAYS AS (height * 2 + gusset) STORED,
    -- Bag area for feature engineering
    bag_area_sqin   NUMERIC(10,3) GENERATED ALWAYS AS (width * height) STORED,

    -- Specifications (matching spreadsheet columns)
    substrate       TEXT,
    finish          TEXT,
    embellishment   TEXT DEFAULT 'None',
    fill_style      TEXT DEFAULT 'Top',
    seal_type       TEXT DEFAULT 'Stand Up',
    gusset_type     TEXT DEFAULT 'None',
    zipper          TEXT DEFAULT 'No Zipper',
    tear_notch      TEXT DEFAULT 'None',
    hole_punch      TEXT DEFAULT 'None',
    corner_treatment TEXT DEFAULT 'Straight',

    -- Dazpak-specific fields
    num_skus        INTEGER DEFAULT 1,
    num_colors      INTEGER,
    web_width       NUMERIC(8,4),        -- e.g. 13.0000
    repeat_length   NUMERIC(8,4),        -- e.g. 5.2500
    material_spec   TEXT,                -- Full material description

    -- Ross-specific fields
    account_no      TEXT,
    seal_width      TEXT,                -- e.g. ".3125 Seal"
    colors_spec     TEXT                 -- e.g. "CMYK"
);

-- Pricing tiers — one row per quote × quantity level
CREATE TABLE IF NOT EXISTS quote_prices (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    quote_id        UUID REFERENCES quotes(id) ON DELETE CASCADE,
    tier_index      SMALLINT NOT NULL,
    quantity        INTEGER NOT NULL,

    -- Universal pricing
    unit_price      NUMERIC(10,5) NOT NULL,      -- Price per unit/impression
    total_price     NUMERIC(12,2),

    -- Dazpak-specific pricing (from PDF columns)
    price_per_m_imps   NUMERIC(12,4),   -- Price / M Imps
    price_per_msi      NUMERIC(10,4),   -- Price / MSI
    price_per_ea_imp   NUMERIC(10,4),   -- Price / Ea Imp
    tolerance_pct      NUMERIC(5,2),    -- +/- % column
    -- Adder for each additional SKU
    adder_per_m_imps   NUMERIC(12,4),
    adder_per_msi      NUMERIC(10,4),
    adder_per_ea_imp   NUMERIC(10,4),

    -- TedPack-specific pricing (DDP = Delivered Duty Paid)
    ddp_air_price      NUMERIC(10,5),   -- DDP Air $/pc
    ddp_ocean_price    NUMERIC(10,5),   -- DDP Ocean $/pc
    fob_factory_price  NUMERIC(10,5)    -- FOB Factory $/pc
);

-- ML model registry
CREATE TABLE IF NOT EXISTS ml_models (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at          TIMESTAMPTZ DEFAULT now(),
    vendor              TEXT NOT NULL,
    model_type          TEXT NOT NULL,       -- 'gradient_boosting', 'random_forest', etc.
    target_col          TEXT NOT NULL,       -- 'unit_price'
    metrics             JSONB,              -- {mape, rmse, r2, cv_scores}
    feature_importances JSONB,
    model_path          TEXT NOT NULL,
    is_active           BOOLEAN DEFAULT true,
    UNIQUE (vendor, target_col, is_active)
);

-- Generated quotes (predictions)
CREATE TABLE IF NOT EXISTS generated_quotes (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at      TIMESTAMPTZ DEFAULT now(),
    requested_by    TEXT DEFAULT 'system',
    input_params    JSONB NOT NULL,
    vendor_routed   TEXT,
    predictions     JSONB,          -- {qty: {price, lower, upper}}
    confidence      JSONB,
    cost_factors    JSONB
);

-- Generated estimates (PDF output audit trail + data store)
CREATE TABLE IF NOT EXISTS estimates (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at          TIMESTAMPTZ DEFAULT now(),
    estimate_number     TEXT NOT NULL UNIQUE,
    customer_name       TEXT NOT NULL,
    calyx_rep           TEXT,

    -- Bag specs
    width               NUMERIC(8,3),
    height              NUMERIC(8,3),
    gusset              NUMERIC(8,3) DEFAULT 0,
    print_width         NUMERIC(8,3),
    substrate           TEXT,
    finish              TEXT,
    embellishment       TEXT DEFAULT 'None',
    fill_style          TEXT,
    seal_type           TEXT,
    gusset_type         TEXT,
    zipper              TEXT,
    tear_notch          TEXT,
    hole_punch          TEXT,
    corner_treatment    TEXT,
    print_method        TEXT,

    -- Routing
    vendor_routed       TEXT,
    margin_pct          INTEGER,

    -- Pricing tiers (JSONB array of {quantity, unit_cost, unit_sell, total_sell})
    pricing_tiers       JSONB NOT NULL,

    -- Component costs if deterministic (JSONB)
    component_costs     JSONB
);

CREATE INDEX IF NOT EXISTS idx_est_number ON estimates(estimate_number);
CREATE INDEX IF NOT EXISTS idx_est_customer ON estimates(customer_name);
CREATE INDEX IF NOT EXISTS idx_est_created ON estimates(created_at DESC);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_quotes_vendor ON quotes(vendor);
CREATE INDEX IF NOT EXISTS idx_quotes_fl ON quotes(fl_number);
CREATE INDEX IF NOT EXISTS idx_qp_quote ON quote_prices(quote_id);
CREATE INDEX IF NOT EXISTS idx_gen_created ON generated_quotes(created_at DESC);
"""


# ── CRUD Operations ────────────────────────────────────────────────

def insert_quote(quote_data: dict, prices: list[dict]) -> Optional[str]:
    """Insert a single historical quote with pricing tiers."""
    client = get_client()
    try:
        res = client.table("quotes").insert(quote_data).execute()
        quote_id = res.data[0]["id"]
        for p in prices:
            p["quote_id"] = quote_id
        if prices:
            client.table("quote_prices").insert(prices).execute()
        logger.info(f"Inserted quote {quote_id} ({quote_data.get('fl_number','')})")
        return quote_id
    except Exception as e:
        logger.error(f"Insert failed: {e}")
        return None


def _split_tedpack_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split vendor='tedpack' rows into tedpack_air and tedpack_ocean.

    The Supabase schema stores TedPack quotes with vendor='tedpack' and
    separate ddp_air_price / ddp_ocean_price columns in quote_prices.
    The ML training pipeline expects vendor='tedpack_air' and
    vendor='tedpack_ocean' as separate rows with unit_price set to the
    respective DDP price.

    Non-tedpack rows pass through unchanged.
    """
    if "vendor" not in df.columns:
        return df

    tedpack_mask = df["vendor"] == "tedpack"
    if not tedpack_mask.any():
        return df

    non_tedpack = df[~tedpack_mask].copy()
    tedpack = df[tedpack_mask].copy()

    split_rows = []

    # Convert DDP columns to numeric (they may arrive as strings from Supabase)
    for col in ("ddp_air_price", "ddp_ocean_price"):
        if col in tedpack.columns:
            tedpack[col] = pd.to_numeric(tedpack[col], errors="coerce")

    # Air rows: use ddp_air_price where available, else fall back to unit_price
    has_air = (
        "ddp_air_price" in tedpack.columns
        and tedpack["ddp_air_price"].notna().any()
    )
    if has_air:
        air_df = tedpack[tedpack["ddp_air_price"].notna()].copy()
        air_df["vendor"] = "tedpack_air"
        air_df["unit_price"] = air_df["ddp_air_price"]
        split_rows.append(air_df)
    else:
        # Fallback: if no DDP air prices, use unit_price for air
        air_df = tedpack.copy()
        air_df["vendor"] = "tedpack_air"
        split_rows.append(air_df)
        logger.warning("No ddp_air_price data — using unit_price as fallback for tedpack_air")

    # Ocean rows: use ddp_ocean_price where available
    has_ocean = (
        "ddp_ocean_price" in tedpack.columns
        and tedpack["ddp_ocean_price"].notna().any()
    )
    if has_ocean:
        ocean_df = tedpack[tedpack["ddp_ocean_price"].notna()].copy()
        ocean_df["vendor"] = "tedpack_ocean"
        ocean_df["unit_price"] = ocean_df["ddp_ocean_price"]
        split_rows.append(ocean_df)
    else:
        logger.warning("No ddp_ocean_price data — tedpack_ocean will have no training rows")

    result = pd.concat([non_tedpack] + split_rows, ignore_index=True)

    # Clean up DDP columns (no longer needed after split)
    for col in ("ddp_air_price", "ddp_ocean_price"):
        if col in result.columns:
            result = result.drop(columns=[col])

    tedpack_air_count = len(result[result["vendor"] == "tedpack_air"])
    tedpack_ocean_count = len(result[result["vendor"] == "tedpack_ocean"])
    logger.info(
        f"TedPack split: {tedpack_mask.sum()} tedpack rows → "
        f"{tedpack_air_count} tedpack_air + {tedpack_ocean_count} tedpack_ocean"
    )

    return result


def fetch_training_data() -> pd.DataFrame:
    """Fetch all quotes + prices as a flat DataFrame for ML training.

    Deduplication: When the same FL number has been ingested multiple
    times (e.g. revised estimates from different PDF emails), we keep
    only the most recent quote per (fl_number, width, height, gusset,
    quantity) combination. This prevents contradictory prices from
    old revisions from confusing the model.
    """
    client = get_client()
    try:
        res = client.table("quotes").select("*, quote_prices(*)").execute()
        if not res.data:
            return pd.DataFrame()
        rows = []
        for q in res.data:
            base = {k: v for k, v in q.items() if k != "quote_prices"}
            for p in q.get("quote_prices", []):
                row = {**base}
                row["quantity"] = p["quantity"]
                row["unit_price"] = p["unit_price"]
                row["tier_index"] = p.get("tier_index")
                row["price_per_m_imps"] = p.get("price_per_m_imps")
                row["price_per_msi"] = p.get("price_per_msi")
                row["tolerance_pct"] = p.get("tolerance_pct")
                row["ddp_air_price"] = p.get("ddp_air_price")
                row["ddp_ocean_price"] = p.get("ddp_ocean_price")
                rows.append(row)
        df = pd.DataFrame(rows)

        if df.empty:
            return df

        # ── Split TedPack rows into tedpack_air / tedpack_ocean ───
        df = _split_tedpack_rows(df)

        # ── Deduplication: keep latest revision per spec+qty ──────
        df = deduplicate_training_data(df)

        return df
    except Exception as e:
        logger.error(f"Fetch training data failed: {e}")
        return pd.DataFrame()


def deduplicate_training_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate price rows caused by re-ingestion of revised quotes.

    Two-pass deduplication:
    1. For rows WITH an fl_number: group by (fl_number, width, height,
       gusset, substrate, quantity) and keep only the most recent row.
       This preserves legitimate variants (same FL, different bag sizes
       or substrates) while removing true revision duplicates.
    2. Secondary pass: remove rows with identical (vendor, width, height,
       gusset, substrate, zipper, quantity, unit_price) — exact duplicates.
    """
    before_count = len(df)

    # Parse created_at for sorting
    if "created_at" in df.columns:
        df["_created_ts"] = pd.to_datetime(df["created_at"], errors="coerce")
    else:
        df["_created_ts"] = pd.NaT

    # Split: rows with FL numbers (can dedup) vs without (keep all)
    has_fl = df["fl_number"].notna() & (df["fl_number"].str.strip() != "")
    df_with_fl = df[has_fl].copy()
    df_no_fl = df[~has_fl].copy()

    if not df_with_fl.empty:
        # Normalize fl_number for grouping
        df_with_fl["_fl_norm"] = df_with_fl["fl_number"].str.strip().str.upper()

        # Pass 1: Same FL + same bag specs + same quantity = revision dupe
        # Include dimensions AND substrate to preserve legitimate variants
        dedup_cols = ["_fl_norm", "width", "height", "gusset", "substrate", "quantity"]
        available_dedup = [c for c in dedup_cols if c in df_with_fl.columns]

        df_with_fl = (
            df_with_fl
            .sort_values("_created_ts", ascending=False, na_position="last")
            .drop_duplicates(subset=available_dedup, keep="first")
        )
        df_with_fl = df_with_fl.drop(columns=["_fl_norm"])

    # Recombine
    df = pd.concat([df_with_fl, df_no_fl], ignore_index=True)
    df = df.drop(columns=["_created_ts"])

    # Pass 2: Remove exact duplicates (same specs + same price)
    exact_dedup_cols = ["vendor", "width", "height", "gusset", "substrate",
                        "zipper", "quantity", "unit_price"]
    available_cols = [c for c in exact_dedup_cols if c in df.columns]
    if available_cols:
        before_pass2 = len(df)
        df = df.drop_duplicates(subset=available_cols, keep="first")
        pass2_removed = before_pass2 - len(df)
    else:
        pass2_removed = 0

    after_count = len(df)
    if before_count != after_count:
        logger.info(
            f"Deduplication: {before_count} → {after_count} rows "
            f"({before_count - after_count} removed: "
            f"{before_count - after_count - pass2_removed} revision dupes, "
            f"{pass2_removed} exact dupes)"
        )

    return df


def save_model_metadata(vendor: str, model_type: str, target_col: str,
                        metrics: dict, feat_imp: dict, model_path: str):
    """Register a trained model in the database."""
    client = get_client()
    try:
        # Deactivate previous
        client.table("ml_models").update({"is_active": False}).match(
            {"vendor": vendor, "target_col": target_col, "is_active": True}
        ).execute()
        client.table("ml_models").insert({
            "vendor": vendor, "model_type": model_type,
            "target_col": target_col, "metrics": metrics,
            "feature_importances": feat_imp, "model_path": model_path,
            "is_active": True,
        }).execute()
    except Exception as e:
        logger.error(f"Save model metadata failed: {e}")


def save_generated_quote(input_params: dict, vendor: str,
                         predictions: dict, confidence: dict,
                         cost_factors: dict):
    """Persist a generated quote prediction."""
    client = get_client()
    try:
        client.table("generated_quotes").insert({
            "input_params": input_params,
            "vendor_routed": vendor,
            "predictions": predictions,
            "confidence": confidence,
            "cost_factors": cost_factors,
        }).execute()
    except Exception as e:
        logger.error(f"Save generated quote failed: {e}")


def fetch_recent_predictions(limit: int = 50) -> pd.DataFrame:
    """Get recent generated quotes for the analytics dashboard."""
    client = get_client()
    try:
        res = (client.table("generated_quotes")
               .select("*").order("created_at", desc=True)
               .limit(limit).execute())
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        logger.error(f"Fetch predictions failed: {e}")
        return pd.DataFrame()


def save_estimate(estimate_data: dict) -> Optional[str]:
    """
    Save a generated estimate to the estimates table.

    estimate_data should include:
        estimate_number, customer_name, calyx_rep,
        width, height, gusset, print_width,
        substrate, finish, embellishment, fill_style, seal_type,
        gusset_type, zipper, tear_notch, hole_punch, corner_treatment,
        print_method, vendor_routed, margin_pct,
        pricing_tiers (list of dicts), component_costs (optional)
    """
    client = get_client()
    try:
        # Convert lists/dicts to JSON-compatible format
        import json
        data = dict(estimate_data)
        if "pricing_tiers" in data and isinstance(data["pricing_tiers"], list):
            data["pricing_tiers"] = json.dumps(data["pricing_tiers"])
        if "component_costs" in data and isinstance(data["component_costs"], list):
            data["component_costs"] = json.dumps(data["component_costs"])

        res = client.table("estimates").insert(data).execute()
        est_id = res.data[0]["id"] if res.data else None
        logger.info(f"Saved estimate {data.get('estimate_number')} → {est_id}")
        return est_id
    except Exception as e:
        logger.error(f"Save estimate failed: {e}")
        return None
