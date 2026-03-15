"""
PDF Quote Extraction Pipeline.

Extracts structured pricing data from Dazpak and Ross PDF quotes.
Each vendor has a very different format — see below.

── Dazpak PDF Structure (from screenshot) ───────────────────────────
Header:     Quote #, Date, To, Ships To, Attention, Comments
Item:       FL-CQ-XXXX description, dimensions (W × H + BG), features
Material:   Layer list (e.g. .56 Matte PET / Adhesive / .48 MET PET / 3.0 LLDPE)
Pricing:    Table with columns:
            UOM | Quantities | +/- | Price/M Imps | Price/MSI | Price/Ea Imp
            Plus adder columns: Adder/M Imps | Adder/MSI | Adder/Ea Imp
Footer:     Web Width, Repeat, Terms, FOB, Art & Plates cost

── Ross PDF Structure (from screenshot) ─────────────────────────────
Header:     Date, Estimate No., Account No.
Customer:   Company, address
Details:    Application (FL-DL-XXXX name), Product Size (W × H × G)
            Colors (CMYK), Materials (Stock# descriptions)
Finishing:  Seal Width, Hang Hole, Zipper, Tear Notch, Gusset, Other
Pricing:    Simple table: Quantity | Each | Total | Grand Total
Footer:     Non-Recurring Charges, Thank You, Terms
"""
import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logger.warning("pdfplumber not installed — PDF extraction disabled")


# ── Dazpak PDF Parser ──────────────────────────────────────────────

