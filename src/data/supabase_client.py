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
    vendor          TEXT NOT NULL CHECK (vendor IN ('dazpak','ross','internal')),
    print_method    TEXT NOT NULL CHECK (print_method IN ('digital','flexographic')),
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
    adder_per_ea_imp   NUMERIC(10,4)
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


def fetch_training_data() -> pd.DataFrame:
    """Fetch all quotes + prices as a flat DataFrame for ML training."""
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
                rows.append(row)
        return pd.DataFrame(rows)
    except Exception as e:
        logger.error(f"Fetch training data failed: {e}")
        return pd.DataFrame()


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
