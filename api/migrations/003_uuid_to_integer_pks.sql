-- Migration 003: Convert all 8 tables from UUID primary keys to BIGINT GENERATED ALWAYS AS IDENTITY
--
-- Customer portal tables (customer_leads, customer_quotes, customer_files) are
-- TRUNCATED because they hold ephemeral lead data that can be re-collected.
--
-- ML system tables (quotes, quote_prices, ml_models, generated_quotes, estimates)
-- are migrated in-place to preserve historical training/pricing data.

-- ============================================================================
-- PART 1: CUSTOMER PORTAL TABLES (clean slate — drop and recreate columns)
-- ============================================================================

-- 1a. Drop foreign keys
ALTER TABLE customer_files  DROP CONSTRAINT customer_files_lead_id_fkey;
ALTER TABLE customer_files  DROP CONSTRAINT customer_files_quote_id_fkey;
ALTER TABLE customer_quotes DROP CONSTRAINT customer_quotes_lead_id_fkey;

-- 1b. Drop indexes
DROP INDEX IF EXISTS idx_customer_quotes_lead_id;
DROP INDEX IF EXISTS idx_customer_files_lead_id;

-- 1c. Truncate before column type changes (UUID can't cast to BIGINT)
TRUNCATE customer_leads, customer_quotes, customer_files;

-- 1d. customer_leads: drop UUID id, add BIGINT id
ALTER TABLE customer_leads DROP CONSTRAINT customer_leads_pkey;
ALTER TABLE customer_leads DROP COLUMN id;
ALTER TABLE customer_leads ADD COLUMN id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

-- 1e. customer_quotes: drop UUID columns, add BIGINT columns
ALTER TABLE customer_quotes DROP CONSTRAINT customer_quotes_pkey;
ALTER TABLE customer_quotes DROP COLUMN id;
ALTER TABLE customer_quotes DROP COLUMN lead_id;
ALTER TABLE customer_quotes ADD COLUMN id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;
ALTER TABLE customer_quotes ADD COLUMN lead_id BIGINT NOT NULL;

-- 1f. customer_files: drop UUID columns, add BIGINT columns
ALTER TABLE customer_files DROP CONSTRAINT customer_files_pkey;
ALTER TABLE customer_files DROP COLUMN id;
ALTER TABLE customer_files DROP COLUMN lead_id;
ALTER TABLE customer_files DROP COLUMN quote_id;
ALTER TABLE customer_files ADD COLUMN id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;
ALTER TABLE customer_files ADD COLUMN lead_id BIGINT NOT NULL;
ALTER TABLE customer_files ADD COLUMN quote_id BIGINT;

-- 1g. Recreate foreign keys
ALTER TABLE customer_quotes
    ADD CONSTRAINT customer_quotes_lead_id_fkey
    FOREIGN KEY (lead_id) REFERENCES customer_leads(id);
ALTER TABLE customer_files
    ADD CONSTRAINT customer_files_lead_id_fkey
    FOREIGN KEY (lead_id) REFERENCES customer_leads(id);
ALTER TABLE customer_files
    ADD CONSTRAINT customer_files_quote_id_fkey
    FOREIGN KEY (quote_id) REFERENCES customer_quotes(id);

-- 1h. Recreate indexes
CREATE INDEX idx_customer_quotes_lead_id ON customer_quotes(lead_id);
CREATE INDEX idx_customer_files_lead_id  ON customer_files(lead_id);


-- ============================================================================
-- PART 2: ML SYSTEM TABLES — quotes + quote_prices (data-preserving)
-- ============================================================================

-- 2a. Drop FK and index
ALTER TABLE quote_prices DROP CONSTRAINT quote_prices_quote_id_fkey;
DROP INDEX IF EXISTS idx_qp_quote;

-- 2b. Add new BIGINT identity column to quotes
ALTER TABLE quotes ADD COLUMN new_id BIGINT GENERATED ALWAYS AS IDENTITY;

-- 2c. Map quote_prices to new IDs
ALTER TABLE quote_prices ADD COLUMN new_quote_id BIGINT;
UPDATE quote_prices qp
   SET new_quote_id = q.new_id
  FROM quotes q
 WHERE qp.quote_id = q.id;

-- 2d. Swap quotes PK
ALTER TABLE quotes DROP CONSTRAINT quotes_pkey;
ALTER TABLE quotes DROP COLUMN id;
ALTER TABLE quotes RENAME COLUMN new_id TO id;
ALTER TABLE quotes ADD PRIMARY KEY (id);

-- 2e. Swap quote_prices PK
ALTER TABLE quote_prices ADD COLUMN new_pk_id BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE quote_prices DROP CONSTRAINT quote_prices_pkey;
ALTER TABLE quote_prices DROP COLUMN id;
ALTER TABLE quote_prices RENAME COLUMN new_pk_id TO id;
ALTER TABLE quote_prices ADD PRIMARY KEY (id);

-- 2f. Swap quote_prices.quote_id
ALTER TABLE quote_prices DROP COLUMN quote_id;
ALTER TABLE quote_prices RENAME COLUMN new_quote_id TO quote_id;

-- 2g. Recreate FK and index
ALTER TABLE quote_prices
    ADD CONSTRAINT quote_prices_quote_id_fkey
    FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE;
CREATE INDEX idx_qp_quote ON quote_prices(quote_id);


-- ============================================================================
-- PART 3: ML SYSTEM TABLES — standalone (data-preserving)
-- ============================================================================

-- 3a. ml_models (UNIQUE constraint on vendor/target_col/is_active survives)
ALTER TABLE ml_models ADD COLUMN new_id BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE ml_models DROP CONSTRAINT ml_models_pkey;
ALTER TABLE ml_models DROP COLUMN id;
ALTER TABLE ml_models RENAME COLUMN new_id TO id;
ALTER TABLE ml_models ADD PRIMARY KEY (id);

-- 3b. generated_quotes
ALTER TABLE generated_quotes ADD COLUMN new_id BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE generated_quotes DROP CONSTRAINT generated_quotes_pkey;
ALTER TABLE generated_quotes DROP COLUMN id;
ALTER TABLE generated_quotes RENAME COLUMN new_id TO id;
ALTER TABLE generated_quotes ADD PRIMARY KEY (id);

-- 3c. estimates
ALTER TABLE estimates ADD COLUMN new_id BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE estimates DROP CONSTRAINT estimates_pkey;
ALTER TABLE estimates DROP COLUMN id;
ALTER TABLE estimates RENAME COLUMN new_id TO id;
ALTER TABLE estimates ADD PRIMARY KEY (id);


-- ============================================================================
-- PART 4: Recreate indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_quotes_vendor ON quotes(vendor);
CREATE INDEX IF NOT EXISTS idx_quotes_fl     ON quotes(fl_number);
CREATE INDEX IF NOT EXISTS idx_gen_created ON generated_quotes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_est_number   ON estimates(estimate_number);
CREATE INDEX IF NOT EXISTS idx_est_customer ON estimates(customer_name);
CREATE INDEX IF NOT EXISTS idx_est_created  ON estimates(created_at DESC);