def extract_dazpak_pdf(pdf_path: str, *, source_filename: str = None) -> Optional[dict]:
    """
    Extract structured data from a single Dazpak quotation PDF.
    Returns dict with quote metadata, specs, and pricing tiers.

    Args:
        pdf_path: Local path to the downloaded PDF file.
        source_filename: Original Google Drive filename (used to extract
            substrate, finish, and num_colors when PDF body parsing fails).
    """
    if not HAS_PDFPLUMBER:
        return None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            tables = []
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception as e:
        logger.error(f"Failed to read Dazpak PDF {pdf_path}: {e}")
        return None

    result = {
        "vendor": "dazpak",
        "print_method": "flexographic",
        "source_type": "pdf",
        "source_file": Path(pdf_path).name,
        "prices": [],
    }

    # ── Extract quote metadata ──────────────────────────────────────
    # Quote #
    m = re.search(r'Quote\s*#\s*(\d+)', text)
    if m:
        result["quote_number"] = m.group(1)

    # Date
    m = re.search(r'Date\s+(\d{1,2}/\d{1,2}/\d{2,4})', text)
    if m:
        result["quote_date"] = m.group(1)

    # FL number
    m = re.search(r'(FL-[A-Z]{2}-\d+)', text)
    if m:
        result["fl_number"] = m.group(1)

    # ── Extract dimensions from item description ────────────────────
    # Pattern: 5"W X 5.5H + 2" B.G.  OR  5W X 5.5H + 2 B.G.
    dim_pattern = re.compile(
        r'([\d.]+)["\s]*W\s*[Xx×]\s*([\d.]+)["\s]*H'
        r'(?:\s*[+×Xx]\s*([\d.]+)["\s]*(?:B\.?G\.?|G)?)?',
        re.IGNORECASE
    )
    m = dim_pattern.search(text)
    if m:
        result["width"] = float(m.group(1))
        result["height"] = float(m.group(2))
        result["gusset"] = float(m.group(3)) if m.group(3) else 0.0

    # ── Extract features from description ───────────────────────────
    text_lower = text.lower()

    # Tear Notch
    if 'tear notch' in text_lower:
        result["tear_notch"] = "Standard"

    # Zipper
    if 'cr zipper' in text_lower:
        result["zipper"] = "CR Zipper"
    elif 'no zipper' in text_lower:
        result["zipper"] = "No Zipper"

    # Double Cut
    if 'double cut' in text_lower:
        result["corner_treatment"] = "Straight"

    # Number of SKUs
    m = re.search(r'(\d+)\s*SKU', text)
    if m:
        result["num_skus"] = int(m.group(1))

    # Number of colors
    m = re.search(r'Ink\s*-\s*(\d+)\s*Color', text, re.IGNORECASE)
    if m:
        result["num_colors"] = int(m.group(1))

    # MOQ
    m = re.search(r'([\d,]+)\s*MOQ', text)
    if m:
        result["moq"] = int(m.group(1).replace(',', ''))

    # ── Extract material specification ──────────────────────────────
    # Look for material block between "Material:" and next section.
    # Try multiple patterns — pdfplumber output varies across PDFs.
    mat_match = (
        # Pattern 1: Material on next line(s) until Pricing/UOM
        re.search(r'Material:\s*\n(.+?)(?:\n\s*Pricing|\n\s*UOM)', text, re.DOTALL)
        # Pattern 2: Material on same line
        or re.search(r'Material:\s*(.+?)(?:\n\s*(?:Pricing|UOM|Web Width|Repeat))', text, re.DOTALL)
        # Pattern 3: Material followed by any section break
        or re.search(r'Material:\s*\n?(.+?)(?:\n\n|\n\s*\n)', text, re.DOTALL)
    )
    if mat_match:
        result["material_spec"] = mat_match.group(1).strip().replace('\n', ' / ')

    # ── Parse substrate + finish from material_spec or filename ────
    from dazpak_material_parser import parse_dazpak_material_spec, parse_dazpak_filename

    # Try material_spec first (from PDF body)
    if result.get("material_spec"):
        mat = parse_dazpak_material_spec(result["material_spec"])
        if mat["substrate"]:
            result["substrate"] = mat["substrate"]
        if mat["finish"]:
            result["finish"] = mat["finish"]

    # Fallback: parse the original Drive filename
    fname = source_filename or Path(pdf_path).name
    if not result.get("substrate") or not result.get("finish"):
        fn_mat = parse_dazpak_filename(fname)
        if fn_mat["substrate"] and not result.get("substrate"):
            result["substrate"] = fn_mat["substrate"]
        if fn_mat["finish"] and not result.get("finish"):
            result["finish"] = fn_mat["finish"]
        if fn_mat["num_colors"] and not result.get("num_colors"):
            result["num_colors"] = fn_mat["num_colors"]

    # ── Extract Web Width and Repeat ────────────────────────────────
    m = re.search(r'Web Width\s*[\n\s]*([\d.]+)', text)
    if m:
        result["web_width"] = float(m.group(1))

    m = re.search(r'Repeat\s*[\n\s]*([\d.]+)', text)
    if m:
        result["repeat_length"] = float(m.group(1))

    # ── Extract pricing from tables ─────────────────────────────────
    # Dazpak table columns (from PDF screenshot):
    #   UOM | Quantities | +/- | Price/M Imps | Price/MSI | Price/Ea Imp | Adder/M Imps | Adder/MSI | Adder/Ea Imp
    #
    # pdfplumber can shift column positions, so we:
    #   1. Try to find the header row and map column positions dynamically
    #   2. Fall back to identifying columns by value ranges
    for table in tables:
        if not table or len(table) < 2:
            continue

        # Find the header row
        header_row = None
        col_map = {}
        for i, row in enumerate(table):
            row_text = ' '.join(str(c) for c in row if c).lower()
            if 'quantities' in row_text or 'price' in row_text or 'ea imp' in row_text:
                header_row = i
                # Try to map column positions from header text
                for j, cell in enumerate(row):
                    cell_text = str(cell).lower().strip() if cell else ''
                    if 'quantities' in cell_text or 'qty' in cell_text:
                        col_map['qty'] = j
                    elif 'ea imp' in cell_text and 'adder' not in cell_text:
                        col_map['ea_imp'] = j
                    elif 'msi' in cell_text and 'adder' not in cell_text:
                        col_map['msi'] = j
                    elif 'm imp' in cell_text and 'adder' not in cell_text:
                        col_map['m_imps'] = j
                    elif '+' in cell_text or '-' in cell_text:
                        col_map['tolerance'] = j
                break

        if header_row is None:
            continue

        # Parse data rows after header
        for row in table[header_row + 1:]:
            if not row or len(row) < 3:
                continue

            cells = [str(c).strip() if c else '' for c in row]

            # Strategy 1: Use mapped column positions
            if col_map.get('qty') is not None and col_map.get('ea_imp') is not None:
                qty = _parse_number(cells[col_map['qty']] if col_map['qty'] < len(cells) else '')
                price_ea_imp = _parse_currency(cells[col_map['ea_imp']] if col_map['ea_imp'] < len(cells) else '')
                price_msi = _parse_currency(cells[col_map.get('msi', 99)] if col_map.get('msi', 99) < len(cells) else '')
                price_m_imps = _parse_currency(cells[col_map.get('m_imps', 99)] if col_map.get('m_imps', 99) < len(cells) else '')
                tolerance = _parse_number(cells[col_map.get('tolerance', 99)] if col_map.get('tolerance', 99) < len(cells) else '')
            else:
                # Strategy 2: Use fixed positions (original assumption)
                qty = _parse_number(cells[1] if len(cells) > 1 else '')
                tolerance = _parse_number(cells[2] if len(cells) > 2 else '')
                price_m_imps = _parse_currency(cells[3] if len(cells) > 3 else '')
                price_msi = _parse_currency(cells[4] if len(cells) > 4 else '')
                price_ea_imp = _parse_currency(cells[5] if len(cells) > 5 else '')

            if not qty or not price_ea_imp:
                # Strategy 3: Find the smallest dollar value in the row as Ea Imp
                #   M Imps is ~$150-$300, MSI is ~$2-$4, Ea Imp is ~$0.10-$0.50
                dollar_vals = []
                for j, c in enumerate(cells):
                    v = _parse_currency(c)
                    if v is not None and v > 0:
                        dollar_vals.append((j, v))
                
                int_vals = []
                for j, c in enumerate(cells):
                    v = _parse_number(c)
                    if v is not None and v >= 1000:
                        int_vals.append((j, v))
                
                if int_vals and dollar_vals:
                    qty = int_vals[0][1]  # First large integer = quantity
                    # Sort dollar values: smallest is Ea Imp, medium is MSI, largest is M Imps
                    dollar_vals.sort(key=lambda x: x[1])
                    price_ea_imp = dollar_vals[0][1]  # Smallest = per unit
                    price_msi = dollar_vals[1][1] if len(dollar_vals) > 1 else None
                    price_m_imps = dollar_vals[2][1] if len(dollar_vals) > 2 else None

            if qty and price_ea_imp:
                # Sanity checks: Ea Imp should be $0.01–$2.00 range
                if qty < 100 or qty > 2_000_000:
                    continue
                if price_ea_imp < 0.005 or price_ea_imp > 2.0:
                    continue

                result["prices"].append({
                    "quantity": int(qty),
                    "unit_price": price_ea_imp,
                    "price_per_m_imps": price_m_imps,
                    "price_per_msi": price_msi,
                    "price_per_ea_imp": price_ea_imp,
                    "tolerance_pct": tolerance if isinstance(tolerance, (int, float)) else None,
                    "adder_per_m_imps": None,
                    "adder_per_msi": None,
                    "adder_per_ea_imp": None,
                })

    # If table parsing failed, try regex on raw text
    if not result["prices"]:
        result["prices"] = _extract_dazpak_prices_regex(text)

    return result


