"""
Dazpak Material Spec Parser & Backfill
=======================================
Two parsing strategies:

1. parse_dazpak_filename() — Extract substrate, finish, num_colors from the
   Google Drive PDF filename (most reliable — Apps Script names them consistently).

2. parse_dazpak_material_spec() — Parse the raw material_spec text extracted
   from the PDF body (fallback when filename isn't available).

Filename format (from Apps Script email scraper):
  {DATE} - Dazpak - {SUBJECT} - Calyx Containers - Q {QUOTE#} - {DESC} - {DIM} - {MATERIALS} - {COLORS}.pdf

Material portion examples:
  Soft Touch .48 Matte PET - .48 MET PET - 3.0 PE - 5 Colors
  .48 Matte PET - .48 MET PET - 3.0 LLDPE - 9 Colors
  .48 PET - .48 MET PET - 3.0 PE - 6 Colors+ Matte Varnish
  .50 ALOX PET - 3.5 PE - 4 Colors + Matte Varnish

material_spec format (from PDF body):
  .48 Matte PET / Adhesive / .48 MET PET / Adhesive / 3.0 LLDPE / 9045
  Soft Touch .48 Matte PET / Adhesive / .48 MET PET / 3.0 PE

Usage:
  SUPABASE_KEY=your_key python dazpak_material_parser.py --backfill
  python dazpak_material_parser.py --test
"""

import re
import os

# ═══════════════════════════════════════════════════════════════
# DAZPAK MATERIAL MAPPINGS
# ═══════════════════════════════════════════════════════════════

# Outer layer → Finish mapping
# The outer layer in Dazpak structures determines the laminate finish.
# Pattern: optional "Soft Touch" prefix + gauge + film type
DAZPAK_FINISH_RULES = [
    # Order matters — check most specific first
    (r"Soft\s*Touch", "Soft Touch Laminate"),
    (r"Gloss\s+PET", "Gloss Laminate"),
    (r"Matte\s+PET", "Matte Laminate"),
    # Plain .48 PET with Matte Varnish → Matte Laminate
    # (handled separately via varnish detection)
]

# Middle/base layer → Substrate mapping
# Keywords found in the second layer of Dazpak laminate structures
DAZPAK_SUBSTRATE_KEYWORDS = {
    "ALOX PET": "HB CLR PET",
    "ALOX": "HB CLR PET",
    "WHITE MET PET": "WHT MET PET",
    "White MET PET": "WHT MET PET",
    "WHT MET PET": "WHT MET PET",
    "HB CLR PET": "HB CLR PET",
    "CLR PET": "CLR PET",
    "EVOH": "HB CLR PET",
    "MET PET": "MET PET",  # Must be after WHITE MET PET
}


# ═══════════════════════════════════════════════════════════════
# FILENAME PARSER
# ═══════════════════════════════════════════════════════════════

def parse_dazpak_filename(filename: str) -> dict:
    """
    Parse substrate, finish, and num_colors from a Dazpak PDF filename.

    The material section sits between dimensions and colors:
      ...9 W x 6 H - Soft Touch .48 Matte PET - .48 MET PET - 3.0 PE - 5 Colors.pdf

    Returns:
      {"substrate": "MET PET", "finish": "Soft Touch Laminate", "num_colors": 5}
    """
    result = {"substrate": None, "finish": None, "num_colors": None}
    if not filename:
        return result

    # Extract num_colors from "N Colors" near the end
    colors_match = re.search(r"(\d+)\s*Colors?", filename, re.IGNORECASE)
    if colors_match:
        result["num_colors"] = int(colors_match.group(1))

    # Extract the material section from the filename.
    # Strategy: find the segment between dimensions (W x H) and Colors
    # Dimensions end pattern: "N W x N H" or "N H + N BG" or "N C.O."
    # Material starts after the last dimension marker + " - "
    mat_match = re.search(
        r'(?:\d+(?:\.\d+)?\s*(?:BG|B\.G\.?|H|C\.O\.))'  # end of dimensions
        r'\s*-\s*'                                         # separator
        r'(.+?)'                                           # material layers
        r'\s*-\s*\d+\s*Colors?',                           # start of colors
        filename,
        re.IGNORECASE,
    )
    if not mat_match:
        # Fallback: just search the whole filename for material keywords
        return _parse_material_from_text(filename, result)

    material_section = mat_match.group(1)

    # "Matte Varnish" appears AFTER "Colors" in the filename (e.g. "5 Colors + Matte Varnish.pdf")
    # Include it in the material section so _parse_material_from_text can detect it
    if re.search(r"Matte\s+Varnish", filename, re.IGNORECASE):
        material_section += " + Matte Varnish"

    return _parse_material_from_text(material_section, result)


