"""
Bridge between Supabase quote data and PDF generation.

Extracts parameters from the quote's JSONB specifications and pricing
columns and calls the existing generate_estimate_pdf function for
each active pricing method.
"""
import io
import logging

from pypdf import PdfWriter, PdfReader
from src.utils.pdf_estimate import generate_estimate_pdf

logger = logging.getLogger(__name__)

METHOD_COLUMNS = {
    "pricing_digital": "Digital",
    "pricing_flexo": "Flexographic",
    "pricing_intl_air": "International Air",
    "pricing_intl_ocean": "International Ocean",
}


def build_pdfs_for_quote(
    quote_data: dict,
    customer_name: str,
    calyx_rep: str = "Owen Labombard",
) -> list[tuple[bytes, str, str]]:
    """
    Generate one PDF per active pricing method on the quote.

    Returns list of (pdf_bytes, estimate_number, method_label) tuples.
    """
    specs = quote_data.get("specifications", {})

    w = specs.get("width", 0)
    h = specs.get("height", 0)
    g = specs.get("gusset", 0)
    dimensions = f"{w} x {h}" + (f" x {g}" if g else "")

    results = []

    for col, method_label in METHOD_COLUMNS.items():
        pricing_data = quote_data.get(col)
        if pricing_data is None:
            continue

        tiers = pricing_data.get("tiers", [])
        if not tiers:
            continue

        pricing = [
            {
                "quantity": t["quantity"],
                "unit_price": t["unit_price"],
                "total_price": t["total_price"],
            }
            for t in tiers
        ]

        pdf_bytes, estimate_number = generate_estimate_pdf(
            customer_name=customer_name,
            calyx_rep=calyx_rep,
            dimensions=dimensions,
            print_method=method_label,
            substrate=specs.get("substrate", "N/A"),
            finish=specs.get("finish", "N/A"),
            colors="CMYK",
            embellishment=specs.get("embellishment", "None"),
            fill_style=specs.get("fill_style", "N/A"),
            seal_type=specs.get("seal_type", "N/A"),
            zipper=specs.get("zipper", "None"),
            tear_notch=specs.get("tear_notch", "None"),
            hole_punch=specs.get("hole_punch", "None"),
            gusset_detail=specs.get("gusset_type", "None"),
            corners=specs.get("corners", "Straight"),
            pricing=pricing,
        )

        results.append((pdf_bytes, estimate_number, method_label))

    return results


def merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes:
    """Merge multiple PDFs into a single PDF in order."""
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def build_merged_pdf_for_quote(
    quote_data: dict,
    customer_name: str,
    calyx_rep: str = "Owen Labombard",
) -> tuple[bytes, str] | None:
    """
    Generate all method PDFs and merge into a single PDF.

    Returns (merged_pdf_bytes, primary_estimate_number) or None if no pricing.
    Order: Digital → Flexographic → International Air → International Ocean
    """
    pdfs = build_pdfs_for_quote(quote_data, customer_name, calyx_rep)
    if not pdfs:
        return None
    primary_estimate_number = pdfs[0][1]
    merged = merge_pdfs([pdf_bytes for pdf_bytes, _, _ in pdfs])
    return merged, primary_estimate_number