def _extract_dazpak_prices_regex(text: str) -> list[dict]:
    """Fallback: extract Dazpak pricing via regex from raw text."""
    prices = []
    # Pattern: quantity  tolerance%  $price  $price  $price
    # Example: 75,000  33%  $220.6000  $3.2322  $0.2206
    pattern = re.compile(
        r'([\d,]+)\s+'               # Quantity
        r'(\d+%?)\s+'               # Tolerance
        r'\$([\d,.]+)\s+'           # Price/M Imps (large, ~$100-$300)
        r'\$([\d,.]+)\s+'           # Price/MSI (medium, ~$2-$5)
        r'\$([\d,.]+)',             # Price/Ea Imp (small, ~$0.10-$0.50)
    )
    for m in pattern.finditer(text):
        qty = int(m.group(1).replace(',', ''))
        m_imps = float(m.group(3).replace(',', ''))
        msi = float(m.group(4).replace(',', ''))
        ea_imp = float(m.group(5).replace(',', ''))

        # Sanity: Ea Imp should be the smallest of the three
        if ea_imp > msi or ea_imp > m_imps:
            continue
        # Ea Imp should be realistic per-bag price
        if ea_imp < 0.005 or ea_imp > 2.0:
            continue
        if qty < 100 or qty > 2_000_000:
            continue

        prices.append({
            "quantity": qty,
            "unit_price": ea_imp,
            "price_per_m_imps": m_imps,
            "price_per_msi": msi,
            "price_per_ea_imp": ea_imp,
            "tolerance_pct": float(m.group(2).replace('%', '')) if '%' in m.group(2) else None,
        })
    return prices


# ── Ross PDF Parser ────────────────────────────────────────────────

