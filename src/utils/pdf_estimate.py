"""
Generate Calyx Containers Estimate PDFs.

Produces a branded PDF matching the Calyx document style,
using 'Estimate' terminology with appropriate terms & conditions.
"""
import io
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit, ImageReader


# ── Brand Colors ───────────────────────────────────────────────────
CHARCOAL = HexColor("#1a1a1a")
DARK_GREY = HexColor("#4a4a4a")
MID_GREY = HexColor("#6b7280")
LIGHT_GREY = HexColor("#e5e7eb")
TABLE_HEADER_BG = HexColor("#f3f4f6")

# Logo — cached PNG bytes fetched once at startup (from filesystem or URL)
_LOGO_BYTES: bytes | None = None

def _load_logo() -> bytes | None:
    # Try filesystem first
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "assets" / "calyx_logo.png",
        Path.cwd() / "assets" / "calyx_logo.png",
        Path("/app/assets/calyx_logo.png"),
    ]
    for p in candidates:
        if p.exists():
            return p.read_bytes()
    # Fall back to fetching from public Vercel URL
    try:
        with urllib.request.urlopen(
            "https://calyx-quoting-portal.vercel.app/calyx-logo.svg", timeout=5
        ) as resp:
            return resp.read()
    except Exception:
        return None

_LOGO_BYTES = _load_logo()


def _generate_estimate_number() -> str:
    """Generate a unique estimate number: EST-YYYYMMDD-HHMMSS-XX."""
    now = datetime.now()
    short_id = uuid.uuid4().hex[:2].upper()
    return f"EST-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{short_id}"