def _parse_material_from_text(text: str, result: dict) -> dict:
    """
    Identify substrate and finish from a text string containing Dazpak material layers.
    Works on both filename material sections and material_spec strings.
    """
    if not text:
        return result

    text_upper = text.upper()

    # ── Finish ──
    # Check for Soft Touch first (can appear as prefix or inline)
    if re.search(r"SOFT\s*TOUCH", text_upper):
        result["finish"] = "Soft Touch Laminate"
    elif "GLOSS" in text_upper and "PET" in text_upper:
        result["finish"] = "Gloss Laminate"
    elif "MATTE" in text_upper and "PET" in text_upper:
        result["finish"] = "Matte Laminate"
    elif "MATTE VARNISH" in text_upper:
        # Plain PET with registered matte varnish coating
        result["finish"] = "Matte Laminate"

    # ── Substrate ──
    # ALOX PET, HB CLR PET, and EVOH are all "HB CLR PET" (high-barrier clear).
    # NOTE: For Dazpak, MET PET and WHT MET PET are the same — Dazpak's MET PET
    # is white-backed by default. Both map to "MET PET".
    if "ALOX" in text_upper:
        result["substrate"] = "HB CLR PET"
    elif re.search(r"WHITE?\s+MET\s+PET", text_upper):
        result["substrate"] = "MET PET"  # Dazpak WHT MET PET = MET PET
    elif "HB CLR PET" in text_upper or "EVOH" in text_upper:
        result["substrate"] = "HB CLR PET"
    elif "CLR PET" in text_upper:
        result["substrate"] = "CLR PET"
    elif "MET PET" in text_upper:
        # Must be after WHITE MET PET check
        result["substrate"] = "MET PET"

    # Special case: ".48 PET" or ".50 PET" without MET → CLR PET
    # These appear in newer quotes with Matte Varnish coating
    if result["substrate"] is None:
        if re.search(r"\.\d+\s+PET(?!\s*-\s*\.\d+\s+MET)", text):
            # Plain PET without a metallic middle layer
            result["substrate"] = "CLR PET"

    return result


# ═══════════════════════════════════════════════════════════════
# MATERIAL_SPEC PARSER (from PDF body text)
# ═══════════════════════════════════════════════════════════════

def parse_dazpak_material_spec(material_spec: str) -> dict:
    """
    Parse a Dazpak material_spec string into substrate and finish.

    Input format examples:
      ".48 Matte PET / Adhesive / .48 MET PET / Adhesive / 3.0 LLDPE / 9045"
      "Soft Touch .48 Matte PET / Adhesive / .48 White MET PET / 3.0 PE"
      ".50 ALOX PET / 3.5 PE"
      ".48 PET / .48 MET PET / 3.0 PE / Registered Matte Varnish"

    Returns:
      {"substrate": "MET PET", "finish": "Matte Laminate"}
    """
    result = {"substrate": None, "finish": None}
    if not material_spec:
        return result

    return _parse_material_from_text(material_spec, result)


# ═══════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════

