"""
Application configuration for Calyx Containers ML Quoting System.
All specification options derived from actual historical quote data.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / os.getenv("MODEL_DIR", "models")
MODEL_DIR.mkdir(exist_ok=True)

# ── Supabase ────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ── Google APIs ─────────────────────────────────────────────────────
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "config/google_service_account.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1hXfQiACUAkFK04lTdj5NFx1rxE8A7jcSqVLG4kuazrQ")
SPREADSHEET_GID = os.getenv("SPREADSHEET_GID", "1053012450")
DAZPAK_FOLDER_ID = os.getenv("DAZPAK_FOLDER_ID", "12A8sPC0mL4XanLAgfcT_mTQzmG6hItpl")
ROSS_FOLDER_ID = os.getenv("ROSS_FOLDER_ID", "1SxqbXb7Xn7Cw9xsEVNp2QWiWrOdqFXUc")

# ── Vendor Business Rules ──────────────────────────────────────────
# Dazpak: Flexographic, MOQ 35,000-50,000 per SKU (from PDF: "35,000 MOQ per SKU")
DAZPAK_MIN_ORDER_QTY = 35_000
# Ross: Digital, only accepts print width > 12" (Height × 2 + Gusset)
ROSS_MIN_PRINT_WIDTH_INCHES = 12.0

# ── Specification Options (from actual spreadsheet data) ───────────
# Column A: Vendor
VENDORS = ["Dazpak", "Ross"]

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
    "Custom",
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
FINISH_UI_OPTIONS = ["Matte Laminate", "Soft Touch Laminate", "None"]

# Column G: Embellishment
EMBELLISHMENT_OPTIONS = ["N/A", "NA", "None"]
EMBELLISHMENT_UI_OPTIONS = ["None", "Hot Stamp (Gold)", "Hot Stamp (Silver)", "Embossing", "Spot UV"]

# Column H: Fill Style
FILL_STYLE_OPTIONS = ["Top", "Bottom"]

# Column I: Seal Type
SEAL_TYPE_OPTIONS = [
    "Stand Up",
    "3 Side Seal",
    "3-Side Seal",
]
SEAL_TYPE_UI_OPTIONS = ["Stand Up", "3 Side Seal"]

# Column J: Gusset Details
GUSSET_OPTIONS = [
    "Flat Bottom / Side Gusset",
    "K Seal",
    "K Seal & Skirt Seal",
    "N/A",
]
GUSSET_UI_OPTIONS = ["Flat Bottom / Side Gusset", "K Seal", "K Seal & Skirt Seal", "None"]

# Column K: Zipper
ZIPPER_OPTIONS = [
    "CR Zipper",          # Child-Resistant
    "Standard CR",        # Standard Child-Resistant
    "No Zipper",
    "Presto CR Zipper",   # From Ross PDF
]
ZIPPER_UI_OPTIONS = ["CR Zipper", "Standard CR", "Presto CR Zipper", "No Zipper"]

# Column L: Tear Notch
TEAR_NOTCH_OPTIONS = ["Standard", "N/A", "2 - Tear Notch"]
TEAR_NOTCH_UI_OPTIONS = ["Standard", "Double (2)", "None"]

# Column M: Hole Punch
HOLE_PUNCH_OPTIONS = ["N/A", "Standard", "Round (Butterfly)", "Euro Slot", "Sombrero"]
HOLE_PUNCH_UI_OPTIONS = ["None", "Standard", "Round (Butterfly)", "Euro Slot", "Sombrero"]

# Column O: Corners
CORNER_OPTIONS = ["Straight", "Rounded", "Round"]
CORNER_UI_OPTIONS = ["Straight", "Rounded"]

# Print method mapped from vendor
PRINT_METHODS = ["Digital", "Flexographic"]

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
# Dazpak typical tiers (from PDF): 75K, 100K, 200K, 350K, 500K
DAZPAK_DEFAULT_TIERS = [75_000, 100_000, 200_000, 350_000, 500_000]
# Ross typical tiers (from PDF): 4K, 5K, 6K, 10K
ROSS_DEFAULT_TIERS = [4_000, 5_000, 6_000, 10_000]
# User-configurable tiers (6 tiers)
DEFAULT_QTY_TIERS = [1_000, 5_000, 10_000, 25_000, 50_000, 100_000]

# ── ML Configuration ───────────────────────────────────────────────
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
CONFIDENCE_LOWER = 0.10
CONFIDENCE_UPPER = 0.90

# ── Dazpak Pricing Columns (from PDF structure) ───────────────────
# UOM: Impressions
# Pricing: Price/M Imps, Price/MSI, Price/Ea Imp
# Adder for each additional SKU: Adder/M Imps, Adder/MSI, Adder/Ea Imp
DAZPAK_PRICE_COLS = ["price_per_m_imps", "price_per_msi", "price_per_ea_imp"]
DAZPAK_ADDER_COLS = ["adder_per_m_imps", "adder_per_msi", "adder_per_ea_imp"]

# ── Ross Pricing Columns (from PDF structure) ─────────────────────
# Simple: Quantity, Each (unit price), Total
ROSS_PRICE_COLS = ["unit_price", "total_price"]
