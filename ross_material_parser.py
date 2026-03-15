"""
Ross Material Spec Parser & Backfill
=====================================
Two components:

1. parse_ross_material_spec() — Add to pdf_extraction.py to parse
   material_spec into substrate, finish, and embellishment fields.

2. backfill_ross_materials() — One-time script to update existing
   Ross quotes in Supabase with parsed substrate/finish.

Usage:
  # Backfill existing data:
  SUPABASE_KEY=your_key python ross_material_parser.py

  # Or import the parser in pdf_extraction.py:
  from ross_material_parser import parse_ross_material_spec
"""

import re
import os

# ═══════════════════════════════════════════════════════════════
# ROSS STOCK NUMBER → CATEGORY MAPPINGS
# ═══════════════════════════════════════════════════════════════

# Finish (laminate — first stock in material_spec)
ROSS_FINISH_MAP = {
    "3904": "Matte Laminate",       # 2700 Series Platinum Poly Matte Thermal Laminate
    "3905": "Soft Touch Laminate",  # 1.5 mil Karess Thermal Tactile Over Laminate
    "3907": "Gloss Laminate",       # 2500 Series Platinum Poly Gloss Thermal Lamination
    "3912": "Holographic",          # 1.4 mil Rainbow Holografik Thermal Lamination
}

# Keyword fallback for finish (when stock# not parseable)
ROSS_FINISH_KEYWORDS = {
    "MATTE": "Matte Laminate",
    "KARESS": "Soft Touch Laminate",
    "TACTILE": "Soft Touch Laminate",
    "GLOSS": "Gloss Laminate",
    "HOLOGRAFIK": "Holographic",
    "HOLOGRAPHIC": "Holographic",
}

# Substrate (base film — second stock in material_spec)
ROSS_SUBSTRATE_MAP = {
    "5001": "WHT MET PET",  # 48PET/10#WLDPE/FOIL — current white, being replaced by 5011
    "5005": "MET PET",      # 4MIL MET PET SUP
    "5006": "WHT MET PET",  # 2ML Classic White PET Snack Web
    "5009": "WHT MET PET",  # 3.5 MIL WHITE MET PET / CLEAR PE — previous white stock
    "5010": "MET PET",      # 3.5 MIL MET PET / CLEAR PE FILM
    "5011": "WHT MET PET",  # 3 MIL WHITE MET PET / 2.5 MIL LDPE — current white stock
    "5012": "MET PET",      # 48GA MET PET / 2.5 MIL LDPE RS
    "5014": "WHT MET PET",  # 3.9 MIL WHITE COSMETIC WEB
    "5015": "MET PET",      # 3.9 MIL SILVER MET PET
    "5101": "MET PET",      # 48PET/10#LDPE/FOIL — not currently used
    "5309": "HB CLR PET",   # 3mil CLEAR EVOH LDPE (SUP) — high barrier clear
    "5312": "CLR PET",      # 46ga PVDC PET / 3.0mil CLEAR LDPE
    "5313": "HB CLR PET",   # .50 ALOX PET / 3.0 LLDPE → HB CLR PET (high-barrier clear)
    "5408": "WHT MET PET",  # EZTEAR WHITE LAMINATED POUCH STRUCTURE
    "5701": "CLR PET",      # CLEAR STAND UP POUCH
    "5999": None,           # CUSTOMER SUPPLIED MATERIAL — unknown
}

# Keyword fallback for substrate
ROSS_SUBSTRATE_KEYWORDS = {
    "ALOX": "HB CLR PET",
    "EVOH": "HB CLR PET",
    "WHITE MET PET": "WHT MET PET",
    "WHITE COSMETIC": "WHT MET PET",
    "CLASSIC WHITE": "WHT MET PET",
    "EZTEAR WHITE": "WHT MET PET",
    "SILVER MET PET": "MET PET",
    "MET PET": "MET PET",
    "CLEAR STAND UP": "CLR PET",
    "PVDC PET": "CLR PET",
    "CLEAR EVOH": "HB CLR PET",
}

