"""
Google Sheets ingestion — reads the historical quote-request tracker
and normalizes it into the quotes schema.

Spreadsheet columns observed (from screenshot):
  A: Vendor (Dazpak / Ross)
  B: FL Number (FL-DL-1495, FL-CQ-0855, etc.)
  C: Bag (description — sometimes empty)
  D: Size (e.g. "4W X 6.5H X 1.7", "5.25W X 4.65H X 2")
  E: Substrate (MET PET, CLR PET, WHT MET PET, HB CLR PET, etc.)
  F: Finish (Matte Laminate, Soft Touch Laminate, Matte Lam, N/A)
  G: Embellishment (N/A)
  H: Fill Style (Top, Bottom)
  I: Seal Type (Stand Up, 3 Side Seal, 3-Side Seal)
  J: Gusset Details (Flat Bottom / Side Gusset, K Seal, K Seal & Skirt Seal, N/A)
  K: Zipper (CR Zipper, Standard CR, No Zipper)
  L: Tear Notch (Standard, N/A)
  M: Hole Punch (N/A)
  N: Corners — possibly missing from view
  O: Corners (Straight, Rounded, Round)

Note: This sheet tracks quote REQUESTS, not prices.
      Prices come from the PDF quotes (Dazpak / Ross).
"""
import logging
import re
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


# ── Dimension parser ────────────────────────────────────────────────
# Handles formats like:
#   "4W X 6.5H X 1.7"   → (4.0, 6.5, 1.7)
#   "5W X 14.5H"         → (5.0, 14.5, 0.0)
#   "3.5W X 4.5H"        → (3.5, 4.5, 0.0)
#   "4.527W X 5.905H"    → (4.527, 5.905, 0.0)
#   "6.12 (W) X 9.75 (H) X 3.00 (G)"  → Ross PDF format

SIZE_PATTERN = re.compile(
    r'([\d.]+)\s*(?:\(?W\)?)?\s*'       # Width
    r'[Xx×]\s*'
    r'([\d.]+)\s*(?:\(?H\)?)?\s*'       # Height
    r'(?:[Xx×]\s*([\d.]+))?'            # Optional Gusset
    r'(?:\s*(?:\(?[GB]\)?|B\.?G\.?))?',  # Optional BG/G suffix
    re.IGNORECASE
)

def parse_size(size_str: str) -> Tuple[Optional[float], Optional[float], float]:
    """
    Parse a size string into (width, height, gusset).
    Returns (None, None, 0.0) if unparseable.
    """
    if not isinstance(size_str, str) or not size_str.strip():
        return None, None, 0.0

    # Remove extra quotes/inches marks
    cleaned = size_str.replace('"', '').replace("'", '').strip()

    m = SIZE_PATTERN.search(cleaned)
    if m:
        w = float(m.group(1))
        h = float(m.group(2))
        g = float(m.group(3)) if m.group(3) else 0.0
        return w, h, g

    return None, None, 0.0


def normalize_vendor(val: str) -> str:
    """Normalize vendor name."""
    v = str(val).strip().lower()
    if 'daz' in v:
        return 'dazpak'
    if 'ross' in v:
        return 'ross'
    return v


def normalize_finish(val: str) -> str:
    """Normalize finish values."""
    v = str(val).strip().lower()
    if v in ('n/a', 'na', 'none', ''):
        return 'None'
    if 'soft touch' in v or 'soft_touch' in v:
        return 'Soft Touch Laminate'
    if 'matte' in v:
        return 'Matte Laminate'
    return str(val).strip()


def normalize_seal_type(val: str) -> str:
    v = str(val).strip().lower()
    if '3' in v and 'side' in v:
        return '3 Side Seal'
    if 'stand' in v:
        return 'Stand Up'
    return str(val).strip()


def normalize_gusset(val: str) -> str:
    v = str(val).strip().lower()
    if v in ('n/a', 'na', 'none', ''):
        return 'None'
    if 'flat' in v and 'bottom' in v:
        return 'Flat Bottom / Side Gusset'
    if 'k seal' in v and 'skirt' in v:
        return 'K Seal & Skirt Seal'
    if 'k' in v and 'seal' in v:
        return 'K Seal'
    return str(val).strip()


def normalize_zipper(val: str) -> str:
    v = str(val).strip().lower()
    if v in ('n/a', 'na', 'none', '', 'no zipper'):
        return 'No Zipper'
    if 'presto' in v:
        return 'Presto CR Zipper'
    if 'standard' in v:
        return 'Standard CR'
    if 'cr' in v:
        return 'CR Zipper'
    return str(val).strip()


def normalize_na(val: str, default: str = 'None') -> str:
    v = str(val).strip()
    if v.lower() in ('n/a', 'na', 'none', ''):
        return default
    return v


