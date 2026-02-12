"""
Output formatting helpers for the Streamlit UI.
"""
import pandas as pd


def format_currency(value: float, decimals: int = 4) -> str:
    """Format as USD currency."""
    if value >= 1:
        return f"${value:,.2f}"
    return f"${value:,.{decimals}f}"


def format_quantity(value: int) -> str:
    """Format quantity with commas."""
    return f"{value:,}"


def predictions_to_dataframe(predictions: list[dict]) -> pd.DataFrame:
    """Convert prediction results to a display-ready DataFrame."""
    if not predictions:
        return pd.DataFrame()

    df = pd.DataFrame(predictions)
    df["Quantity"] = df["quantity"].apply(format_quantity)
    df["Unit Price"] = df["unit_price"].apply(lambda x: format_currency(x, 5))
    df["Total Price"] = df["total_price"].apply(lambda x: format_currency(x, 2))
    df["Lower Bound"] = df["lower_bound"].apply(lambda x: format_currency(x, 5))
    df["Upper Bound"] = df["upper_bound"].apply(lambda x: format_currency(x, 5))
    df["90% CI Range"] = df.apply(
        lambda r: f"{format_currency(r['lower_bound'], 5)} – {format_currency(r['upper_bound'], 5)}",
        axis=1,
    )

    return df[["Quantity", "Unit Price", "Total Price", "90% CI Range"]]


def cost_factors_to_dataframe(cost_factors: dict) -> pd.DataFrame:
    """Convert cost factors dict to a display DataFrame."""
    if not cost_factors:
        return pd.DataFrame()

    rows = []
    for feature, info in cost_factors.items():
        label = feature.replace("_", " ").title()
        rows.append({
            "Cost Factor": label,
            "Importance": f"{info['importance']:.1f}%",
            "Your Value": info["value"],
            "_sort": info["importance"],
        })

    df = pd.DataFrame(rows).sort_values("_sort", ascending=False).drop(columns=["_sort"])
    return df.reset_index(drop=True)
