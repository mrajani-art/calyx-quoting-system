"""
Application configuration for Calyx Containers ML Quoting System.
All specification options derived from actual historical quote data.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Streamlit Cloud secrets fallback
try:
    import streamlit as st
    for key in ["SUPABASE_URL", "SUPABASE_KEY", "GOOGLE_CREDENTIALS",
                "SPREADSHEET_ID", "SPREADSHEET_GID", "DAZPAK_FOLDER_ID",
                "ROSS_FOLDER_ID", "INTERNAL_SHEET_ID"]:
        if key in st.secrets and key not in os.environ:
            os.environ[key] = st.secrets[key]
except Exception:
    pass

# ── Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / os.getenv("MODEL_DIR", "models")
MODEL_DIR.mkdir(exist_ok=True)
ASSETS_DIR = BASE_DIR / "assets"

# ── Sales Reps ──────────────────────────────────────────────────────
CALYX_REPS = [
    "Lance Mitton",
    "Brad Sherman",
    "Jake Lynch",
    "Dave Borkowski",
    "Kyle Bissell",
    "Alex Gonzalez",
    "Owen Labombard",
]

# ── Supabase ────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ── Google APIs ─────────────────────────────────────────────────────
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "config/google_service_account.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1hXfQiACUAkFK04lTdj5NFx1rxE8A7jcSqVLG4kuazrQ")
SPREADSHEET_GID = os.getenv("SPREADSHEET_GID", "1053012450")
DAZPAK_FOLDER_ID = os.getenv("DAZPAK_FOLDER_ID", "12A8sPC0mL4XanLAgfcT_mTQzmG6hItpl")
ROSS_FOLDER_ID = os.getenv("ROSS_FOLDER_ID", "1SxqbXb7Xn7Cw9xsEVNp2QWiWrOdqFXUc")
INTERNAL_SHEET_ID = os.getenv("INTERNAL_SHEET_ID", "1L1HRn7WpTnGvZwRIQnppNlMxQdmnOxxUcpbU2r25Bkk")

# ── Vendor Business Rules ──────────────────────────────────────────
# Dazpak: Flexographic, MOQ 35,000-50,000 per SKU (from PDF: "35,000 MOQ per SKU")
DAZPAK_MIN_ORDER_QTY = 35_000
# Ross: Digital, only accepts print width > 12" (Height × 2 + Gusset)
ROSS_MIN_PRINT_WIDTH_INCHES = 12.0
# Internal: Digital (HP 6900), web width < 12" (Height × 2 + Gusset)
INTERNAL_MAX_WEB_WIDTH = 12.0
# TedPack: Gravure (overseas), MOQ ~2,500 per SKU
TEDPACK_MIN_ORDER_QTY = 2_500

# ── Specification Options (from actual spreadsheet data) ───────────
# Column A: Vendor
VENDORS = ["Dazpak", "Ross", "Internal", "TedPack"]

# Column E: Substrate — observed values from spreadsheet
SUBSTRATE_TYPES = [
    "MET PET",           # Metallic PET
    "CLR PET",           # Clear PET
    "WHT MET PET",       # White Metallic PET
    "Wht Met PET",       # Alternate casing
    "HB CLR PET",        # High Barrier Clear PET
    "High Barrier CLR",  # High Barrier Clear
    "MET PET",
    "Custom",
]
# Deduplicated + normalized version for the UI
SUBSTRATE_OPTIONS = [
    "MET PET (Metallic)",
    "CLR PET (Clear)",
    "WHT MET PET (White Metallic)",
    "HB CLR PET (High Barrier Clear)",
]

# Map UI labels → canonical values used in ML features
SUBSTRATE_CANONICAL = {
    "MET PET (Metallic)": "MET_PET",
    "CLR PET (Clear)": "CLR_PET",
    "WHT MET PET (White Metallic)": "WHT_MET_PET",
    "HB CLR PET (High Barrier Clear)": "HB_CLR_PET",
    "Custom": "CUSTOM",
}

# Column F: Finish
FINISH_OPTIONS = [
    "Matte Laminate",
    "Soft Touch Laminate",
    "Matte Lam",          # Abbreviation seen in data
    "N/A",
]
FINISH_UI_OPTIONS = ["Matte Laminate", "Soft Touch Laminate", "Gloss Laminate", "None"]

# Column G: Embellishment
EMBELLISHMENT_OPTIONS = ["N/A", "NA", "None"]
# Embellishment: Foil only available for Gravure (international) quotes
EMBELLISHMENT_UI_OPTIONS_GRAVURE = ["None", "Foil", "Spot UV"]
EMBELLISHMENT_UI_OPTIONS_DEFAULT = ["None", "Spot UV"]

# Column H: Fill Style
FILL_STYLE_OPTIONS = ["Top", "Bottom"]

# Column I: Seal Type
SEAL_TYPE_OPTIONS = [
    "Stand Up",
    "3 Side Seal",
    "3-Side Seal",
]
SEAL_TYPE_UI_OPTIONS = ["3 Side Seal - Top Fill", "3 Side Seal - Bottom Fill", "2 Side Seal - Top Fill", "Stand Up Pouch"]

# Column J: Gusset Details
GUSSET_OPTIONS = [
    "Flat Bottom / Side Gusset",
    "K Seal",
    "K Seal & Skirt Seal",
    "Plow Bottom",
    "N/A",
]
GUSSET_UI_OPTIONS = ["Plow Bottom", "K Seal & Skirt Seal", "None"]

# Column K: Zipper
ZIPPER_OPTIONS = [
    "CR Zipper",          # Child-Resistant
    "Standard CR",        # Standard Child-Resistant
    "No Zipper",
    "Presto CR Zipper",   # From Ross PDF
    "Single Profile Non-CR",  # From internal Cerm data
    "Double Profile Non-CR",  # From internal Cerm data
]
ZIPPER_UI_OPTIONS = ["CR Zipper", "Non-CR Zipper", "No Zipper"]

# Column L: Tear Notch
TEAR_NOTCH_OPTIONS = ["Standard", "N/A", "2 - Tear Notch"]
TEAR_NOTCH_UI_OPTIONS = ["None", "Standard"]

# Column M: Hole Punch
HOLE_PUNCH_OPTIONS = ["N/A", "Standard", "Round (Butterfly)", "Euro Slot", "Sombrero"]
HOLE_PUNCH_UI_OPTIONS = ["None", "Round", "Euro"]

# Column O: Corners
CORNER_OPTIONS = ["Straight", "Rounded", "Round"]
CORNER_UI_OPTIONS = ["Straight", "Rounded"]

# Print method mapped from vendor
PRINT_METHODS = ["Digital", "Flexographic", "Gravure"]

# ── Dazpak Material Layers (from PDF) ──────────────────────────────
# Material structure: thickness + material layers with adhesive between
# Example from PDF: .56 Matte PET / Adhesive / .48 MET PET / Adhesive / 3.0 LLDPE
DAZPAK_OUTER_LAYERS = [
    ".56 Matte PET",
    ".48 MET PET",
    "CLR PET",
    "HB CLR PET",
    "WHT MET PET",
]
DAZPAK_INNER_LAYERS = [
    "3.0 LLDPE",
    "2.5 MIL LDPE",
]

# ── Ross Material Specs (from PDF) ─────────────────────────────────
# Example: Stock# 3905 1.5 mil KARESS THERMAL TACTILE OVER LAMINATE
#          Stock# 5011 3 MIL WHITE MET PET / 2.5 MIL LDPE
ROSS_MATERIAL_STOCKS = {
    "3905": "1.5 mil KARESS THERMAL TACTILE OVER LAMINATE",
    "5011": "3 MIL WHITE MET PET / 2.5 MIL LDPE",
}

# ── Default Quantity Tiers ──────────────────────────────────────────
# Flexographic (Dazpak) default tiers
DAZPAK_DEFAULT_TIERS = [35_000, 50_000, 100_000, 150_000, 200_000, 250_000, 500_000, 750_000, 1_000_000, 1_250_000, 1_500_000, 2_000_000]
# Digital default tiers (Ross + Internal share the same defaults)
ROSS_DEFAULT_TIERS = [5_000, 10_000, 15_000, 25_000, 50_000, 75_000, 100_000, 125_000, 150_000, 175_000, 200_000, 250_000]
INTERNAL_DEFAULT_TIERS = [5_000, 10_000, 15_000, 25_000, 50_000, 75_000, 100_000, 125_000, 150_000, 175_000, 200_000, 250_000]
# TedPack typical tiers (from quotes): 10K-500K
TEDPACK_DEFAULT_TIERS = [10_000, 25_000, 50_000, 100_000, 250_000, 500_000]
# User-configurable tiers (fallback)
DEFAULT_QTY_TIERS = [5_000, 10_000, 15_000, 25_000, 50_000, 75_000, 100_000, 125_000, 150_000, 175_000, 200_000, 250_000]

# ── ML Configuration ───────────────────────────────────────────────
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
CONFIDENCE_LOWER = 0.10
CONFIDENCE_UPPER = 0.90

# TedPack uses wider CI bounds for better coverage (overseas pricing variance)
TEDPACK_CONFIDENCE_LOWER = 0.05
TEDPACK_CONFIDENCE_UPPER = 0.95
# Conservative bias: blend point prediction toward upper bound so quoted cost leans higher
TEDPACK_CONSERVATIVE_BLEND = 0.10  # adjusted = point * 0.90 + upper * 0.10
# Tighter outlier threshold for TedPack (fewer anomalous overseas quotes)
TEDPACK_OUTLIER_SIGMA = 2.5
# Minimum CI half-width as fraction of point estimate (floor)
TEDPACK_MIN_CI_HALF_WIDTH = 0.12  # ±12% minimum spread

# ── Recency Weighting ─────────────────────────────────────────────
# Recent quotes get heavier weight during training so the model
# tracks current market pricing while still learning from history.
#
# Weight curve:
#   0–90 days    → 3.0  (full recent boost)
#   ~270 days    → 1.5  (one half-life of decay)
#   ~450 days    → 0.75
#   630+ days    → 0.2  (floor — never fully ignored)
RECENCY_RECENT_DAYS = 90           # quotes within 90 days = "recent"
RECENCY_RECENT_WEIGHT = 3.0        # 3× weight for recent quotes
RECENCY_DECAY_HALF_LIFE = 180      # older quotes halve every 180 days
RECENCY_MIN_WEIGHT = 0.2           # floor weight for oldest quotes

# ── Dazpak Pricing Columns (from PDF structure) ───────────────────
# UOM: Impressions
# Pricing: Price/M Imps, Price/MSI, Price/Ea Imp
# Adder for each additional SKU: Adder/M Imps, Adder/MSI, Adder/Ea Imp
DAZPAK_PRICE_COLS = ["price_per_m_imps", "price_per_msi", "price_per_ea_imp"]
DAZPAK_ADDER_COLS = ["adder_per_m_imps", "adder_per_msi", "adder_per_ea_imp"]

# ── Ross Pricing Columns (from PDF structure) ─────────────────────
# Simple: Quantity, Each (unit price), Total
ROSS_PRICE_COLS = ["unit_price", "total_price"]

# ── TedPack Pricing Columns ──────────────────────────────────────
# DDP = Delivered Duty Paid (landed cost to UT warehouse)
TEDPACK_PRICE_COLS = ["ddp_air_price", "ddp_ocean_price"]

# ── Ross Equipment Standards (from Label Traxx config) ────────────
# These constants capture Ross's known cost structure drivers
# to improve ML feature engineering. Material cost and margin unknown.

# HP 200K Film Press (wide-format digital)
ROSS_HP200K_RATE_PER_HR = 409.00       # $/hr press rate (all color counts)
ROSS_HP200K_CLICK_CMYOVG = 0.0394     # $/click CMYK+OVG channels
ROSS_HP200K_CLICK_WHITE = 0.01917     # $/click white ink
ROSS_HP200K_CLICK_BLACK = 0.01917     # $/click black ink
ROSS_HP200K_PRIMING_MSI = 0.07        # $/MSI inline priming
ROSS_HP200K_SETUP_HRS = 0.25          # Job setup make-ready hours
ROSS_HP200K_SPOILAGE_PCT = 0.008      # Flat 0.8% spoilage
ROSS_HP200K_MAX_PRINT_WIDTH = 29.5    # inches
ROSS_HP200K_MAX_STOCK_WIDTH = 30.0    # inches

# 30" Gonderflex Press (flexo)
ROSS_GONDERFLEX_RATE_PER_HR = 186.00  # $/hr press rate
ROSS_GONDERFLEX_SPEED_FPM = 180       # ft/min constant
ROSS_GONDERFLEX_PLATE_CHANGE = 25.00  # $ per plate change
ROSS_GONDERFLEX_COLOR_CHANGE = 25.00  # $ per color change
# Spoilage table: (max_length_ft, spoilage_pct)
ROSS_GONDERFLEX_SPOILAGE_TABLE = [
    (5_000, 0.08),
    (10_000, 0.05),
    (20_000, 0.048),
    (30_000, 0.042),
    (40_000, 0.04),
    (50_000, 0.038),
    (60_000, 0.032),
    (70_000, 0.028),
    (80_000, 0.022),
    (90_000, 0.018),
    (100_000, 0.015),
    (450_000, 0.01),
]

# Pouch Maker (converting)
ROSS_CONVERTING_FLAT_RATE = 0.055     # $/pouch flat converting charge
ROSS_ZIPPER_COST_MSI = 5.258772       # $/MSI zipper material
ROSS_ZIPPER_WIDTH_IN = 0.95           # inches, zipper web width