def extract_ross_pdf(pdf_path: str) -> Optional[dict]:
    """
    Extract structured data from a single Ross (RossPac) quotation PDF.
    """
    if not HAS_PDFPLUMBER:
        return None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        logger.error(f"Failed to read Ross PDF {pdf_path}: {e}")
        return None

    result = {
        "vendor": "ross",
        "print_method": "digital",
        "source_type": "pdf",
        "source_file": Path(pdf_path).name,
        "prices": [],
    }

    # ── Estimate No ─────────────────────────────────────────────────
    m = re.search(r'Estimate\s*No\.?\s*(\d+)', text)
    if m:
        result["quote_number"] = m.group(1)

    # Account No
    m = re.search(r'Account\s*No\.?\s*(\d+)', text)
    if m:
        result["account_no"] = m.group(1)

    # Date
    m = re.search(r'Date:\s*(.+?)(?:\n|$)', text)
    if m:
        result["quote_date"] = m.group(1).strip()

    # FL Number / Application
    m = re.search(r'Application-?\s*(FL-[A-Z]{2}-\d+)', text)
    if m:
        result["fl_number"] = m.group(1)

    # ── Product Size: "6.12 (W) X 9.75 (H) X 3.00 (G)" ───────────
    m = re.search(
        r'Product\s*Size-?\s*([\d.]+)\s*\(W\)\s*[Xx×]\s*([\d.]+)\s*\(H\)'
        r'(?:\s*[Xx×]\s*([\d.]+)\s*\(G\))?',
        text
    )
    if m:
        result["width"] = float(m.group(1))
        result["height"] = float(m.group(2))
        result["gusset"] = float(m.group(3)) if m.group(3) else 0.0

    # Colors
    m = re.search(r'Colors-?\s*(.+?)(?:\n|$)', text)
    if m:
        result["colors_spec"] = m.group(1).strip()

    # Materials
    m = re.search(r'Materials-?\s*(.+?)(?:\n\s*Finishing|\n\s*$)', text, re.DOTALL)
    if m:
        result["material_spec"] = m.group(1).strip().replace('\n', ' / ')

    # Parse material_spec into substrate + finish + embellishment
    if result.get("material_spec"):
        from ross_material_parser import parse_ross_material_spec
        mat = parse_ross_material_spec(result["material_spec"])
        result["substrate"] = mat["substrate"]
        result["finish"] = mat["finish"]
        if mat.get("embellishment"):
            result["embellishment"] = mat["embellishment"]

    # ── Finishing details ───────────────────────────────────────────
    # Seal Width
    m = re.search(r'Seal\s*Width:\s*(.+?)(?:\s{2,}|\n)', text)
    if m:
        result["seal_width"] = m.group(1).strip()

    # Tear Notch
    m = re.search(r'Tear\s*Notch:\s*(.+?)(?:\s{2,}|\n)', text)
    if m:
        val = m.group(1).strip()
        if '2' in val:
            result["tear_notch"] = "Double (2)"
        elif val.lower() not in ('none', 'n/a'):
            result["tear_notch"] = "Standard"

    # Hang Hole
    m = re.search(r'Hang\s*Hole:\s*(.+?)(?:\s{2,}|\n)', text)
    if m:
        val = m.group(1).strip()
        result["hole_punch"] = "None" if val.lower() in ('none', 'n/a') else val

    # Zipper
    m = re.search(r'Zipper:\s*(.+?)(?:\s{2,}|\n)', text)
    if m:
        val = m.group(1).strip()
        if 'presto' in val.lower():
            result["zipper"] = "Presto CR Zipper"
        elif 'cr' in val.lower():
            result["zipper"] = "CR Zipper"
        elif val.lower() in ('none', 'n/a'):
            result["zipper"] = "No Zipper"
        else:
            result["zipper"] = val

    # Gusset type
    m = re.search(r'Gusset:\s*(.+?)(?:\s{2,}|\n)', text)
    if m:
        val = m.group(1).strip()
        if 'k' in val.lower() and 'seal' in val.lower() and 'skirt' in val.lower():
            result["gusset_type"] = "K Seal & Skirt Seal"
        elif 'k' in val.lower() and 'seal' in val.lower():
            result["gusset_type"] = "K Seal"
        else:
            result["gusset_type"] = val

    # Other (corners, etc.)
    m = re.search(r'Other:\s*(.+?)(?:\s{2,}|\n)', text)
    if m:
        val = m.group(1).strip()
        if 'round' in val.lower():
            result["corner_treatment"] = "Rounded"
        else:
            result["corner_treatment"] = "Straight"

    # ── Pricing: Quantity / Each / Total ────────────────────────────
    # Ross PDF format (from screenshot):
    #   Quantity    Each       Total       Grand Total
    #   4,000       $0.55470   $2,218.80   $2,218.80
    #   5,000       $0.52622   $2,631.10   $2,631.10
    #
    # The regex matches: number  $number  $number
    # We need strict sanity checks because other dollar amounts
    # appear elsewhere in the PDF (Grand Total, Non-Recurring Charges, etc.)
    price_pattern = re.compile(
        r'([\d,]+)\s+\$([\d,.]+)\s+\$([\d,.]+)'
    )
    for m in price_pattern.finditer(text):
        qty = int(m.group(1).replace(',', ''))
        each = float(m.group(2).replace(',', ''))
        total = float(m.group(3).replace(',', ''))

        # ── Sanity checks to filter out false matches ───────────
        # 1. Quantity must be a realistic order quantity (100–500,000)
        if qty < 100 or qty > 500_000:
            continue

        # 2. Unit price must be realistic for per-bag pricing ($0.01–$5.00)
        if each < 0.005 or each > 5.0:
            continue

        # 3. Total should roughly equal qty × each (within 5% tolerance)
        expected_total = qty * each
        if expected_total > 0:
            ratio = total / expected_total
            if ratio < 0.90 or ratio > 1.10:
                continue

        result["prices"].append({
            "quantity": qty,
            "unit_price": each,
            "total_price": total,
        })

    return result


