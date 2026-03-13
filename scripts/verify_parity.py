#!/usr/bin/env python3
"""
Verify pricing parity between Streamlit (internal) and API (customer-facing).

Builds specs both ways and asserts they produce identical model inputs and prices.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.schemas.quote_request import InstantQuoteRequest
from api.services.prediction_service import _build_internal_specs, get_predictor

# ── Test Cases ────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Stand Up Pouch, MET PET, Matte, CR Zipper",
        "streamlit_specs": {
            "width": 4.5,
            "height": 6.0,
            "gusset": 2.0,
            "substrate": "MET_PET",
            "finish": "Matte Laminate",
            "seal_type": "Stand Up Pouch",
            "gusset_type": "Plow Bottom",
            "fill_style": "Top",
            "zipper": "CR Zipper",
            "tear_notch": "None",
            "hole_punch": "None",
            "corner_treatment": "Straight",
            "embellishment": "None",
        },
        "api_input": {
            "width": 4.5,
            "height": 6.0,
            "gusset": 2.0,
            "substrate": "Metallic",
            "finish": "Matte",
            "seal_type": "Stand Up Pouch",
            "gusset_type": "Plow Bottom",
            "fill_style": "Top",
            "zipper": "Child-Resistant",
            "tear_notch": "None",
            "hole_punch": "None",
            "corners": "Straight",
            "embellishment": "None",
            "quantities": [5000, 10000, 25000],
            "lead_id": "test-verify",
        },
    },
    {
        "name": "3 Side Seal, Top Fill, Plow Bottom gusset (the bug case)",
        "streamlit_specs": {
            "width": 5.0,
            "height": 8.0,
            "gusset": 0.0,
            "substrate": "CLR_PET",
            "finish": "Gloss Laminate",
            "seal_type": "3 Side Seal - Top Fill",
            "gusset_type": "Plow Bottom",
            "fill_style": "Top",
            "zipper": "No Zipper",
            "tear_notch": "Standard",
            "hole_punch": "None",
            "corner_treatment": "Rounded",
            "embellishment": "None",
        },
        "api_input": {
            "width": 5.0,
            "height": 8.0,
            "gusset": 0.0,
            "substrate": "Clear",
            "finish": "Gloss",
            "seal_type": "3 Side Seal",
            "gusset_type": "Plow Bottom",
            "fill_style": "Top",
            "zipper": "None",
            "tear_notch": "Standard",
            "hole_punch": "None",
            "corners": "Rounded",
            "embellishment": "None",
            "quantities": [5000, 10000, 25000],
            "lead_id": "test-verify",
        },
    },
    {
        "name": "3 Side Seal, Bottom Fill, No gusset",
        "streamlit_specs": {
            "width": 3.5,
            "height": 5.0,
            "gusset": 0.0,
            "substrate": "WHT_MET_PET",
            "finish": "Soft Touch Laminate",
            "seal_type": "3 Side Seal - Bottom Fill",
            "gusset_type": "None",
            "fill_style": "Bottom",
            "zipper": "Non-CR Zipper",
            "tear_notch": "None",
            "hole_punch": "Round",
            "corner_treatment": "Straight",
            "embellishment": "Foil",
        },
        "api_input": {
            "width": 3.5,
            "height": 5.0,
            "gusset": 0.0,
            "substrate": "White Metallic",
            "finish": "Soft Touch",
            "seal_type": "3 Side Seal",
            "gusset_type": "None",
            "fill_style": "Bottom",
            "zipper": "Standard",
            "tear_notch": "None",
            "hole_punch": "Round",
            "corners": "Straight",
            "embellishment": "Foil",
            "quantities": [5000, 10000, 25000],
            "lead_id": "test-verify",
        },
    },
    {
        "name": "SUP, High Barrier, K Seal gusset",
        "streamlit_specs": {
            "width": 6.0,
            "height": 9.5,
            "gusset": 3.5,
            "substrate": "HB_CLR_PET",
            "finish": "None",
            "seal_type": "Stand Up Pouch",
            "gusset_type": "K Seal & Skirt Seal",
            "fill_style": "Top",
            "zipper": "CR Zipper",
            "tear_notch": "Standard",
            "hole_punch": "Euro",
            "corner_treatment": "Rounded",
            "embellishment": "Spot UV",
        },
        "api_input": {
            "width": 6.0,
            "height": 9.5,
            "gusset": 3.5,
            "substrate": "High Barrier",
            "finish": "None",
            "seal_type": "Stand Up Pouch",
            "gusset_type": "K Seal",
            "fill_style": "Top",
            "zipper": "Child-Resistant",
            "tear_notch": "Standard",
            "hole_punch": "Euro Slot",
            "corners": "Rounded",
            "embellishment": "Spot UV",
            "quantities": [5000, 10000, 25000],
            "lead_id": "test-verify",
        },
    },
]


def run_tests():
    passed = 0
    failed = 0

    for tc in TEST_CASES:
        name = tc["name"]
        streamlit_specs = tc["streamlit_specs"]
        api_input = tc["api_input"]

        # Build specs via API path
        req = InstantQuoteRequest(**api_input)
        api_specs = _build_internal_specs(req)

        # Compare specs
        mismatches = []
        for key in streamlit_specs:
            api_val = api_specs.get(key)
            st_val = streamlit_specs[key]
            if api_val != st_val:
                mismatches.append(f"  {key}: streamlit={st_val!r} vs api={api_val!r}")

        if mismatches:
            print(f"FAIL: {name}")
            print("\n".join(mismatches))
            failed += 1
            continue

        # Compare predictions
        predictor = get_predictor()
        quantities = sorted(api_input["quantities"])

        st_digital_specs = {**streamlit_specs, "print_method": "Digital"}
        api_digital_specs = {**api_specs, "print_method": "Digital"}

        st_result = predictor.predict(st_digital_specs, quantities)
        api_result = predictor.predict(api_digital_specs, quantities)

        st_prices = [p.get("unit_price") for p in st_result.get("predictions", [])]
        api_prices = [p.get("unit_price") for p in api_result.get("predictions", [])]

        if st_prices != api_prices:
            print(f"FAIL: {name} (price mismatch)")
            print(f"  Streamlit prices: {st_prices}")
            print(f"  API prices:       {api_prices}")
            failed += 1
        else:
            print(f"PASS: {name}")
            passed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(TEST_CASES)}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
