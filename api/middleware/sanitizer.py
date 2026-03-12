"""
Response sanitizer middleware.

Recursively strips forbidden keys and vendor/internal strings from
any response data before it reaches the customer. This is the last
line of defense to ensure no internal data leaks through the API.
"""
from typing import Any

# Keys that must NEVER appear in customer-facing responses
FORBIDDEN_KEYS = {
    "vendor",
    "vendor_name",
    "unit_cost",
    "cost",
    "cost_factors",
    "model_metrics",
    "component_costs",
    "margin",
    "margin_pct",
    "margin_multiplier",
    "routing_reason",
    "print_width",
    "bag_area",
    "lower_bound",
    "upper_bound",
    "confidence_range",
    "error",
    "warnings",
    "lead_times",
}

# Substrings that must never appear in string values (case-insensitive)
FORBIDDEN_STRINGS = [
    "dazpak",
    "ross",
    "tedpack",
    "hp 6900",
    "hp6900",
    "hp200k",
    "internal",
    "gonderflex",
    "label traxx",
    "cerm",
    "gravure",
    "msi",
    "spoilage",
]


def sanitize_response(data: Any) -> Any:
    """
    Recursively sanitize a response object.

    1. Removes any key in FORBIDDEN_KEYS from dicts
    2. Checks all string values -- if any contain a FORBIDDEN_STRING
       (case-insensitive), replaces the value with "[redacted]"
    3. Recurses into nested dicts and lists
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Skip forbidden keys entirely
            if key in FORBIDDEN_KEYS:
                continue
            sanitized[key] = sanitize_response(value)
        return sanitized

    elif isinstance(data, list):
        return [sanitize_response(item) for item in data]

    elif isinstance(data, str):
        lower = data.lower()
        for forbidden in FORBIDDEN_STRINGS:
            if forbidden in lower:
                return "[redacted]"
        return data

    else:
        # Numbers, booleans, None -- pass through
        return data
