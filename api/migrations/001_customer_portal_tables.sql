-- Customer Portal Tables
-- Migration: 001_customer_portal_tables
-- Creates tables for lead capture and customer quotes

-- ── customer_leads ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customer_leads (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at      TIMESTAMPTZ DEFAULT now(),
    full_name       TEXT NOT NULL,
    business_name   TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT NOT NULL,
    annual_spend    TEXT NOT NULL,
    session_id      TEXT,
    slack_notified  BOOLEAN DEFAULT false
);

CREATE INDEX idx_customer_leads_email ON customer_leads (email);
CREATE INDEX idx_customer_leads_created_at ON customer_leads (created_at DESC);

-- ── customer_quotes ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customer_quotes (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at          TIMESTAMPTZ DEFAULT now(),
    lead_id             BIGINT NOT NULL REFERENCES customer_leads(id),
    specifications      JSONB NOT NULL,
    pricing_digital     JSONB,
    pricing_flexo       JSONB,
    pricing_intl_air    JSONB,
    pricing_intl_ocean  JSONB,
    selected_quantity   INTEGER,
    requested_manager   BOOLEAN DEFAULT false,
    artwork_uploaded    BOOLEAN DEFAULT false,
    artwork_url         TEXT,
    internal_vendors    JSONB,
    margin_applied      NUMERIC(5,2),
    slack_notified      BOOLEAN DEFAULT false
);

CREATE INDEX idx_customer_quotes_lead_id ON customer_quotes (lead_id);
CREATE INDEX idx_customer_quotes_created_at ON customer_quotes (created_at DESC);

-- ── Row Level Security ──────────────────────────────────────────────
ALTER TABLE customer_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_quotes ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (API backend uses service key)
CREATE POLICY "Service role full access on leads"
    ON customer_leads FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on quotes"
    ON customer_quotes FOR ALL
    USING (true)
    WITH CHECK (true);