def generate_estimate_pdf(
    customer_name: str,
    calyx_rep: str,
    dimensions: str,
    print_method: str,
    substrate: str,
    finish: str,
    colors: str,
    embellishment: str,
    fill_style: str,
    seal_type: str,
    zipper: str,
    tear_notch: str,
    hole_punch: str,
    gusset_detail: str,
    corners: str,
    pricing: list[dict],
    estimate_number: str | None = None,
) -> tuple[bytes, str]:
    """
    Generate estimate PDF and return (pdf_bytes, estimate_number).

    pricing: list of dicts with keys 'quantity', 'unit_price', 'total_price'
    """
    if estimate_number is None:
        estimate_number = _generate_estimate_number()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter  # 612 x 792

    ml = 0.75 * inch
    mr = w - 0.75 * inch
    content_w = mr - ml
    y = h - 0.6 * inch

    # ── Logo ───────────────────────────────────────────────────
    logo_drawn = False
    if _LOGO_BYTES:
        try:
            logo = ImageReader(io.BytesIO(_LOGO_BYTES))
            c.drawImage(logo, ml, y - 32, width=200, height=60,
                        preserveAspectRatio=True, anchor='sw', mask='auto')
            logo_drawn = True
        except Exception:
            pass
    if not logo_drawn:
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(CHARCOAL)
        c.drawString(ml, y, "CALYX CONTAINERS")

    # ESTIMATE title (right aligned)
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(CHARCOAL)
    c.drawRightString(mr, y, "ESTIMATE")

    y -= 50

    # ── Company & Customer Info ────────────────────────────────
    c.setFont("Helvetica", 8.5)
    c.setFillColor(DARK_GREY)
    for line in ["Calyx Containers", "1991 Parkway Blvd",
                 "West Valley City, UT 84119", "(724) 303-7481"]:
        c.drawString(ml, y, line)
        y -= 12

    # Right column info
    info_y = y + 48
    info_val_x = mr - 200 + 100
    today = datetime.now().strftime("%-m/%-d/%y")

    def _info(label, value, ypos):
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(MID_GREY)
        c.drawRightString(mr - 200 + 95, ypos, f"{label}:")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(CHARCOAL)
        c.drawString(info_val_x, ypos, value)

    _info("Estimate Issued", today, info_y)
    _info("Customer Name", customer_name, info_y - 13)
    _info("Calyx Rep", calyx_rep, info_y - 26)
    _info("Lead Time", "TBD", info_y - 39)

    y -= 20

    # ── Blue rule ──────────────────────────────────────────────
    c.setStrokeColor(HexColor("#1e3a5f"))
    c.setLineWidth(2.5)
    c.line(ml, y, mr, y)
    y -= 22

    # ── Print Method Header ───────────────────────────────────
    METHOD_DISPLAY = {
        "digital": "Digital",
        "flexographic": "Flexographic",
        "international air": "International Air",
        "international ocean": "International Ocean",
    }
    method_label = METHOD_DISPLAY.get(print_method.lower(), print_method)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(CHARCOAL)
    c.drawString(ml, y, method_label)
    y -= 18

    # ── Estimate info line ─────────────────────────────────────
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(MID_GREY)
    c.drawString(ml, y, "Estimate:")
    c.setFont("Helvetica", 9)
    c.setFillColor(CHARCOAL)
    c.drawString(ml + 55, y, estimate_number)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(MID_GREY)
    c.drawString(ml + 260, y, "Product Dimensions:")
    c.setFont("Helvetica", 9)
    c.setFillColor(CHARCOAL)
    c.drawString(ml + 365, y, dimensions)
    y -= 22

    # ── Specs Grid (balanced 2 columns, 6 left / 5 right) ─────
    all_specs = [
        ("Substrate", substrate),
        ("Finish", finish),
        ("Colors", colors),
        ("Embellishment", embellishment),
        ("Fill Style", fill_style),
        ("Seal Type", seal_type),
        ("Zipper", zipper),
        ("Tear Notch", tear_notch),
        ("Hole Punch", hole_punch),
        ("Gusset Detail", gusset_detail),
        ("Corners", corners),
    ]
    mid = (len(all_specs) + 1) // 2  # 6 left, 5 right
    left_specs = all_specs[:mid]
    right_specs = all_specs[mid:]

    spec_y = y
    for label, value in left_specs:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(MID_GREY)
        c.drawString(ml, spec_y, f"{label}:")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(CHARCOAL)
        c.drawString(ml + 85, spec_y, value or "—")
        spec_y -= 14

    spec_y2 = y
    col2_x = ml + 260
    for label, value in right_specs:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(MID_GREY)
        c.drawString(col2_x, spec_y2, f"{label}:")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(CHARCOAL)
        c.drawString(col2_x + 90, spec_y2, value or "—")
        spec_y2 -= 14

    y = min(spec_y, spec_y2) - 20

    # ── Item Summary Table (chunked, 6 tiers per section) ──────
    TIERS_PER_SECTION = 6
    chunks = [pricing[i:i + TIERS_PER_SECTION] for i in range(0, len(pricing), TIERS_PER_SECTION)]

    for chunk_idx, chunk in enumerate(chunks):
        # Section header (only on first chunk)
        if chunk_idx == 0:
            c.setFillColor(TABLE_HEADER_BG)
            c.rect(ml, y - 4, content_w, 16, fill=1, stroke=0)
            c.setFillColor(CHARCOAL)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(ml + 6, y, "Item Summary")
            y -= 22

        num_cols = len(chunk)
        label_col_w = 100
        data_area_w = content_w - label_col_w
        col_w = data_area_w / max(num_cols, 1)

        # Quantity header row
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(CHARCOAL)
        for i, p in enumerate(chunk):
            cx = ml + label_col_w + col_w * i + col_w / 2
            c.drawCentredString(cx, y, f"{p['quantity']:,}")

        y -= 4
        c.setStrokeColor(LIGHT_GREY)
        c.setLineWidth(0.5)
        c.line(ml, y, mr, y)
        y -= 14

        # Price Per Unit
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(DARK_GREY)
        c.drawString(ml + 6, y, "Price Per Unit")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(CHARCOAL)
        for i, p in enumerate(chunk):
            val = p["unit_price"]
            price_str = f"${val:,.4f}" if val < 1 else f"${val:,.2f}"
            cx = ml + label_col_w + col_w * i + col_w / 2
            c.drawCentredString(cx, y, price_str)
        y -= 16

        # Total Price
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(DARK_GREY)
        c.drawString(ml + 6, y, "Total Price")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(CHARCOAL)
        for i, p in enumerate(chunk):
            cx = ml + label_col_w + col_w * i + col_w / 2
            c.drawCentredString(cx, y, f"${p['total_price']:,.2f}")
        y -= 24

    # ── Terms & Conditions ─────────────────────────────────────
    c.setStrokeColor(LIGHT_GREY)
    c.setLineWidth(0.5)
    c.rect(ml, y - 110, content_w, 110, fill=0, stroke=1)

    terms_y = y - 12
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(DARK_GREY)

    terms = [
        "This document is a preliminary estimate provided for budgetary and planning purposes only. "
        "It does not constitute a firm price commitment or a binding agreement.",
        "",
        "A firm estimate will be provided once artwork has been received and the customer is ready "
        "to proceed with a purchase. Final pricing may vary based on artwork review, material "
        "availability, production specifications, and order confirmation details.",
        "",
        "Quantity Variance: A \u00b110% quantity variation is permissible unless a different amount is specified.",
        "",
        "Thank you for the opportunity to present this estimate.",
    ]
    for line in terms:
        if line == "":
            terms_y -= 6
            continue
        for wl in simpleSplit(line, "Helvetica-Oblique", 7.5, content_w - 16):
            c.drawString(ml + 8, terms_y, wl)
            terms_y -= 10

    c.save()
    buf.seek(0)
    return buf.read(), estimate_number
