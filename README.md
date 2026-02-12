# Calyx Containers — ML-Powered Quoting System

Machine learning-powered price prediction for flexible packaging quotes, built for Calyx Containers' Dazpak (flexographic) and Ross (digital) vendor workflows.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Streamlit Frontend                       │
│  Quote Builder │ Analytics │ Model Manager            │
└───────┬────────────────┬──────────────┬──────────────┘
        │                │              │
┌───────▼────────────────▼──────────────▼──────────────┐
│              Business Logic                           │
│  Vendor Routing │ Validation │ Formatting             │
│  Dazpak: MOQ 35K, Flexo                              │
│  Ross: Print Width > 12", Digital                     │
└───────┬────────────────┬──────────────┬──────────────┘
        │                │              │
┌───────▼────────────────▼──────────────▼──────────────┐
│              ML Engine                                │
│  Feature Engineering │ GBR Models │ Quantile CI       │
│  Separate models per vendor                           │
└───────┬────────────────┬──────────────┬──────────────┘
        │                │              │
┌───────▼────────────────▼──────────────▼──────────────┐
│              Data Layer                               │
│  Supabase (PostgreSQL) │ Google Sheets │ PDF Extract  │
└───────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env   # Fill in Supabase + Google creds

# 3. Setup database
python scripts/setup_database.py   # Copy SQL to Supabase

# 4. Train models (demo data to start)
python scripts/train_models.py --demo

# 5. Launch
streamlit run app.py
```

## Data Sources

| Source | Content | Ingestion |
|--------|---------|-----------|
| [Google Sheet](https://docs.google.com/spreadsheets/d/1hXfQiACUAkFK04lTdj5NFx1rxE8A7jcSqVLG4kuazrQ/edit?gid=1053012450) | Quote request specs (Vendor, FL#, Size, Substrate, Finish, etc.) | `scripts/ingest_sheets.py` |
| [Dazpak PDFs](https://drive.google.com/drive/folders/12A8sPC0mL4XanLAgfcT_mTQzmG6hItpl) | Flexographic quotes with tier pricing (Price/M Imps, Price/Ea Imp) | `scripts/ingest_pdfs.py --vendor dazpak` |
| [Ross PDFs](https://drive.google.com/drive/folders/1SxqbXb7Xn7Cw9xsEVNp2QWiWrOdqFXUc) | Digital quotes with Quantity/Each/Total pricing | `scripts/ingest_pdfs.py --vendor ross` |

## Vendor Routing Rules

| Vendor | Print Method | Key Constraint | Typical Tiers |
|--------|-------------|----------------|---------------|
| **Dazpak** | Flexographic | MOQ 35,000 units/SKU | 75K, 100K, 200K, 350K, 500K |
| **Ross** | Digital | Print width > 12" (H×2+G) | 4K, 5K, 6K, 10K |

## ML Model Details

- **Algorithm:** Gradient Boosting Regressor (scikit-learn)
- **Confidence Intervals:** Quantile regression at 10th/90th percentile
- **Features:** 10 numeric (dims, area, log qty, interactions) + 10 categorical (substrate, finish, zipper, etc.)
- **Cross-validation:** 5-fold with MAPE scoring

## Project Structure

```
├── app.py                          # Streamlit entry point
├── config/settings.py              # All configuration & spec options
├── src/
│   ├── data/
│   │   ├── supabase_client.py      # DB schema + CRUD
│   │   ├── sheets_ingestion.py     # Google Sheets parser
│   │   └── pdf_extraction.py       # Dazpak + Ross PDF parsers
│   ├── ml/
│   │   ├── feature_engineering.py  # Feature pipeline
│   │   ├── model_training.py       # Training + evaluation
│   │   └── prediction.py           # Quote generation engine
│   └── utils/
│       ├── vendor_routing.py       # Business rule routing
│       ├── validation.py           # Input validation
│       └── formatting.py           # Display formatting
├── scripts/
│   ├── setup_database.py           # Schema DDL printer
│   ├── ingest_sheets.py            # Sheets → Supabase
│   ├── ingest_pdfs.py              # PDFs → Supabase
│   └── train_models.py             # Model training CLI
├── models/                         # Saved .joblib models
└── docs/
    ├── database_schema.md
    └── deployment_guide.md
```

## Documentation

- [Database Schema](docs/database_schema.md)
- [Deployment Guide](docs/deployment_guide.md)