# ── Batch Processing ───────────────────────────────────────────────

def extract_all_pdfs(folder_path: str, vendor: str) -> list[dict]:
    """
    Extract data from all PDFs in a folder.
    vendor: 'dazpak' or 'ross'
    """
    folder = Path(folder_path)
    if not folder.exists():
        logger.error(f"Folder not found: {folder}")
        return []

    extractor = extract_dazpak_pdf if vendor == "dazpak" else extract_ross_pdf
    results = []

    for pdf_file in sorted(folder.glob("*.pdf")):
        logger.info(f"Extracting {pdf_file.name}...")
        data = extractor(str(pdf_file))
        if data and data.get("prices"):
            results.append(data)
        else:
            logger.warning(f"No pricing extracted from {pdf_file.name}")

    logger.info(f"Extracted {len(results)} {vendor} quotes with pricing")
    return results


def pdfs_to_dataframes(extracted: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convert extracted PDF data into (quotes_df, prices_df) for DB insertion.
    """
    quote_rows = []
    price_rows = []

    for i, q in enumerate(extracted):
        # Build quote record
        qr = {
            "vendor": q.get("vendor"),
            "print_method": q.get("print_method"),
            "fl_number": q.get("fl_number"),
            "quote_number": q.get("quote_number"),
            "quote_date": q.get("quote_date"),
            "source_type": "pdf",
            "source_file": q.get("source_file"),
            "width": q.get("width"),
            "height": q.get("height"),
            "gusset": q.get("gusset", 0),
            "substrate": q.get("substrate"),
            "finish": q.get("finish"),
            "embellishment": q.get("embellishment", "None"),
            "fill_style": q.get("fill_style"),
            "seal_type": q.get("seal_type"),
            "gusset_type": q.get("gusset_type"),
            "zipper": q.get("zipper"),
            "tear_notch": q.get("tear_notch"),
            "hole_punch": q.get("hole_punch", "None"),
            "corner_treatment": q.get("corner_treatment"),
            "num_skus": q.get("num_skus"),
            "num_colors": q.get("num_colors"),
            "web_width": q.get("web_width"),
            "repeat_length": q.get("repeat_length"),
            "material_spec": q.get("material_spec"),
            "account_no": q.get("account_no"),
            "seal_width": q.get("seal_width"),
            "colors_spec": q.get("colors_spec"),
        }
        quote_rows.append(qr)

        # Build price records
        for tier_idx, p in enumerate(q.get("prices", [])):
            pr = {
                "_temp_quote_idx": i,
                "tier_index": tier_idx,
                "quantity": p["quantity"],
                "unit_price": p["unit_price"],
                "total_price": p.get("total_price"),
                "price_per_m_imps": p.get("price_per_m_imps"),
                "price_per_msi": p.get("price_per_msi"),
                "price_per_ea_imp": p.get("price_per_ea_imp"),
                "tolerance_pct": p.get("tolerance_pct"),
                "adder_per_m_imps": p.get("adder_per_m_imps"),
                "adder_per_msi": p.get("adder_per_msi"),
                "adder_per_ea_imp": p.get("adder_per_ea_imp"),
            }
            price_rows.append(pr)

    return pd.DataFrame(quote_rows), pd.DataFrame(price_rows)


# ── Helpers ─────────────────────────────────────────────────────────

def _parse_number(s: str) -> Optional[float]:
    """Parse a number string, returning None on failure."""
    if not s:
        return None
    cleaned = re.sub(r'[^0-9.]', '', s.replace(',', ''))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_currency(s: str) -> Optional[float]:
    """Parse a currency string like '$220.6000' or '$0.2206'."""
    if not s:
        return None
    cleaned = re.sub(r'[^0-9.]', '', s)
    try:
        return float(cleaned)
    except ValueError:
        return None