def test_parser():
    """Verify parser against known filename and material_spec patterns."""

    # ── Filename tests ──
    filename_cases = [
        # (filename_fragment, expected_substrate, expected_finish, expected_colors)
        (
            "Q 14364 - FL-DL 1476 Schwazze Printed 3 Side Seal Pouch with CR Zipper - 9 W x 6 H - Soft Touch .48 Matte PET - .48 MET PET - 3.0 PE - 5 Colors.pdf",
            "MET PET", "Soft Touch Laminate", 5,
        ),
        (
            "Q 13402 - Anderson Crazy Candy Printed Laminated SUP with Zipper - 5.75 W x 9 H + 3 BG - .48 Matte PET - .48 MET PET - 3.0 LLDPE - 9 Colors.pdf",
            "MET PET", "Matte Laminate", 9,
        ),
        (
            "Q 14265 - Printed Laminated Pouch with CR Zipper - 4.5 W x 5 H + 2 BG - .48 PET - .48 MET PET - 3.0 PE - 5 Colors + Matte Varnish.pdf",
            "MET PET", "Matte Laminate", 5,
        ),
        (
            "Q 14039 - Schwazze Printed 3 Side Seal Pouch - 4 W x 7 H - Soft Touch .48 Matte PET - .48 MET PET - 3.0 PE - 4 Colors.pdf",
            "MET PET", "Soft Touch Laminate", 4,
        ),
        (
            "Q 13146C Rev1 - KYND Printed Laminated SUP with CR Zipper - 6 W x 8 H +2 BG - Soft Touch .48 Matte PET - .48 MET PET - 3.0 PE - 5 Colors.pdf",
            "MET PET", "Soft Touch Laminate", 5,
        ),
        (
            "Q 14361 - Printed Laminated Pouch with CR Zipper - 4.5 W x 5.5 H + 2 BG - .48 Soft Touch Matte PET - .48 MET PET - 3.0 PE - 5 Colors.pdf",
            "MET PET", "Soft Touch Laminate", 5,
        ),
        (
            "Q 14264 - Printed Laminated Pouch with CR Zipper - 4.5 W x 6 H + 2 BG - .48 PET - .48 MET PET - 3.0 PE - 5 Colors + Matte Varnish.pdf",
            "MET PET", "Matte Laminate", 5,
        ),
        (
            "Q 14500 - Printed Laminated SUP - 5 W x 5.25 H +3 BG - Soft Touch .48 Matte PET - .48 White MET PET - 3.0 PE - 4 Colors.pdf",
            "MET PET", "Soft Touch Laminate", 4,  # Dazpak WHT MET PET = MET PET
        ),
        (
            "Q 14600 - Printed 3 Side Seal Pouch - 3 W x 6 H - .50 ALOX PET - 3.5 PE - 4 Colors.pdf",
            "HB CLR PET", None, 4,
        ),
        (
            "Q 14700 - Printed Laminated Pouch - 4.5 W x 5 H + 2 BG - .50 ALOX PET - 3.5 LLDPE - 4 Colors + Matte Varnish.pdf",
            "HB CLR PET", "Matte Laminate", 4,
        ),
        (
            "Q 14800 - Printed SUP - 5 W x 5.25 H +3 BG - .50 ALOX PET - 3.5 PE - 5 Colors + Matte Varnish.pdf",
            "HB CLR PET", "Matte Laminate", 5,
        ),
        # Web width format (rollstock)
        (
            "Q 14100 - Rollstock - 12.0 Web x 3.75 C.O. - .56 Matte PET - .48 MET PET - 3.0 LLDPE - 7 Colors.pdf",
            "MET PET", "Matte Laminate", 7,
        ),
        # Plain .48 PET 2-layer (no MET PET middle) with Matte Varnish
        (
            "Q 14900 - Printed Pouch - 6 W x 5.5 H + 2.5 BG - .48 PET - 3.5 PE - 5 Colors + Matte Varnish.pdf",
            "CLR PET", "Matte Laminate", 5,
        ),
    ]

    print("── Filename Parser Tests ──")
    fn_passed = 0
    for i, (fn, exp_sub, exp_fin, exp_colors) in enumerate(filename_cases):
        result = parse_dazpak_filename(fn)
        ok_sub = result["substrate"] == exp_sub
        ok_fin = result["finish"] == exp_fin
        ok_col = result["num_colors"] == exp_colors

        if ok_sub and ok_fin and ok_col:
            fn_passed += 1
            print(f"  ✓ Test {i+1}: {result['substrate']}, {result['finish']}, {result['num_colors']} colors")
        else:
            print(f"  ✗ Test {i+1} FAILED:")
            print(f"    Input: ...{fn[-80:]}")
            if not ok_sub:
                print(f"    Substrate: got={result['substrate']} expected={exp_sub}")
            if not ok_fin:
                print(f"    Finish:    got={result['finish']} expected={exp_fin}")
            if not ok_col:
                print(f"    Colors:    got={result['num_colors']} expected={exp_colors}")

    print(f"\n  {fn_passed}/{len(filename_cases)} passed")

    # ── Material spec tests ──
    spec_cases = [
        (
            ".48 Matte PET / Adhesive / .48 MET PET / Adhesive / 3.0 LLDPE / 9045",
            "MET PET", "Matte Laminate",
        ),
        (
            "Soft Touch .48 Matte PET / Adhesive / .48 MET PET / 3.0 PE",
            "MET PET", "Soft Touch Laminate",
        ),
        (
            ".48 Soft Touch Matte PET / Adhesive / .48 White MET PET / 3.0 PE",
            "MET PET", "Soft Touch Laminate",  # Dazpak WHT MET PET = MET PET
        ),
        (
            ".50 ALOX PET / 3.5 PE",
            "HB CLR PET", None,
        ),
        (
            ".48 PET / .48 MET PET / 3.0 PE / Registered Matte Varnish",
            "MET PET", "Matte Laminate",
        ),
        (
            ".48 PET / 3.5 PE / Registered Matte Varnish",
            "CLR PET", "Matte Laminate",
        ),
        (
            ".56 Matte PET / Adhesive / .48 MET PET / 3.0 LLDPE",
            "MET PET", "Matte Laminate",
        ),
        (
            "Soft Touch .48 Matte PET / Adhesive / .48 White MET PET / Adhesive / 3.0 PE",
            "MET PET", "Soft Touch Laminate",  # Dazpak WHT MET PET = MET PET
        ),
    ]

    print("\n── Material Spec Parser Tests ──")
    ms_passed = 0
    for i, (spec, exp_sub, exp_fin) in enumerate(spec_cases):
        result = parse_dazpak_material_spec(spec)
        ok_sub = result["substrate"] == exp_sub
        ok_fin = result["finish"] == exp_fin

        if ok_sub and ok_fin:
            ms_passed += 1
            print(f"  ✓ Test {i+1}: {result['substrate']}, {result['finish']}")
        else:
            print(f"  ✗ Test {i+1} FAILED:")
            print(f"    Input: {spec[:60]}...")
            if not ok_sub:
                print(f"    Substrate: got={result['substrate']} expected={exp_sub}")
            if not ok_fin:
                print(f"    Finish:    got={result['finish']} expected={exp_fin}")

    print(f"\n  {ms_passed}/{len(spec_cases)} passed")
    return fn_passed + ms_passed, len(filename_cases) + len(spec_cases)