# Embellishment (optional 3rd stock — 8xxx series)
ROSS_EMBELLISHMENT_MAP = {
    "8304": "Cold Foil",    # Bright Blue Cold Foil
    "8308": "Cold Foil",    # GD202 Sunset Gold Cold Foil
    "8409": "Holographic",  # LS-011 Rainbow Holographic
}


# ═══════════════════════════════════════════════════════════════
# PARSER
# ═══════════════════════════════════════════════════════════════

def parse_ross_material_spec(material_spec: str) -> dict:
    """
    Parse a Ross material_spec string into substrate, finish, embellishment.
    
    Input format examples:
      "Stock# 3904 2700 SERIES PLATINUM POLY MATTE THERMAL LAMINATE / Stock# 5010 3.5 MIL MET PET / CLEAR PE FILM"
      "Stock#39051.5milKARESSTHERMALTACTILEOVERLAMINATE / Stock#510148PET/10#LDPE/FOIL/10#HB-PE/1.5METALLOCENE"
      "Stock#53093milCLEAREVOHLDPE(SUP)"  (no laminate)
    
    Returns:
      {"substrate": "MET PET", "finish": "Matte", "embellishment": None}
    """
    if not material_spec:
        return {"substrate": None, "finish": None, "embellishment": None}
    
    result = {"substrate": None, "finish": None, "embellishment": None}
    
    # Split on " / " (with spaces) to get stock segments
    # Handle both spaced and unspaced formats
    segments = re.split(r'\s*/\s*(?=Stock)', material_spec)
    
    # Extract stock numbers from each segment
    stocks = []
    for seg in segments:
        # Match "Stock# NNNN" or "Stock#NNNN" 
        m = re.match(r'Stock#\s*(\d{4})', seg.strip())
        if m:
            stocks.append({
                "number": m.group(1),
                "description": seg.strip(),
            })
    
    if not stocks:
        # Try keyword fallback on entire string
        upper = material_spec.upper()
        for kw, val in ROSS_FINISH_KEYWORDS.items():
            if kw in upper:
                result["finish"] = val
                break
        for kw, val in ROSS_SUBSTRATE_KEYWORDS.items():
            if kw in upper:
                result["substrate"] = val
                break
        return result
    
    # Categorize each stock
    for stock in stocks:
        num = stock["number"]
        desc_upper = stock["description"].upper()
        
        # Check if it's a laminate/finish (3xxx series)
        if num.startswith("3") and num in ROSS_FINISH_MAP:
            result["finish"] = ROSS_FINISH_MAP[num]
        
        # Check if it's a substrate (5xxx series)  
        elif num.startswith("5") and num in ROSS_SUBSTRATE_MAP:
            result["substrate"] = ROSS_SUBSTRATE_MAP[num]
        
        # Check if it's an embellishment (8xxx series)
        elif num.startswith("8") and num in ROSS_EMBELLISHMENT_MAP:
            result["embellishment"] = ROSS_EMBELLISHMENT_MAP[num]
        
        # Unknown stock — try keyword matching
        else:
            # Check finish keywords
            for kw, val in ROSS_FINISH_KEYWORDS.items():
                if kw in desc_upper:
                    if not result["finish"]:
                        result["finish"] = val
                    break
            
            # Check substrate keywords
            for kw, val in ROSS_SUBSTRATE_KEYWORDS.items():
                if kw in desc_upper:
                    if not result["substrate"]:
                        result["substrate"] = val
                    break
    
    # If no laminate found, finish = None (unlaminated)
    # Substrate should default to MET PET if nothing matched
    if result["substrate"] is None and stocks:
        result["substrate"] = "MET PET"  # safe default
    
    return result


# ═══════════════════════════════════════════════════════════════
# CODE TO ADD TO pdf_extraction.py (extract_ross_pdf function)
# ═══════════════════════════════════════════════════════════════

