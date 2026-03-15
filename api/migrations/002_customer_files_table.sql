-- Migration 002: Customer files table for artwork uploads
-- Tracks files uploaded via the contact request modal, stored in Supabase Storage.

CREATE TABLE IF NOT EXISTS customer_files (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at      TIMESTAMPTZ DEFAULT now(),
    lead_id         UUID NOT NULL REFERENCES customer_leads(id),
    quote_id        UUID REFERENCES customer_quotes(id),
    file_name       TEXT NOT NULL,
    file_type       TEXT NOT NULL,
    file_size       INTEGER NOT NULL,
    storage_path    TEXT NOT NULL,
    public_url      TEXT NOT NULL
);

CREATE INDEX idx_customer_files_lead_id ON customer_files (lead_id);
CREATE INDEX idx_customer_files_created_at ON customer_files (created_at DESC);

ALTER TABLE customer_files ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on files"
    ON customer_files FOR ALL
    USING (true)
    WITH CHECK (true);
