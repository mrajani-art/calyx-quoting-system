# Database Schema Documentation

## Overview

The system uses Supabase (PostgreSQL) with 4 core tables.

## Entity Relationship

```
quotes (1) ──→ (many) quote_prices
                        │
ml_models               │ (via vendor matching)
                        │
generated_quotes ───────┘ (predictions stored as JSONB)
```

## Tables

### `quotes`
Stores every historical quote from both the Google Sheet tracker and extracted PDFs.

| Column             | Type         | Notes                                          |
|--------------------|--------------|-------------------------------------------------|
| id                 | UUID (PK)    | Auto-generated                                  |
| created_at         | TIMESTAMPTZ  | Auto-set                                         |
| vendor             | TEXT         | `dazpak` or `ross`                               |
| print_method       | TEXT         | `digital` or `flexographic`                      |
| fl_number          | TEXT         | e.g. `FL-DL-1495`, `FL-CQ-0855`                 |
| quote_number       | TEXT         | Dazpak Quote # or Ross Estimate No               |
| quote_date         | DATE         | From PDF                                         |
| source_type        | TEXT         | `spreadsheet`, `pdf`, or `manual`                |
| width              | NUMERIC(8,3) | Inches                                           |
| height             | NUMERIC(8,3) | Inches                                           |
| gusset             | NUMERIC(8,3) | Inches (default 0)                               |
| print_width        | NUMERIC(8,3) | **Generated**: `height * 2 + gusset`             |
| bag_area_sqin      | NUMERIC(10,3)| **Generated**: `width * height`                  |
| substrate          | TEXT         | MET PET, CLR PET, WHT MET PET, HB CLR PET       |
| finish             | TEXT         | Matte Laminate, Soft Touch Laminate, None        |
| embellishment      | TEXT         | None, Hot Stamp, etc.                            |
| fill_style         | TEXT         | Top, Bottom                                      |
| seal_type          | TEXT         | Stand Up, 3 Side Seal                            |
| gusset_type        | TEXT         | None, K Seal, K Seal & Skirt Seal, Flat Bottom   |
| zipper             | TEXT         | CR Zipper, Standard CR, Presto CR, No Zipper     |
| tear_notch         | TEXT         | Standard, Double (2), None                       |
| hole_punch         | TEXT         | None, Standard, Round, Euro Slot, Sombrero       |
| corner_treatment   | TEXT         | Straight, Rounded                                |
| num_skus           | INTEGER      | Dazpak: number of SKUs on quote                  |
| num_colors         | INTEGER      | Dazpak: ink color count                          |
| web_width          | NUMERIC(8,4) | Dazpak: e.g. 13.0000                             |
| repeat_length      | NUMERIC(8,4) | Dazpak: e.g. 5.2500                              |
| material_spec      | TEXT         | Full material description from PDF               |
| account_no         | TEXT         | Ross: customer account number                    |
| seal_width         | TEXT         | Ross: e.g. ".3125 Seal"                          |
| colors_spec        | TEXT         | Ross: e.g. "CMYK"                                |

### `quote_prices`
One row per quantity tier per quote. Dazpak quotes have ~5 tiers, Ross ~4.

| Column             | Type          | Notes                                          |
|--------------------|---------------|-------------------------------------------------|
| id                 | UUID (PK)     |                                                  |
| quote_id           | UUID (FK)     | References `quotes.id`                           |
| tier_index         | SMALLINT      | 0-based tier position                            |
| quantity           | INTEGER       | e.g. 75000, 100000 (Dazpak) or 4000, 5000 (Ross)|
| unit_price         | NUMERIC(10,5) | Price per unit/impression                        |
| total_price        | NUMERIC(12,2) | Ross: qty × unit price                           |
| price_per_m_imps   | NUMERIC(12,4) | Dazpak: $/1000 impressions                       |
| price_per_msi      | NUMERIC(10,4) | Dazpak: $/MSI                                   |
| price_per_ea_imp   | NUMERIC(10,4) | Dazpak: $/each impression                       |
| tolerance_pct      | NUMERIC(5,2)  | Dazpak: +/- percentage                          |
| adder_per_m_imps   | NUMERIC(12,4) | Dazpak: adder for additional SKU                 |
| adder_per_msi      | NUMERIC(10,4) | Dazpak: adder for additional SKU                 |
| adder_per_ea_imp   | NUMERIC(10,4) | Dazpak: adder for additional SKU                 |

### `ml_models`
Registry of trained models with performance metrics.

| Column              | Type    | Notes                              |
|---------------------|---------|------------------------------------|
| id                  | UUID    |                                     |
| vendor              | TEXT    | `dazpak` or `ross`                  |
| model_type          | TEXT    | `gradient_boosting`                 |
| target_col          | TEXT    | `unit_price`                        |
| metrics             | JSONB   | `{mape, rmse, r2, coverage_90}`     |
| feature_importances | JSONB   | `{feature: importance, ...}`        |
| model_path          | TEXT    | Path to .joblib file                |
| is_active           | BOOLEAN | Only one active per vendor+target   |

### `generated_quotes`
Stores every prediction made by the system for audit trail.

| Column         | Type    | Notes                              |
|----------------|---------|------------------------------------|
| id             | UUID    |                                     |
| created_at     | TIMESTAMPTZ |                                 |
| input_params   | JSONB   | Full user input specs               |
| vendor_routed  | TEXT    | Which vendor was selected           |
| predictions    | JSONB   | `{qty: {price, lower, upper}}`      |
| confidence     | JSONB   | Model confidence details            |
| cost_factors   | JSONB   | Feature importance breakdown        |

## Setup

Run the SQL from `src/data/supabase_client.py :: SCHEMA_SQL` in your Supabase SQL Editor.