# ═══════════════════════════════════════════════════════════════
# BACKFILL SCRIPT
# ═══════════════════════════════════════════════════════════════

def backfill_dazpak_materials():
    """
    Backfill substrate, finish, and num_colors for existing Dazpak quotes.

    Strategy 1: Parse material_spec on rows that have it (26 rows).
    Strategy 2: List Drive PDFs, parse filenames, match to DB rows by
                FL number or (width, height, gusset) to fill the 376 sparse rows.
    """
    try:
        import certifi
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except ImportError:
        pass

    from supabase import create_client

    SUPABASE_URL = "https://dernxirzvawjmdxzxefl.supabase.co"
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

    if not SUPABASE_KEY:
        SUPABASE_KEY = input("Enter SUPABASE_KEY: ").strip()

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("=" * 60)
    print("DAZPAK MATERIAL SPEC BACKFILL")
    print("=" * 60)

    # ── Strategy 1: Parse existing material_spec values ──
    print("\n── Strategy 1: Parse material_spec → substrate/finish ──")

    offset = 0
    batch_size = 1000
    all_quotes = []
    while True:
        resp = (
            client.table("quotes")
            .select("id,fl_number,material_spec,substrate,finish,num_colors,source_file,width,height,gusset")
            .eq("vendor", "dazpak")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not resp.data:
            break
        all_quotes.extend(resp.data)
        if len(resp.data) < batch_size:
            break
        offset += batch_size

    print(f"  Total Dazpak quotes: {len(all_quotes)}")

    updates_from_spec = []
    already_set = 0
    no_material = 0

    for q in all_quotes:
        if q.get("substrate") and q.get("finish"):
            already_set += 1
            continue

        mat_spec = q.get("material_spec")
        if not mat_spec:
            no_material += 1
            continue

        parsed = parse_dazpak_material_spec(mat_spec)
        update_data = {}
        if parsed["substrate"] and not q.get("substrate"):
            update_data["substrate"] = parsed["substrate"]
        if parsed["finish"] and not q.get("finish"):
            update_data["finish"] = parsed["finish"]

        if update_data:
            updates_from_spec.append((q["id"], update_data, q.get("fl_number", "?")))

    print(f"  Already populated:   {already_set}")
    print(f"  No material_spec:    {no_material}")
    print(f"  Parseable from spec: {len(updates_from_spec)}")

    # ── Strategy 2: Parse Drive PDF filenames ──
    print("\n── Strategy 2: Parse Drive PDF filenames → substrate/finish ──")

    drive_service = None
    try:
        import json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            creds_info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(
                creds_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
            )
            drive_service = build("drive", "v3", credentials=creds)
        else:
            creds_path = os.environ.get("GOOGLE_CREDENTIALS")
            if creds_path and os.path.isfile(creds_path):
                creds = service_account.Credentials.from_service_account_file(
                    creds_path, scopes=["https://www.googleapis.com/auth/drive.readonly"]
                )
                drive_service = build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"  Could not connect to Google Drive: {e}")

    updates_from_filename = []

    if drive_service:
        # Import folder ID from settings
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from config.settings import DAZPAK_FOLDER_ID
        except ImportError:
            DAZPAK_FOLDER_ID = os.environ.get("DAZPAK_FOLDER_ID", "")

        if DAZPAK_FOLDER_ID:
            # List all PDFs in Drive folder
            pdf_files = []
            page_token = None
            while True:
                response = drive_service.files().list(
                    q=f"'{DAZPAK_FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false",
                    spaces="drive",
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token,
                    pageSize=100,
                ).execute()
                pdf_files.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            print(f"  Found {len(pdf_files)} PDFs in Drive")

            # Build lookup: (width, height, gusset) → [quote_ids]
            # For rows that still need substrate/finish
            needs_update = [
                q for q in all_quotes
                if not q.get("substrate")
                and q["id"] not in {u[0] for u in updates_from_spec}
            ]

            dim_lookup = {}
            fl_lookup = {}
            for q in needs_update:
                w = round(float(q.get("width", 0)), 2)
                h = round(float(q.get("height", 0)), 2)
                g = round(float(q.get("gusset", 0) or 0), 2)
                dim_key = (w, h, g)
                dim_lookup.setdefault(dim_key, []).append(q)
                fl = (q.get("fl_number") or "").strip().upper()
                if fl:
                    fl_lookup.setdefault(fl, []).append(q)

            # Parse each filename and try to match
            for pdf_file in pdf_files:
                fname = pdf_file["name"]
                parsed = parse_dazpak_filename(fname)

                if not parsed["substrate"] and not parsed["finish"]:
                    continue

                # Extract FL number from filename
                fl_match = re.search(r"(FL-[A-Z]{2}-?\d{3,5})", fname, re.IGNORECASE)
                fl_from_file = fl_match.group(1).upper().replace(" ", "-") if fl_match else None

                # Extract dimensions from filename
                dim_match = re.search(
                    r'([\d.]+)\s*W\s*[Xx×]\s*([\d.]+)\s*H'
                    r'(?:\s*[+]\s*([\d.]+)\s*(?:BG|B\.G\.?))?',
                    fname, re.IGNORECASE,
                )

                matched_quotes = []

                # Try FL number match first
                if fl_from_file and fl_from_file in fl_lookup:
                    matched_quotes = fl_lookup[fl_from_file]
                # Fall back to dimension match
                elif dim_match:
                    w = round(float(dim_match.group(1)), 2)
                    h = round(float(dim_match.group(2)), 2)
                    g = round(float(dim_match.group(3)), 2) if dim_match.group(3) else 0.0
                    dim_key = (w, h, g)
                    if dim_key in dim_lookup:
                        matched_quotes = dim_lookup[dim_key]

                for q in matched_quotes:
                    update_data = {}
                    if parsed["substrate"] and not q.get("substrate"):
                        update_data["substrate"] = parsed["substrate"]
                    if parsed["finish"] and not q.get("finish"):
                        update_data["finish"] = parsed["finish"]
                    if parsed["num_colors"] and not q.get("num_colors"):
                        update_data["num_colors"] = parsed["num_colors"]
                    if not q.get("source_file"):
                        update_data["source_file"] = fname

                    if update_data:
                        # Avoid duplicate updates
                        existing_ids = {u[0] for u in updates_from_filename}
                        if q["id"] not in existing_ids:
                            updates_from_filename.append(
                                (q["id"], update_data, q.get("fl_number") or f"{q['width']}x{q['height']}")
                            )

            print(f"  Matched from filenames: {len(updates_from_filename)}")
        else:
            print("  DAZPAK_FOLDER_ID not set, skipping Drive scan")
    else:
        print("  No Google Drive credentials, skipping Drive scan")

    # ── Combine and execute ──
    all_updates = updates_from_spec + updates_from_filename
    print(f"\n── Total updates: {len(all_updates)} ──")

    if not all_updates:
        print("\nNothing to update!")
        return

    # Preview
    print("\n── Preview (first 15) ──")
    for qid, data, fl in all_updates[:15]:
        print(
            f"  {str(fl):20s}  → substrate={data.get('substrate', '-'):15s}  "
            f"finish={data.get('finish', '-'):25s}  "
            f"colors={data.get('num_colors', '-')}"
        )

    # Confirm
    confirm = input(f"\nUpdate {len(all_updates)} rows in Supabase? (y/n): ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    # Execute
    print("\nUpdating...")
    success = 0
    errors = 0
    for qid, data, fl in all_updates:
        try:
            client.table("quotes").update(data).eq("id", qid).execute()
            success += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ERROR updating {fl}: {e}")

    print(f"\n  Updated: {success}")
    print(f"  Errors:  {errors}")

    # Distribution summary
    print("\n── Distribution of parsed values ──")
    substrate_counts = {}
    finish_counts = {}
    for _, data, _ in all_updates:
        s = data.get("substrate", "(unchanged)")
        f = data.get("finish", "(unchanged)")
        substrate_counts[s] = substrate_counts.get(s, 0) + 1
        finish_counts[f] = finish_counts.get(f, 0) + 1

    print("  Substrates:")
    for k, v in sorted(substrate_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:20s}  {v}")
    print("  Finishes:")
    for k, v in sorted(finish_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:25s}  {v}")


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        passed, total = test_parser()
        sys.exit(0 if passed == total else 1)
    elif "--backfill" in sys.argv:
        backfill_dazpak_materials()
    else:
        print("Usage:")
        print("  python dazpak_material_parser.py --test      Run parser tests")
        print("  python dazpak_material_parser.py --backfill  Backfill Supabase")
        print()
        passed, total = test_parser()
        if passed == total:
            print()
            if input("Run backfill? (y/n): ").strip().lower() == "y":
                backfill_dazpak_materials()