def normalize_corners(val: str) -> str:
    v = str(val).strip().lower()
    if v in ('round', 'rounded'):
        return 'Rounded'
    if v in ('straight', 'standard'):
        return 'Straight'
    if not v or v in ('n/a', 'na'):
        return 'Straight'
    return str(val).strip()


def load_from_gspread() -> pd.DataFrame:
    """
    Fetch data from Google Sheets via gspread.
    Requires GOOGLE_CREDENTIALS service account JSON.
    """
    import gspread
    from google.oauth2.service_account import Credentials
    from config.settings import GOOGLE_CREDENTIALS, SPREADSHEET_ID, SPREADSHEET_GID

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS, scopes=SCOPES)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)

    ws = None
    for sheet in ss.worksheets():
        if str(sheet.id) == str(SPREADSHEET_GID):
            ws = sheet
            break
    if ws is None:
        raise ValueError(f"Worksheet GID {SPREADSHEET_GID} not found")

    return pd.DataFrame(ws.get_all_records())


def load_from_csv(path: str) -> pd.DataFrame:
    """Fallback: load from an exported CSV."""
    return pd.read_csv(path)


def clean_sheet_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize the raw spreadsheet data.
    Maps the actual column letters/names to our schema.
    """
    # ── Standardize column names ────────────────────────────────────
    col_map = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl == 'vendor':
            col_map[c] = 'vendor'
        elif cl in ('fl number', 'fl_number', 'fl#'):
            col_map[c] = 'fl_number'
        elif cl == 'bag':
            col_map[c] = 'bag_desc'
        elif cl == 'size':
            col_map[c] = 'raw_size'
        elif cl == 'substrate':
            col_map[c] = 'substrate'
        elif cl == 'finish':
            col_map[c] = 'finish'
        elif cl == 'embellishment':
            col_map[c] = 'embellishment'
        elif cl in ('fill style', 'fill_style'):
            col_map[c] = 'fill_style'
        elif cl in ('seal type', 'seal_type'):
            col_map[c] = 'seal_type'
        elif cl in ('gusset details', 'gusset_details'):
            col_map[c] = 'gusset_type'
        elif cl == 'zipper':
            col_map[c] = 'zipper'
        elif cl in ('tear notch', 'tear_notch'):
            col_map[c] = 'tear_notch'
        elif cl in ('hole punch', 'hole_punch'):
            col_map[c] = 'hole_punch'
        elif cl == 'corners':
            col_map[c] = 'corner_treatment'

    df = df.rename(columns=col_map)

    # ── Parse dimensions ────────────────────────────────────────────
    if 'raw_size' in df.columns:
        parsed = df['raw_size'].apply(parse_size)
        df['width'] = parsed.apply(lambda x: x[0])
        df['height'] = parsed.apply(lambda x: x[1])
        df['gusset'] = parsed.apply(lambda x: x[2])
    else:
        logger.warning("No 'Size' column found in spreadsheet")
        return df

    # Drop rows where dimensions couldn't be parsed
    df = df.dropna(subset=['width', 'height']).copy()

    # ── Normalize all spec fields ───────────────────────────────────
    df['vendor'] = df['vendor'].apply(normalize_vendor)
    df['print_method'] = df['vendor'].map(
        {'dazpak': 'flexographic', 'ross': 'digital'}
    ).fillna('digital')

    if 'finish' in df.columns:
        df['finish'] = df['finish'].apply(normalize_finish)
    if 'seal_type' in df.columns:
        df['seal_type'] = df['seal_type'].apply(normalize_seal_type)
    if 'gusset_type' in df.columns:
        df['gusset_type'] = df['gusset_type'].apply(normalize_gusset)
    if 'zipper' in df.columns:
        df['zipper'] = df['zipper'].apply(normalize_zipper)
    if 'tear_notch' in df.columns:
        df['tear_notch'] = df['tear_notch'].apply(lambda x: normalize_na(x, 'None'))
    if 'hole_punch' in df.columns:
        df['hole_punch'] = df['hole_punch'].apply(lambda x: normalize_na(x, 'None'))
    if 'corner_treatment' in df.columns:
        df['corner_treatment'] = df['corner_treatment'].apply(normalize_corners)
    if 'embellishment' in df.columns:
        df['embellishment'] = df['embellishment'].apply(lambda x: normalize_na(x, 'None'))
    if 'fill_style' in df.columns:
        df['fill_style'] = df['fill_style'].fillna('Top')

    # Source tracking
    df['source_type'] = 'spreadsheet'

    # Computed fields
    df['print_width'] = df['height'] * 2 + df['gusset']
    df['bag_area_sqin'] = df['width'] * df['height']

    logger.info(f"Cleaned {len(df)} quote requests from spreadsheet")
    return df