PDF_EXTRACTION_PATCH = '''
# ──────────────────────────────────────────────────────────────
# ADD THIS after the "Materials" extraction block (around line 250)
# in extract_ross_pdf(), right after:
#     result["material_spec"] = m.group(1).strip().replace('\\n', ' / ')
# ──────────────────────────────────────────────────────────────

    # Parse material_spec into substrate + finish
    if result.get("material_spec"):
        from ross_material_parser import parse_ross_material_spec
        mat = parse_ross_material_spec(result["material_spec"])
        result["substrate"] = mat["substrate"]
        result["finish"] = mat["finish"]
        if mat.get("embellishment"):
            result["embellishment"] = mat["embellishment"]
'''


# ═══════════════════════════════════════════════════════════════
# BACKFILL SCRIPT
# ═══════════════════════════════════════════════════════════════

def backfill_ross_materials():
    """
    One-time backfill: read all Ross quotes with material_spec,
    parse into substrate/finish, update in Supabase.
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
    print("ROSS MATERIAL SPEC BACKFILL")
    print("=" * 60)
    
    # Fetch all Ross quotes
    print("\nFetching Ross quotes...")
    resp = client.table("quotes").select(
        "id,fl_number,material_spec,substrate,finish,embellishment"
    ).eq("vendor", "ross").execute()
    
    quotes = resp.data
    print(f"  Total Ross quotes: {len(quotes)}")
    
    # Parse and collect updates
    updates = []
    already_set = 0
    no_material = 0
    parsed = 0
    
    for q in quotes:
        mat_spec = q.get("material_spec")
        
        if not mat_spec:
            no_material += 1
            continue
        
        # Skip if already populated
        if q.get("substrate") and q.get("finish"):
            already_set += 1
            continue
        
        parsed_mat = parse_ross_material_spec(mat_spec)
        
        update_data = {}
        if parsed_mat["substrate"] and not q.get("substrate"):
            update_data["substrate"] = parsed_mat["substrate"]
        if parsed_mat["finish"] and not q.get("finish"):
            update_data["finish"] = parsed_mat["finish"]
        if parsed_mat.get("embellishment") and not q.get("embellishment"):
            update_data["embellishment"] = parsed_mat["embellishment"]
        
        if update_data:
            updates.append((q["id"], update_data, q.get("fl_number", "?")))
            parsed += 1
    
    print(f"  Already populated: {already_set}")
    print(f"  No material_spec:  {no_material}")
    print(f"  To update:         {parsed}")
    
    if not updates:
        print("\nNothing to update!")
        return
    
    # Show preview
    print(f"\n── Preview (first 10) ──")
    for qid, data, fl in updates[:10]:
        print(f"  {fl:15s}  → substrate={data.get('substrate', '-')}  "
              f"finish={data.get('finish', '-')}  "
              f"embellishment={data.get('embellishment', '-')}")
    
    # Confirm
    confirm = input(f"\nUpdate {len(updates)} rows in Supabase? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Aborted.")
        return
    
    # Execute updates
    print("\nUpdating...")
    success = 0
    errors = 0
    for qid, data, fl in updates:
        try:
            client.table("quotes").update(data).eq("id", qid).execute()
            success += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ERROR updating {fl}: {e}")
    
    print(f"\n  Updated: {success}")
    print(f"  Errors:  {errors}")
    
    # Summary of what was set
    print(f"\n── Distribution of parsed values ──")
    substrate_counts = {}
    finish_counts = {}
    for _, data, _ in updates:
        s = data.get("substrate", "None")
        f = data.get("finish", "None")
        substrate_counts[s] = substrate_counts.get(s, 0) + 1
        finish_counts[f] = finish_counts.get(f, 0) + 1
    
    print("  Substrates:")
    for k, v in sorted(substrate_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:20s}  {v}")
    print("  Finishes:")
    for k, v in sorted(finish_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:20s}  {v}")


# ═══════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════

def test_parser():
    """Verify parser against known material specs."""
    test_cases = [
        # (material_spec, expected_substrate, expected_finish, expected_embellishment)
        (
            "Stock# 3904 2700 SERIES PLATINUM POLY MATTE THERMAL LAMINATE / Stock# 5010 3.5 MIL MET PET / CLEAR PE FILM",
            "MET PET", "Matte Laminate", None
        ),
        (
            "Stock# 3905 1.5 mil KARESS THERMAL TACTILE OVER LAMINATE / Stock# 5309 3mil CLEAR EVOH LDPE (SUP)",
            "HB CLR PET", "Soft Touch Laminate", None
        ),
        (
            "Stock# 3907 2500 SERIES PLATINUM POLY GLOSS THERMAL LAMINATION / Stock# 5001 48PET/10#WLDPE/FOIL/10#HB-PE/1.5 METALLOCENE",
            "WHT MET PET", "Gloss Laminate", None
        ),
        (
            "Stock#39051.5milKARESSTHERMALTACTILEOVERLAMINATE / Stock#50143.9MILWHITECOSMETICWEB",
            "WHT MET PET", "Soft Touch Laminate", None
        ),
        (
            "Stock#39042700SERIESPLATINUMPOLYMATTETHERMALLAMINATE / Stock#510148PET/10#LDPE/FOIL/10#HB-PE/1.5METALLOCENE",
            "MET PET", "Matte Laminate", None
        ),
        (
            "Stock#39072500SERIESPLATINUMPOLYGLOSSTHERMALLAMINATION / Stock#500148PET/10#WLDPE/FOIL/10#HB-PE/1.5METALLOCENE / Stock#8308GD202SUNSETGOLDCOLDFOIL",
            "WHT MET PET", "Gloss Laminate", "Cold Foil"
        ),
        (
            "Stock#53093milCLEAREVOHLDPE(SUP)",
            "HB CLR PET", None, None
        ),
        (
            "Stock#39051.5milKARESSTHERMALTACTILEOVERLAMINATE / Stock#531346gaPVDCPET/3.0milCLEARLDPE",
            "HB CLR PET", "Soft Touch Laminate", None  # 5313 = ALOX PET → HB CLR PET
        ),
        (
            "Stock# 3905 1.5 mil KARESS THERMAL TACTILE OVER LAMINATE / Stock# 5313 .50 ALOX PET / 3.0 LLDPE",
            "HB CLR PET", "Soft Touch Laminate", None
        ),
        (
            "Stock#39121.4MILRAINBOWHOLOGRAFIKTHERMALLAMINATION / Stock#53093milCLEAREVOHLDPE(SUP)",
            "HB CLR PET", "Holographic", None
        ),
    ]
    
    print("── Parser Tests ──")
    passed = 0
    for i, (spec, exp_sub, exp_fin, exp_emb) in enumerate(test_cases):
        result = parse_ross_material_spec(spec)
        
        ok_sub = result["substrate"] == exp_sub
        ok_fin = result["finish"] == exp_fin
        ok_emb = result.get("embellishment") == exp_emb
        
        if ok_sub and ok_fin and ok_emb:
            passed += 1
            print(f"  ✓ Test {i+1}: {result['substrate']}, {result['finish']}, {result.get('embellishment')}")
        else:
            print(f"  ✗ Test {i+1} FAILED:")
            print(f"    Input:    {spec[:80]}...")
            if not ok_sub: print(f"    Substrate: got={result['substrate']} expected={exp_sub}")
            if not ok_fin: print(f"    Finish:    got={result['finish']} expected={exp_fin}")
            if not ok_emb: print(f"    Embellish: got={result.get('embellishment')} expected={exp_emb}")
    
    print(f"\n  {passed}/{len(test_cases)} passed")


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        test_parser()
    elif "--backfill" in sys.argv:
        backfill_ross_materials()
    else:
        print("Usage:")
        print("  python ross_material_parser.py --test      Run parser tests")
        print("  python ross_material_parser.py --backfill  Backfill Supabase")
        print()
        # Default: run tests then ask about backfill
        test_parser()
        print()
        if input("Run backfill? (y/n): ").strip().lower() == "y":
            backfill_ross_materials()
