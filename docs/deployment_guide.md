# Deployment Guide

## Prerequisites

- Python 3.10+
- Supabase account (free tier: https://supabase.com)
- Google Cloud project with Sheets + Drive API enabled
- (Optional) Streamlit Community Cloud account for hosting

## Step 1: Supabase Setup

1. Create a new Supabase project at https://supabase.com/dashboard
2. Go to **SQL Editor** and run the schema SQL:
   ```bash
   python scripts/setup_database.py
   ```
   Copy the printed SQL and paste into the SQL Editor.
3. Copy your project URL and anon key from **Settings → API**.

## Step 2: Google API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a service account under **IAM & Admin → Service Accounts**
3. Enable **Google Sheets API** and **Google Drive API**
4. Download the JSON key file → save as `config/google_service_account.json`
5. Share the Google Sheet with the service account email (viewer access)
6. Share the Google Drive folders with the service account email

## Step 3: Environment Configuration

```bash
cp .env.example .env
# Edit .env with your credentials:
#   SUPABASE_URL=https://xxx.supabase.co
#   SUPABASE_KEY=eyJ...
#   GOOGLE_CREDENTIALS=config/google_service_account.json
```

## Step 4: Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Step 5: Ingest Data

### From Google Sheets (quote request specs):
```bash
python scripts/ingest_sheets.py
```

### From PDF quotes (pricing):
Download PDFs from the shared Drive folders, then:
```bash
# Create local folders
mkdir -p data/dazpak_pdfs data/ross_pdfs

# Copy/download PDFs into those folders, then:
python scripts/ingest_pdfs.py --vendor dazpak --folder data/dazpak_pdfs/
python scripts/ingest_pdfs.py --vendor ross --folder data/ross_pdfs/
```

### Quick test with demo data:
```bash
python scripts/train_models.py --demo
```

## Step 6: Train Models

```bash
# From Supabase data:
python scripts/train_models.py

# From demo data:
python scripts/train_models.py --demo

# From CSV:
python scripts/train_models.py --csv data/training_data.csv
```

## Step 7: Launch Application

```bash
streamlit run app.py
```

App will be available at http://localhost:8501

## Deployment to Streamlit Community Cloud

1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect your GitHub repo
4. Set secrets in the Streamlit dashboard:
   ```toml
   # .streamlit/secrets.toml (local) or Streamlit Cloud secrets
   SUPABASE_URL = "https://xxx.supabase.co"
   SUPABASE_KEY = "eyJ..."
   ```
5. Deploy

## Deployment to Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t calyx-quoting .
docker run -p 8501:8501 --env-file .env calyx-quoting
```

## Retraining Models

Models should be retrained when:
- New PDF quotes are ingested (monthly recommended)
- Model MAPE exceeds 15%
- New product specifications are added

Retrain via the **Model Manager** page in the UI, or:
```bash
python scripts/train_models.py
```
