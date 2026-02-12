"""
Input validation for quote specifications.
"""
from typing import Optional


def validate_dimensions(width: float, height: float, gusset: float = 0) -> list[str]:
    """Validate bag dimensions. Returns list of error messages (empty if valid)."""
    errors = []
    if width <= 0 or width > 30:
        errors.append(f"Width must be between 0\" and 30\" (got {width}\")")
    if height <= 0 or height > 30:
        errors.append(f"Height must be between 0\" and 30\" (got {height}\")")
    if gusset < 0 or gusset > 10:
        errors.append(f"Gusset must be between 0\" and 10\" (got {gusset}\")")
    return errors


def validate_quantities(quantities: list[int]) -> list[str]:
    """Validate quantity tiers."""
    errors = []
    if not quantities:
        errors.append("At least one quantity tier is required")
        return errors
    for i, q in enumerate(quantities):
        if q <= 0:
            errors.append(f"Tier {i+1}: quantity must be positive (got {q})")
        if q > 10_000_000:
            errors.append(f"Tier {i+1}: quantity {q:,} seems unreasonably high")
    # Check ascending order
    for i in range(1, len(quantities)):
        if quantities[i] <= quantities[i - 1]:
            errors.append("Quantity tiers should be in ascending order")
            break
    return errors


def validate_all(specs: dict, quantities: list[int]) -> list[str]:
    """
    Run all validations on user input.
    Returns list of error messages (empty = valid).
    """
    errors = []

    # Dimensions
    width = specs.get("width", 0)
    height = specs.get("height", 0)
    gusset = specs.get("gusset", 0)
    errors.extend(validate_dimensions(width, height, gusset))

    # Quantities
    errors.extend(validate_quantities(quantities))

    # Substrate required
    if not specs.get("substrate"):
        errors.append("Substrate type is required")

    return errors
