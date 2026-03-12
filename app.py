"""
Calyx Containers — ML-Powered Quoting System
Streamlit Application Entry Point

Three main pages:
  1. Quote Builder   — Input specs, get predictions
  2. Analytics       — Explore historical data & trends
  3. Model Manager   — Train/retrain models, view metrics
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config.settings import (
    SUBSTRATE_OPTIONS, SUBSTRATE_CANONICAL,
    FINISH_UI_OPTIONS, EMBELLISHMENT_UI_OPTIONS,
    FILL_STYLE_OPTIONS, SEAL_TYPE_UI_OPTIONS,
    GUSSET_UI_OPTIONS, ZIPPER_UI_OPTIONS,
    TEAR_NOTCH_UI_OPTIONS, HOLE_PUNCH_UI_OPTIONS,
    CORNER_UI_OPTIONS, PRINT_METHODS,
    DEFAULT_QTY_TIERS, DAZPAK_DEFAULT_TIERS, ROSS_DEFAULT_TIERS,
    INTERNAL_DEFAULT_TIERS, INTERNAL_MAX_WEB_WIDTH,
    DAZPAK_MIN_ORDER_QTY, ROSS_MIN_PRINT_WIDTH_INCHES,
    MODEL_DIR, ASSETS_DIR, CALYX_REPS,
)
from src.utils.validation import validate_all
from src.utils.formatting import (
    predictions_to_dataframe, cost_factors_to_dataframe,
    format_currency, format_quantity,
)
from src.utils.vendor_routing import route_vendor, calculate_print_width

# ── Page Config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Calyx Quoting System",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — Calyx Brand Guidelines ─────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    /* ── Global ─────────────────────────────────────── */
    .stApp {
        font-family: 'Instrument Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: #1a1a1a;
    }
    code, .stCode {
        font-family: 'IBM Plex Mono', 'SF Mono', Consolas, monospace;
    }

    /* ── Tighten form elements ───────────────────────── */
    .stMainBlockContainer {
        max-width: 960px;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    [data-testid="stNumberInput"] > div {
        max-width: 160px;
    }

    /* ── Page Header ────────────────────────────────── */
    .page-header {
        padding: 1.25rem 0 1rem;
        margin-bottom: 1.25rem;
        border-bottom: 2px solid #1a1a1a;
    }
    .page-header h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a1a;
        letter-spacing: -0.01em;
    }
    .page-header p {
        margin: 0.25rem 0 0;
        font-size: 0.85rem;
        color: #6b7280;
    }

    /* ── Section Labels ─────────────────────────────── */
    .section-label {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 0.5rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #d1d5db;
    }

    /* ── Metric Cards ───────────────────────────────── */
    .metric-card {
        background: #f9fafb;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .metric-card .value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1a472a;
        font-family: 'IBM Plex Mono', monospace;
    }
    .metric-card .label {
        font-size: 0.65rem;
        font-weight: 600;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.2rem;
    }

    /* ── Vendor Badges ──────────────────────────────── */
    .vendor-badge {
        display: inline-block;
        padding: 0.3rem 0.9rem;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
        letter-spacing: 0.03em;
    }
    .vendor-dazpak {
        background: #ecfdf5; color: #166534; border: 1px solid #bbf7d0;
    }
    .vendor-ross {
        background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe;
    }
    .vendor-internal {
        background: #faf5ff; color: #6b21a8; border: 1px solid #e9d5ff;
    }

    /* ── Routing Box ────────────────────────────────── */
    .routing-box {
        background: #f9fafb;
        padding: 1rem 1.25rem;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        margin-bottom: 0.75rem;
    }
    .routing-box p {
        margin: 0.4rem 0 0;
        font-size: 0.82rem;
        color: #4a4a4a;
    }

    /* ── Warning Box ────────────────────────────────── */
    .warning-box {
        background: #fffbeb;
        border-left: 3px solid #d97706;
        padding: 0.7rem 1rem;
        border-radius: 0 4px 4px 0;
        margin: 0.4rem 0;
        font-size: 0.85rem;
        color: #92400e;
    }

    /* ── Section Divider ────────────────────────────── */
    .section-divider {
        border: none;
        border-top: 1px solid #e5e7eb;
        margin: 1.25rem 0;
    }

    /* ── Results Section ────────────────────────────── */
    .results-header {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #6b7280;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #1a1a1a;
        margin-bottom: 1rem;
        margin-top: 1.5rem;
    }

    /* ── Component Table ────────────────────────────── */
    .comp-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
        margin-top: 0.5rem;
    }
    .comp-table th {
        text-align: left;
        padding: 0.5rem 0.75rem;
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #6b7280;
        border-bottom: 2px solid #1a1a1a;
    }
    .comp-table th.num { text-align: right; }
    .comp-table td {
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid #e5e7eb;
        vertical-align: middle;
    }
    .comp-table td.num {
        text-align: right;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
    }
    .comp-table td.qty {
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
    }
    .comp-table td.sell {
        text-align: right;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        color: #1a472a;
    }
    .comp-table tr.best td { background: #ecfdf5; }

    /* ── Layout Info Row ────────────────────────────── */
    .layout-row {
        display: flex;
        gap: 2rem;
        padding: 0.6rem 0;
        font-size: 0.8rem;
        color: #6b7280;
    }
    .layout-row strong {
        color: #1a1a1a;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* ── Hide Streamlit branding ────────────────────── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* ── Sidebar ────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: #f9fafb;
        border-right: 1px solid #e5e7eb;
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-size: 0.9rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ──────────────────────────────────────────────
if "predictor" not in st.session_state:
    st.session_state.predictor = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None


def load_predictor():
    """Load ML predictor (cached in session state)."""
    if st.session_state.predictor is None:
        from src.ml.prediction import QuotePredictor
        predictor = QuotePredictor()
        try:
            predictor.load_models()
            st.session_state.predictor = predictor
        except Exception as e:
            st.error(f"Failed to load models: {e}")
            return None
    return st.session_state.predictor


# ── Sidebar Navigation ──────────────────────────────────────────────
with st.sidebar:
    # Calyx logo
    logo_svg = ASSETS_DIR / "calyx_logo.svg"
    if logo_svg.exists():
        st.image(str(logo_svg), width=200)
    else:
        st.markdown("### Calyx Containers")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🏷️ Quote Builder", "📊 Analytics", "⚙️ Model Manager"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    # Quick reference
    st.markdown('<div class="section-label">Vendor Reference</div>', unsafe_allow_html=True)
    st.markdown(f"""
    **Dazpak** — Flexographic
    MOQ: {DAZPAK_MIN_ORDER_QTY:,} · Tiers: 75K–500K

    **Ross** — Digital (>12" web)
    Web width = H×2 + G · Tiers: 4K–10K

    **Internal** — HP 6900 (≤12" web)
    In-house digital · Tiers: 500–50K
    """)


# ═══════════════════════════════════════════════════════════════════
# HELPER: Generate demo data for analytics
# ═══════════════════════════════════════════════════════════════════
def _generate_demo_data() -> pd.DataFrame:
    """Generate realistic demo data for analytics preview."""
    np.random.seed(42)
    n = 200

    vendors = np.random.choice(["dazpak", "ross", "internal"], n, p=[0.35, 0.25, 0.40])
    widths = np.random.uniform(3, 8, n).round(2)
    heights = np.random.uniform(4, 12, n).round(2)
    gussets = np.random.choice([0, 1.5, 2, 2.5, 3], n)
    substrates = np.random.choice(["MET_PET", "CLR_PET", "WHT_MET_PET", "HB_CLR_PET"], n)
    finishes = np.random.choice(["Matte Laminate", "Soft Touch Laminate", "Gloss Laminate", "None"], n, p=[0.4, 0.25, 0.15, 0.2])
    zippers = np.random.choice(["CR Zipper", "Standard CR", "Single Profile Non-CR", "No Zipper"], n, p=[0.35, 0.25, 0.15, 0.25])

    # Simulate quote dates spread over last 2 years (recent quotes more common)
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    # Skew toward recent dates: 40% within last 90 days, 60% older
    days_ago = np.concatenate([
        np.random.randint(0, 90, size=int(n * 0.4)),
        np.random.randint(90, 730, size=n - int(n * 0.4)),
    ])
    np.random.shuffle(days_ago)
    created_dates = [now - timedelta(days=int(d)) for d in days_ago]

    quantities = []
    for v in vendors:
        if v == "dazpak":
            quantities.append(np.random.choice([75000, 100000, 200000, 350000, 500000]))
        elif v == "ross":
            quantities.append(np.random.choice([4000, 5000, 6000, 10000]))
        else:
            quantities.append(np.random.choice([500, 1000, 5000, 10000, 25000, 50000]))

    base = np.where(vendors == "dazpak", 0.12, np.where(vendors == "ross", 0.45, 0.25))
    area_factor = (widths * heights) * 0.002
    qty_discount = -np.log10(np.array(quantities)) * 0.03
    substrate_premium = np.where(substrates == "HB_CLR_PET", 0.04, 0)
    zipper_premium = np.where(zippers == "CR Zipper", 0.02, 0)
    noise = np.random.normal(0, 0.01, n)

    unit_prices = np.maximum(base + area_factor + qty_discount + substrate_premium + zipper_premium + noise, 0.01)

    return pd.DataFrame({
        "vendor": vendors,
        "fl_number": [f"FL-{'DL' if v == 'dazpak' else 'CQ'}-{1200+i}" for i, v in enumerate(vendors)],
        "width": widths,
        "height": heights,
        "gusset": gussets,
        "bag_area_sqin": widths * heights,
        "print_width": heights * 2 + gussets,
        "substrate": substrates,
        "finish": finishes,
        "zipper": zippers,
        "quantity": quantities,
        "unit_price": unit_prices.round(5),
        "created_at": created_dates,
    })


# ═══════════════════════════════════════════════════════════════════
# HELPER: Render prediction results
# ═══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=600, show_spinner=False)
def _sweep_predictions(specs_key: str, vendor: str, qty_list: tuple) -> list:
    """Cache-safe wrapper — runs predictor for a quantity sweep."""
    predictor = st.session_state.get("predictor")
    if predictor is None:
        return []
    import json
    specs = json.loads(specs_key)
    try:
        sweep = predictor.predict(specs, list(qty_list), vendor_override=vendor)
        return sweep.get("predictions", [])
    except Exception:
        return []


def _penny_step_chart(result: dict, margin_multiplier: float) -> "go.Figure | None":
    """
    Continuous quantity sweep — the 'penny step' price curve.

    Runs the predictor at ~70 log-spaced quantity points so the chart
    shows where pricing changes at each level, not just at the user's
    chosen tiers.  User-specified tiers are overlaid as large dots.
    """
    import json, numpy as np

    vendor = result.get("vendor", "ross")
    specs  = result.get("specs", {})
    is_det = result.get("is_deterministic", False)
    preds  = result.get("predictions", [])

    if not preds:
        return None

    # ── Quantity sweep range per vendor ─────────────────────────────
    sweep_map = {
        "dazpak":   (35_000, 2_000_000),
        "ross":     (1_000, 300_000),
        "internal": (500, 100_000),
        "tedpack":  (10_000, 1_000_000),
    }
    lo, hi = sweep_map.get(vendor, (1_000, 300_000))
    # Extend hi to cover any user tiers beyond the default range
    max_user_qty = max((p["quantity"] for p in preds), default=hi)
    hi = max(hi, int(max_user_qty * 1.1))

    qty_sweep = np.unique(np.geomspace(lo, hi, 70).astype(int))

    # Add user-specified tiers explicitly so they land exactly on curve
    user_qtys = [p["quantity"] for p in preds]
    qty_sweep = np.unique(np.concatenate([qty_sweep, user_qtys]))

    specs_key = json.dumps({k: v for k, v in specs.items() if k != "quantity"}, sort_keys=True)
    sweep_preds = _sweep_predictions(specs_key, vendor, tuple(qty_sweep.tolist()))

    if not sweep_preds:
        return None

    # Handle Teapack dual air/ocean structure
    if vendor == "tedpack" and sweep_preds and "air_unit_price" in sweep_preds[0]:
        sq  = [p["quantity"]        for p in sweep_preds]
        air = [p["air_unit_price"]  for p in sweep_preds]
        ocn = [p["ocean_unit_price"] for p in sweep_preds]
        air_s = [v * margin_multiplier for v in air]
        ocn_s = [v * margin_multiplier for v in ocn]

        tier_q     = [p["quantity"]        for p in preds]
        tier_air_s = [p["air_unit_price"] * margin_multiplier  for p in preds]
        tier_ocn_s = [p["ocean_unit_price"] * margin_multiplier for p in preds]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sq, y=air_s, mode="lines",
            line=dict(color="#2d6a4f", width=2.5),
            name="Air (sell)", hovertemplate="<b>%{x:,}</b><br>Air: $%{y:.4f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=sq, y=ocn_s, mode="lines",
            line=dict(color="#6cb4e4", width=2.5),
            name="Ocean (sell)", hovertemplate="<b>%{x:,}</b><br>Ocean: $%{y:.4f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=tier_q, y=tier_air_s, mode="markers",
            marker=dict(size=11, color="#1a472a", symbol="circle",
                        line=dict(color="white", width=2)),
            name="Air tiers", hovertemplate="<b>%{x:,} (tier)</b><br>Air: $%{y:.4f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=tier_q, y=tier_ocn_s, mode="markers",
            marker=dict(size=11, color="#1e6091", symbol="diamond",
                        line=dict(color="white", width=2)),
            name="Ocean tiers", hovertemplate="<b>%{x:,} (tier)</b><br>Ocean: $%{y:.4f}<extra></extra>",
        ))
    else:
        sq    = [p["quantity"]   for p in sweep_preds]
        costs = [p["unit_price"] for p in sweep_preds]
        sells = [p["unit_price"] * margin_multiplier for p in sweep_preds]

        # CI band (ML models only)
        has_ci = not is_det and "upper_bound" in (sweep_preds[0] if sweep_preds else {})
        if has_ci:
            uppers = [p["upper_bound"] * margin_multiplier for p in sweep_preds]
            lowers = [p["lower_bound"] * margin_multiplier for p in sweep_preds]

        tier_q = [p["quantity"]   for p in preds]
        tier_s = [p["unit_price"] * margin_multiplier for p in preds]

        fig = go.Figure()
        if has_ci:
            fig.add_trace(go.Scatter(
                x=sq + sq[::-1], y=uppers + lowers[::-1],
                fill="toself", fillcolor="rgba(45,106,79,0.10)",
                line=dict(color="rgba(0,0,0,0)"),
                name="80% CI", hoverinfo="skip", showlegend=True,
            ))
        fig.add_trace(go.Scatter(
            x=sq, y=costs, mode="lines",
            line=dict(color="#9e9e9e", width=1.5, dash="dot"),
            name="Est. Cost",
            hovertemplate="<b>%{x:,}</b><br>Cost: $%{y:.4f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=sq, y=sells, mode="lines",
            line=dict(color="#2d6a4f", width=2.5),
            name=f"Sell Price",
            hovertemplate="<b>%{x:,}</b><br>Sell: $%{y:.4f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=tier_q, y=tier_s, mode="markers",
            marker=dict(size=11, color="#1a472a", symbol="circle",
                        line=dict(color="white", width=2)),
            name="Your Tiers",
            hovertemplate="<b>%{x:,} units (tier)</b><br>Sell: $%{y:.4f}<extra></extra>",
        ))

    fig.update_layout(
        xaxis_title="Quantity",
        yaxis_title="Unit Price ($)",
        template="plotly_white",
        height=380,
        margin=dict(l=50, r=30, t=10, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(tickformat=",")
    return fig


@st.cache_data(ttl=900, show_spinner=False)
def _vendor_alternatives_ai(vendor: str, specs_key: str, tier_summary: str) -> str:
    """
    Call the Anthropic API to generate a sentence-level explanation of
    what it would take to route this job to each alternative vendor.
    Returns markdown-formatted text.
    """
    import os, httpx, json

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
    if not api_key:
        return "_AI vendor analysis requires ANTHROPIC_API_KEY in your environment or Streamlit secrets._"

    specs = json.loads(specs_key)
    w, h, g = specs.get("width", "?"), specs.get("height", "?"), specs.get("gusset", 0)
    substrate = specs.get("substrate", "Unknown")
    finish    = specs.get("finish", "Unknown")
    zipper    = specs.get("zipper", "None")
    pw = float(h) * 2 + float(g) if h != "?" else "?"

    vendor_labels = {
        "internal": "Internal HP 6900 (narrow digital)",
        "ross":     "Ross HP Indigo (wide-format digital)",
        "dazpak":   "Dazpak (flexographic)",
        "tedpack":  "Teapack (China, FOB)",
    }
    current_label = vendor_labels.get(vendor, vendor)

    prompt = f"""You are a flexible packaging pricing analyst at Calyx Containers.
You have just generated a quote for a customer. Here are the job specs:

- Dimensions: {w}" W × {h}" H × {g}" G  (print width = {pw}")
- Substrate: {substrate}
- Finish: {finish}
- Zipper: {zipper}
- Quantity tiers: {tier_summary}
- Routed to: **{current_label}**

The four available vendors and their routing rules:
1. **Internal HP 6900** — narrow digital. Only viable when print width ≤ 12". Best for short runs and proofs.
2. **Ross HP Indigo** — wide-format digital. Used when print width > 12". Best for runs up to ~250K.
3. **Dazpak** — flexographic. MOQ 35,000 units per SKU. Best for 75K–2M unit runs. Plates + setup time adds 3–4 weeks to first run.
4. **Teapack** — Chinese vendor, FOB pricing. Best for high-volume 50K+ orders. Ocean freight: 5–7 weeks. Air freight: 1–2 weeks. 35% tariff currently in effect.

Write 2–4 short, punchy sentences (no headers, no bullet points) that tell the sales rep:
- Why this job landed on {current_label}
- What specific changes (qty, dimensions, print method) would be needed to qualify for each viable alternative
- Any tradeoffs worth flagging (lead time, cost at scale, MOQ gaps, tariff exposure)

Be direct, specific, and use numbers. Mention actual quantity thresholds and lead times.
Do not mention SHAP or machine learning. Keep it under 120 words."""

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
    except Exception as e:
        return f"_Vendor analysis unavailable: {e}_"


def _render_results(result: dict, margin_pct: int = 35):
    """Render prediction results with margin-adjusted sell prices."""
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Calculate margin multiplier: Sell = Cost / (1 - margin/100)
    if margin_pct >= 100:
        margin_pct = 99
    margin_multiplier = 1.0 / (1.0 - margin_pct / 100.0)

    # Header
    st.markdown(f'<div class="results-header">Estimate Results — {margin_pct}% Margin</div>', unsafe_allow_html=True)

    # Header metrics
    preds = result["predictions"]
    if preds:
        mcols = st.columns(3)
        with mcols[0]:
            vendor_label = {"dazpak": "Dazpak", "ross": "Ross", "internal": "Internal"}.get(result["vendor"], result["vendor"])
            vendor_class = {"dazpak": "vendor-dazpak", "ross": "vendor-ross", "internal": "vendor-internal"}.get(result["vendor"], "")
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Vendor</div>
                <div class="value"><span class="vendor-badge {vendor_class}">{vendor_label}</span></div>
            </div>""", unsafe_allow_html=True)
        with mcols[1]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Print Method</div>
                <div class="value" style="font-size:1rem; font-family:'Instrument Sans',sans-serif;">{result['print_method'].title()}</div>
            </div>""", unsafe_allow_html=True)
        with mcols[2]:
            mape = result.get("model_metrics", {}).get("mape", None)

            if isinstance(mape, (int, float)):
                if mape <= 5:
                    conf_label, conf_color = "Very High", "#166534"
                elif mape <= 10:
                    conf_label, conf_color = "High", "#15803d"
                elif mape <= 15:
                    conf_label, conf_color = "Moderate", "#a16207"
                elif mape <= 25:
                    conf_label, conf_color = "Low", "#c2410c"
                else:
                    conf_label, conf_color = "Very Low", "#dc2626"
                conf_detail = f"{100 - mape:.0f}% avg accuracy"
            else:
                conf_label, conf_color = "—", "#6b7280"
                conf_detail = ""

            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Confidence</div>
                <div class="value" style="color:{conf_color};">{conf_label}</div>
                <div class="label" style="font-size:0.6rem;">{conf_detail}</div>
            </div>""", unsafe_allow_html=True)

    # Warnings
    for w in result.get("warnings", []):
        st.warning(w)

    # Pricing table with both cost and sell columns
    st.markdown('<div class="results-header">Pricing by Quantity Tier</div>', unsafe_allow_html=True)
    if preds:
        import pandas as pd
        is_det = result.get("is_deterministic", False)
        lowest_qty_cost = min(preds, key=lambda p: p["unit_price"])

        # Build HTML table
        header_cells = '<th class="num">Unit Cost</th><th class="num">Unit Sell</th><th class="num">Total Cost</th><th class="num">Total Sell</th>'
        if not is_det:
            header_cells += '<th class="num">90% CI Range</th>'
        table_html = f'<table class="comp-table"><thead><tr><th>Quantity</th>{header_cells}</tr></thead><tbody>'

        for p in preds:
            cost = p["unit_price"]
            sell = cost * margin_multiplier
            total_cost = p["total_price"]
            total_sell = total_cost * margin_multiplier
            row_class = ' class="best"' if p is lowest_qty_cost else ''
            ci_cell = ""
            if not is_det:
                ci_cell = f'<td class="num">{format_currency(p["lower_bound"], 5)} – {format_currency(p["upper_bound"], 5)}</td>'
            table_html += f'''<tr{row_class}>
                <td class="qty">{p["quantity"]:,}</td>
                <td class="num">{format_currency(cost, 5)}</td>
                <td class="sell">{format_currency(sell, 5)}</td>
                <td class="num">{format_currency(total_cost, 2)}</td>
                <td class="sell">{format_currency(total_sell, 2)}</td>
                {ci_cell}
            </tr>'''

        table_html += '</tbody></table>'
        # Use st.html() — st.markdown(unsafe_allow_html) strips <table> in newer Streamlit
        styled_table = f"""<style>
        .comp-table {{ width:100%; border-collapse:collapse; font-size:0.82rem; }}
        .comp-table th {{ text-align:left; padding:0.5rem 0.75rem; font-size:0.65rem; font-weight:600;
            letter-spacing:0.06em; text-transform:uppercase; color:#6b7280; border-bottom:2px solid #1a1a1a; }}
        .comp-table th.num {{ text-align:right; }}
        .comp-table td {{ padding:0.5rem 0.75rem; border-bottom:1px solid #e5e7eb; vertical-align:middle; }}
        .comp-table td.num {{ text-align:right; font-family:'IBM Plex Mono',monospace; font-size:0.8rem; }}
        .comp-table td.qty {{ font-family:'IBM Plex Mono',monospace; font-weight:600; }}
        .comp-table td.sell {{ text-align:right; font-family:'IBM Plex Mono',monospace; font-weight:600; color:#1a472a; }}
        .comp-table tr.best td {{ background:#ecfdf5; }}
        </style>{table_html}"""
        st.html(styled_table)

        # ── Download Estimate PDF ──────────────────────────────────
        try:
            from src.utils.pdf_estimate import generate_estimate_pdf

            specs_data = result.get("specs", {})
            dims = f"{specs_data.get('width', '?')} x {specs_data.get('height', '?')} x {specs_data.get('gusset', '?')}"
            cust = specs_data.get("customer_name", "")
            rep = specs_data.get("calyx_rep", "")

            pdf_pricing = []
            for p in preds:
                sell = p["unit_price"] * margin_multiplier
                pdf_pricing.append({
                    "quantity": p["quantity"],
                    "unit_price": sell,
                    "total_price": sell * p["quantity"],
                })

            pdf_bytes, est_number = generate_estimate_pdf(
                customer_name=cust,
                calyx_rep=rep,
                dimensions=dims,
                print_method=specs_data.get("print_method", "Digital"),
                substrate=specs_data.get("substrate", ""),
                finish=specs_data.get("finish", ""),
                colors="CMYK",
                embellishment=specs_data.get("embellishment", "None"),
                fill_style=specs_data.get("fill_style", ""),
                seal_type=specs_data.get("seal_type", ""),
                zipper=specs_data.get("zipper", ""),
                tear_notch=specs_data.get("tear_notch", ""),
                hole_punch=specs_data.get("hole_punch", ""),
                gusset_detail=specs_data.get("gusset_type", ""),
                corners=specs_data.get("corner_treatment", ""),
                pricing=pdf_pricing,
            )

            # Save estimate to database
            try:
                from src.data.supabase_client import save_estimate
                from src.utils.vendor_routing import calculate_print_width as calc_pw

                save_estimate({
                    "estimate_number": est_number,
                    "customer_name": cust,
                    "calyx_rep": rep,
                    "width": specs_data.get("width"),
                    "height": specs_data.get("height"),
                    "gusset": specs_data.get("gusset"),
                    "print_width": calc_pw(specs_data.get("height", 0), specs_data.get("gusset", 0)),
                    "substrate": specs_data.get("substrate"),
                    "finish": specs_data.get("finish"),
                    "embellishment": specs_data.get("embellishment"),
                    "fill_style": specs_data.get("fill_style"),
                    "seal_type": specs_data.get("seal_type"),
                    "gusset_type": specs_data.get("gusset_type"),
                    "zipper": specs_data.get("zipper"),
                    "tear_notch": specs_data.get("tear_notch"),
                    "hole_punch": specs_data.get("hole_punch"),
                    "corner_treatment": specs_data.get("corner_treatment"),
                    "print_method": specs_data.get("print_method"),
                    "vendor_routed": result.get("vendor"),
                    "margin_pct": margin_pct,
                    "pricing_tiers": pdf_pricing,
                    "component_costs": result.get("component_costs"),
                })
            except Exception as db_err:
                import logging
                logging.getLogger(__name__).warning(f"DB save failed: {db_err}")

            safe_cust = cust.replace(" ", "_") if cust else "Customer"
            filename = f"{est_number}_{safe_cust}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
            st.download_button(
                label="Download Estimate PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
            )
            st.caption(f"Estimate {est_number}")
        except Exception as e:
            st.caption(f"PDF generation unavailable: {e}")

    # ── Penny-Step Price Curve ───────────────────────────────────────
    if preds:
        st.markdown('<div class="results-header">Price Curve — All Quantity Levels</div>', unsafe_allow_html=True)
        st.caption("Continuous sweep across the full quantity range. Your quoted tiers shown as ●")
        with st.spinner("Building price curve…"):
            penny_fig = _penny_step_chart(result, margin_multiplier)
        if penny_fig:
            st.plotly_chart(penny_fig, use_container_width=True)
        else:
            st.info("Price curve requires trained models to be loaded.")

    # ── SHAP Breakdown + AI Vendor Analysis ─────────────────────────
    if preds:
        is_det = result.get("is_deterministic", False)
        analysis_cols = st.columns([1, 1])

        with analysis_cols[0]:
            st.markdown('<div class="results-header">Key Price Drivers</div>', unsafe_allow_html=True)
            cf_df = cost_factors_to_dataframe(result.get("cost_factors", {}))
            if not cf_df.empty:
                # Truncate long factor names for display
                cf_df["Cost Factor"] = cf_df["Cost Factor"].str.replace("_", " ").str.title()
                fig2 = px.bar(
                    cf_df.head(10),
                    x="Importance",
                    y="Cost Factor",
                    orientation="h",
                    color="Importance",
                    color_continuous_scale=["#d1d5db", "#1a472a"],
                    text="Your Value",
                )
                fig2.update_traces(textposition="inside", insidetextanchor="middle")
                fig2.update_layout(
                    template="plotly_white",
                    height=340,
                    margin=dict(l=10, r=20, t=10, b=30),
                    showlegend=False,
                    coloraxis_showscale=False,
                    yaxis=dict(autorange="reversed"),
                    xaxis_title="% Influence on Price" if not is_det else "% of Total Cost",
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Price driver breakdown requires a trained model.")

        with analysis_cols[1]:
            st.markdown('<div class="results-header">Vendor Routing Analysis</div>', unsafe_allow_html=True)
            import json
            specs = result.get("specs", {})
            vendor = result.get("vendor", "")
            tier_summary = ", ".join(
                f"{p['quantity']:,}" for p in preds[:6]
            )
            specs_key = json.dumps(
                {k: v for k, v in specs.items() if k != "quantity"}, sort_keys=True
            )
            with st.spinner("Analyzing vendor options…"):
                ai_text = _vendor_alternatives_ai(vendor, specs_key, tier_summary)

            # Render the AI text in a styled card
            st.markdown(f"""
            <div style="
                background:#f0fdf4;
                border-left:3px solid #2d6a4f;
                border-radius:6px;
                padding:1rem 1.1rem;
                font-size:0.85rem;
                line-height:1.65;
                color:#1a1a1a;
                font-family:'Instrument Sans',sans-serif;
                margin-top:0.25rem;
            ">{ai_text}</div>
            """, unsafe_allow_html=True)

            # Quick-glance routing grid below the AI text
            pw = float(specs.get("height", 0)) * 2 + float(specs.get("gusset", 0))
            min_qty = min((p["quantity"] for p in preds), default=0)
            max_qty = max((p["quantity"] for p in preds), default=0)
            rows = {
                "Internal HP":  ("✅" if pw <= 12 else "❌",  "Any qty",       "1–2 days"),
                "Ross":         ("✅" if pw > 12 else "❌",   "Any qty",       "1–2 weeks"),
                "Dazpak":       ("✅" if max_qty >= 35_000 else "⚠️", "35K+ MOQ", "3–5 weeks"),
                "Teapack":      ("✅" if max_qty >= 50_000 else "⚠️", "50K+ ideal","5–7 wks ocean / 1–2 wks air"),
            }
            grid_html = """<table style="width:100%;border-collapse:collapse;font-size:0.75rem;margin-top:0.75rem;">
            <thead><tr>
              <th style="text-align:left;padding:4px 6px;color:#6b7280;border-bottom:1px solid #e5e7eb;">Vendor</th>
              <th style="text-align:center;padding:4px 6px;color:#6b7280;border-bottom:1px solid #e5e7eb;">Eligible</th>
              <th style="text-align:left;padding:4px 6px;color:#6b7280;border-bottom:1px solid #e5e7eb;">Qty</th>
              <th style="text-align:left;padding:4px 6px;color:#6b7280;border-bottom:1px solid #e5e7eb;">Lead Time</th>
            </tr></thead><tbody>"""
            for vname, (elig, qty_note, lt) in rows.items():
                is_active = vname.lower().replace(" hp", "").replace("pack", "pak") in vendor.lower() or \
                            (vname == "Internal HP" and vendor == "internal") or \
                            (vname == "Teapack" and vendor == "tedpack")
                bg = "background:#ecfdf5;" if is_active else ""
                grid_html += f"""<tr style="{bg}">
                  <td style="padding:4px 6px;font-weight:{'600' if is_active else '400'};">{vname}</td>
                  <td style="text-align:center;padding:4px 6px;">{elig}</td>
                  <td style="padding:4px 6px;color:#374151;">{qty_note}</td>
                  <td style="padding:4px 6px;color:#374151;">{lt}</td>
                </tr>"""
            grid_html += "</tbody></table>"
            st.html(grid_html)

        # ── Component Cost Breakdown Table (deterministic only) ──
        if is_det and result.get("component_costs"):
            st.markdown('<div class="results-header">Production Cost Breakdown</div>', unsafe_allow_html=True)
            import pandas as pd
            comp_rows = []
            for cc in result["component_costs"]:
                comp_rows.append({
                    "Quantity": f"{cc['quantity']:,}",
                    "Substrate": format_currency(cc.get("substrate", 0), 2),
                    "Priming": format_currency(cc.get("priming", 0), 2),
                    "Clicks": format_currency(cc.get("clicks", 0), 2),
                    "HP Labor": format_currency(cc.get("hp_makeready", 0) + cc.get("hp_running", 0), 2),
                    "Laminate": format_currency(cc.get("laminate", 0), 2),
                    "Thermo": format_currency(cc.get("thermo_labor", 0), 2),
                    "Zipper": format_currency(cc.get("zipper", 0), 2),
                    "Poucher": format_currency(cc.get("poucher_labor", 0), 2),
                    "Sealer": format_currency(cc.get("sealer", 0), 2),
                    "Packaging": format_currency(cc.get("packaging", 0), 2),
                    "Total": format_currency(cc.get("total", 0), 2),
                })
            comp_df = pd.DataFrame(comp_rows)
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

            # Layout info
            layout = result.get("layout", {})
            if layout:
                st.caption(
                    f"Layout: {layout.get('no_around', '?')} around × "
                    f"{layout.get('no_across', '?')} across | "
                    f"Gear: {layout.get('gear_teeth', '?')} teeth | "
                    f"Repeat: {layout.get('repeat_in', '?')}\" | "
                    f"Spoilage: {layout.get('combined_spoilage', 0)*100:.1f}%"
                )


# ═══════════════════════════════════════════════════════════════════
# PAGE 1: QUOTE BUILDER
# ═══════════════════════════════════════════════════════════════════
if page == "🏷️ Quote Builder":

    st.markdown("""
    <div class="page-header">
        <h1>Packaging Estimate Generator</h1>
        <p>Get instant cost estimates for custom flexible packaging. Enter your bag specs and quantities below — pricing is generated from historical production data and vendor cost models.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Customer & Rep ──────────────────────────────────────────────
    cust_cols = st.columns([3, 2, 2])
    with cust_cols[0]:
        customer_name = st.text_input("Customer Name", value="", placeholder="Enter customer name")
    with cust_cols[1]:
        calyx_rep = st.selectbox("Calyx Rep", CALYX_REPS)
    with cust_cols[2]:
        print_method = st.selectbox("Print Method", PRINT_METHODS,
                                    help="Flexographic → Dazpak | Digital: ≤12\" → Internal, >12\" → Ross")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── Input Form ──────────────────────────────────────────────────
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown('<div class="section-label">Bag Specifications</div>', unsafe_allow_html=True)

        # Dimensions
        dim_cols = st.columns(3)
        with dim_cols[0]:
            width = st.number_input("Width (in)", min_value=0.5, max_value=20.0,
                                    value=5.0, step=0.25, format="%.3f")
        with dim_cols[1]:
            height = st.number_input("Height (in)", min_value=0.5, max_value=20.0,
                                     value=6.5, step=0.25, format="%.3f")
        with dim_cols[2]:
            gusset = st.number_input("Gusset (in)", min_value=0.0, max_value=10.0,
                                     value=2.0, step=0.25, format="%.3f")

        # Calculated print width display
        pw = calculate_print_width(height, gusset)
        if pw > 12:
            pw_color = "🔵"
            pw_label = "Ross eligible (>12\")"
        else:
            pw_color = "🟣"
            pw_label = "Internal (HP 6900) — ≤12\""
        st.caption(f"Print Width: **{pw:.2f}\"** (H×2 + G)  {pw_color} {pw_label}")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Material & finish
        mat_cols = st.columns(2)
        with mat_cols[0]:
            substrate = st.selectbox("Substrate", SUBSTRATE_OPTIONS)
        with mat_cols[1]:
            finish = st.selectbox("Finish", FINISH_UI_OPTIONS)

        # Bag features row 1
        feat_cols1 = st.columns(3)
        with feat_cols1[0]:
            fill_style = st.selectbox("Fill Style", FILL_STYLE_OPTIONS)
        with feat_cols1[1]:
            seal_type = st.selectbox("Seal Type", SEAL_TYPE_UI_OPTIONS)
        with feat_cols1[2]:
            gusset_type = st.selectbox("Gusset Type", GUSSET_UI_OPTIONS)

        # Bag features row 2
        feat_cols2 = st.columns(3)
        with feat_cols2[0]:
            zipper = st.selectbox("Zipper", ZIPPER_UI_OPTIONS)
        with feat_cols2[1]:
            tear_notch = st.selectbox("Tear Notch", TEAR_NOTCH_UI_OPTIONS)
        with feat_cols2[2]:
            corner = st.selectbox("Corners", CORNER_UI_OPTIONS)

        # Remaining features
        feat_cols3 = st.columns(2)
        with feat_cols3[0]:
            hole_punch = st.selectbox("Hole Punch", HOLE_PUNCH_UI_OPTIONS)
        with feat_cols3[1]:
            embellishment = st.selectbox("Embellishment", EMBELLISHMENT_UI_OPTIONS)

    with col_right:
        st.markdown('<div class="section-label">Quantity Tiers</div>', unsafe_allow_html=True)
        st.caption("Up to 12 tiers — leave blank or 0 to skip")

        # Auto-suggest tiers based on vendor routing
        if print_method == "Flexographic":
            suggested = DAZPAK_DEFAULT_TIERS[:]
        elif pw <= 12:
            suggested = INTERNAL_DEFAULT_TIERS[:]
        else:
            suggested = ROSS_DEFAULT_TIERS[:]

        # Pad suggested to 12 (remaining are 0 = empty)
        while len(suggested) < 12:
            suggested.append(0)

        quantities = []
        for row in range(3):
            row_cols = st.columns(4)
            for col in range(4):
                i = row * 4 + col
                with row_cols[col]:
                    default = suggested[i] if i < len(suggested) else 0
                    default_str = f"{default:,}" if default > 0 else ""
                    raw = st.text_input(
                        f"Tier {i+1}",
                        value=default_str,
                        key=f"qty_{i}",
                        placeholder="0",
                    )
                    # Parse: strip commas, spaces
                    cleaned = raw.replace(",", "").replace(" ", "").strip()
                    if cleaned.isdigit() and int(cleaned) > 0:
                        quantities.append(int(cleaned))

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # ── Vendor Routing Preview ──────────────────────────────────
        routing = route_vendor(print_method, height, gusset, quantities)
        vendor_class_map = {"dazpak": "vendor-dazpak", "ross": "vendor-ross", "internal": "vendor-internal"}
        vendor_label_map = {
            "dazpak": "Dazpak (Flexographic)",
            "ross": "Ross (Digital)",
            "internal": "Internal — HP 6900 (Digital)",
        }
        vendor_class = vendor_class_map.get(routing["vendor"], "vendor-internal")
        vendor_label = vendor_label_map.get(routing["vendor"], routing["vendor"])

        st.markdown(f"""
        <div class="routing-box">
            <span class="vendor-badge {vendor_class}">{vendor_label}</span>
            <p>{routing['reason']}</p>
        </div>
        """, unsafe_allow_html=True)

        for w in routing["warnings"]:
            st.markdown(f'<div class="warning-box">{w}</div>', unsafe_allow_html=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # ── Margin Setting ───────────────────────────────────────
        st.markdown('<div class="section-label">Margin</div>', unsafe_allow_html=True)
        margin_cols = st.columns([2, 1])
        with margin_cols[0]:
            margin_pct = st.slider(
                "Margin %",
                min_value=0,
                max_value=100,
                value=20,
                step=5,
                help="Markup applied on top of cost to get the sell price. Sell Price = Cost ÷ (1 - Margin%/100)",
            )
        with margin_cols[1]:
            st.markdown(f"""
            <div class="metric-card" style="margin-top:0.5rem;">
                <div class="label">Margin</div>
                <div class="value">{margin_pct}%</div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # ── Generate Estimate Button ──────────────────────────────────
        generate = st.button("Generate Estimate", type="primary", use_container_width=True)

    # ── Process & Display Results ───────────────────────────────────
    if generate:
        # Build specs dict
        specs = {
            "width": width,
            "height": height,
            "gusset": gusset,
            "substrate": SUBSTRATE_CANONICAL.get(substrate, "CUSTOM"),
            "finish": finish,
            "fill_style": fill_style,
            "seal_type": seal_type,
            "gusset_type": gusset_type,
            "zipper": zipper,
            "tear_notch": tear_notch,
            "hole_punch": hole_punch,
            "corner_treatment": corner,
            "embellishment": embellishment,
            "print_method": print_method,
            "customer_name": customer_name,
            "calyx_rep": calyx_rep,
        }

        # Validate
        errors = validate_all(specs, quantities)
        if errors:
            for e in errors:
                st.error(e)
        else:
            predictor = load_predictor()
            if predictor:
                with st.spinner("Generating predictions..."):
                    result = predictor.predict(specs, sorted(quantities))
                    # Store specs in result for PDF generation
                    result["specs"] = specs
                    st.session_state.last_result = result

                if result.get("error"):
                    st.error(result["error"])
                    st.info("💡 Go to **Model Manager** to train models with your historical data first.")
                else:
                    _render_results(result, margin_pct)
            else:
                st.error("Models not loaded. Train models first via the Model Manager page.")

    # Show previous results if available
    elif st.session_state.last_result and not generate:
        st.markdown("---")
        st.caption("Showing previous estimate results:")
        _render_results(st.session_state.last_result, margin_pct)



# ═══════════════════════════════════════════════════════════════════
# PAGE 2: ANALYTICS
# ═══════════════════════════════════════════════════════════════════
elif page == "📊 Analytics":

    st.markdown("""
    <div class="page-header">
        <h1>Quote Analytics</h1>
        <p>Historical pricing data and trends across vendors</p>
    </div>
    """, unsafe_allow_html=True)

    # Try to load data from Supabase or show demo
    @st.cache_data(ttl=300)
    def load_analytics_data():
        try:
            from src.data.supabase_client import fetch_training_data
            df = fetch_training_data()
            if not df.empty:
                return df, "supabase"
        except Exception:
            pass

        # Generate demo data for UI preview
        return _generate_demo_data(), "demo"

    data, source = load_analytics_data()

    if source == "demo":
        st.info("📌 Showing demo data. Connect Supabase and ingest historical quotes to see real analytics.")

    if not data.empty:
        # Summary metrics
        mcols = st.columns(5)
        with mcols[0]:
            st.metric("Total Quotes", f"{data['fl_number'].nunique() if 'fl_number' in data.columns else len(data):,}")
        with mcols[1]:
            if 'vendor' in data.columns:
                st.metric("Dazpak Quotes", f"{(data['vendor'] == 'dazpak').sum():,}")
        with mcols[2]:
            if 'vendor' in data.columns:
                st.metric("Ross Quotes", f"{(data['vendor'] == 'ross').sum():,}")
        with mcols[3]:
            if 'vendor' in data.columns:
                st.metric("Internal Quotes", f"{(data['vendor'] == 'internal').sum():,}")
        with mcols[4]:
            if 'unit_price' in data.columns:
                st.metric("Avg Unit Price", format_currency(data['unit_price'].mean(), 4))

        st.markdown("---")

        # Charts
        chart_tab1, chart_tab2, chart_tab3 = st.tabs([
            "Price Distribution", "Price vs Volume", "Spec Analysis"
        ])

        with chart_tab1:
            if 'unit_price' in data.columns and 'vendor' in data.columns:
                fig = px.histogram(
                    data, x="unit_price", color="vendor",
                    barmode="overlay", nbins=40,
                    color_discrete_map={"dazpak": "#166534", "ross": "#1e40af", "internal": "#6b21a8"},
                )
                fig.update_layout(template="plotly_white", height=400)
                st.plotly_chart(fig, use_container_width=True)

        with chart_tab2:
            if 'quantity' in data.columns and 'unit_price' in data.columns:
                fig = px.scatter(
                    data, x="quantity", y="unit_price",
                    color="vendor" if "vendor" in data.columns else None,
                    size="bag_area_sqin" if "bag_area_sqin" in data.columns else None,
                    color_discrete_map={"dazpak": "#166534", "ross": "#1e40af", "internal": "#6b21a8"},
                    labels={"quantity": "Order Quantity", "unit_price": "Unit Price ($)"},
                    log_x=True,
                )
                fig.update_layout(template="plotly_white", height=400)
                st.plotly_chart(fig, use_container_width=True)

        with chart_tab3:
            if 'substrate' in data.columns and 'unit_price' in data.columns:
                fig = px.box(
                    data, x="substrate", y="unit_price",
                    color="vendor" if "vendor" in data.columns else None,
                    color_discrete_map={"dazpak": "#166534", "ross": "#1e40af", "internal": "#6b21a8"},
                )
                fig.update_layout(template="plotly_white", height=400)
                st.plotly_chart(fig, use_container_width=True)

        # Raw data explorer
        with st.expander("📋 Raw Data Explorer"):
            st.dataframe(data, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 3: MODEL MANAGER
# ═══════════════════════════════════════════════════════════════════
elif page == "⚙️ Model Manager":

    st.markdown("""
    <div class="page-header">
        <h1>Model Manager</h1>
        <p>Train, evaluate, and manage pricing models</p>
    </div>
    """, unsafe_allow_html=True)

    tab_train, tab_metrics, tab_data = st.tabs([
        "🏋️ Train Models", "📈 Model Metrics", "📥 Data Ingestion"
    ])

    with tab_train:
        st.markdown("### Train Pricing Models")
        st.markdown("""
        This will train separate Gradient Boosting models for:
        - **Dazpak** (Flexographic) — predicts Price/Ea Impression
        - **Ross** (Digital >12") — predicts unit price per bag
        - **Internal** (Digital ≤12" / HP 6900) — predicts unit cost per bag (log-target)

        Each model includes:
        - Point prediction (squared error loss)
        - Lower/upper confidence bounds (10th/90th quantile regression)
        - Cross-validated performance metrics
        - **Recency weighting** — quotes from the last 90 days get 3× training weight
        """)

        data_source = st.radio(
            "Training data source",
            ["Supabase (production)", "Demo data (for testing)"],
            horizontal=True,
        )

        if st.button("🚀 Train Models", type="primary"):
            with st.spinner("Training models... this may take a minute."):
                try:
                    if data_source == "Demo data (for testing)":
                        train_df = _generate_demo_data()
                    else:
                        from src.data.supabase_client import fetch_training_data
                        train_df = fetch_training_data()

                    if train_df.empty:
                        st.error("No training data available. Ingest data first.")
                    else:
                        from src.ml.model_training import train_all_models
                        results = train_all_models(train_df)
                        st.session_state.predictor = None  # Force reload

                        for vendor, metrics in results.items():
                            st.success(f"✅ **{vendor.title()}** — MAPE: {metrics['mape']:.1f}%, R²: {metrics['r2']:.3f}")

                        st.balloons()
                except Exception as e:
                    st.error(f"Training failed: {e}")
                    st.exception(e)

    with tab_metrics:
        st.markdown("### Current Model Performance")

        for vendor in ["dazpak", "ross"]:
            try:
                import joblib
                metrics = joblib.load(MODEL_DIR / f"{vendor}_metrics.joblib")
                importances = joblib.load(MODEL_DIR / f"{vendor}_importances.joblib")

                st.markdown(f"#### {vendor.title()} Model")
                metric_cols = st.columns(5)
                with metric_cols[0]:
                    st.metric("MAPE", f"{metrics['mape']:.1f}%")
                with metric_cols[1]:
                    st.metric("RMSE", f"${metrics['rmse']:.5f}")
                with metric_cols[2]:
                    st.metric("R²", f"{metrics['r2']:.3f}")
                with metric_cols[3]:
                    st.metric("90% CI Coverage", f"{metrics['coverage_90']:.0f}%")
                with metric_cols[4]:
                    st.metric("CV MAPE", f"{metrics['cv_mape_mean']:.1f}% ± {metrics['cv_mape_std']:.1f}%")

                # Show recency weighting info if present
                if metrics.get("recency_weighting"):
                    n_recent = metrics.get("n_recent_train", "?")
                    n_total = metrics.get("n_train", "?")
                    recent_days = metrics.get("recency_recent_days", 90)
                    st.caption(
                        f"📅 Recency weighted: {n_recent}/{n_total} training samples "
                        f"from last {recent_days} days received "
                        f"{metrics.get('recency_recent_weight', 3.0):.0f}× weight"
                    )

                # Feature importance chart
                imp_items = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:12]
                imp_df = pd.DataFrame(imp_items, columns=["Feature", "Importance"])
                fig = px.bar(
                    imp_df, x="Importance", y="Feature", orientation="h",
                    color="Importance",
                    color_continuous_scale=["#d1d5db", "#1a472a"],
                )
                fig.update_layout(
                    template="plotly_white", height=300,
                    yaxis=dict(autorange="reversed"),
                    showlegend=False, coloraxis_showscale=False,
                    margin=dict(l=20, r=20, t=10, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("---")

            except FileNotFoundError:
                st.info(f"No trained model found for **{vendor.title()}**. Train models first.")


        # Internal — Deterministic Calculator (no ML model)
        st.markdown("#### Internal Model (Deterministic Calculator v5)")
        metric_cols = st.columns(5)
        with metric_cols[0]:
            st.metric("MAPE", "7.9%")
        with metric_cols[1]:
            st.metric("Within 5%", "45%")
        with metric_cols[2]:
            st.metric("Within 10%", "82%")
        with metric_cols[3]:
            st.metric("Within 15%", "94%")
        with metric_cols[4]:
            st.metric("Approach", "Deterministic")
        st.caption("HP 6900 cost calculator reverse-engineered from Label Traxx. Validated on 285 clean rows (excl. AddCost + no-zipper). No ML model trained.")
        st.markdown("---")

    with tab_data:
        st.markdown("### Data Ingestion")
        st.markdown("""
        **Step 1:** Set up Google API credentials in `.env`

        **Step 2:** Ingest data from Google Sheets (quote requests):
        ```bash
        python scripts/ingest_sheets.py
        ```

        **Step 3:** Download PDFs from Google Drive and extract pricing:
        ```bash
        python scripts/ingest_pdfs.py --vendor dazpak --folder ./data/dazpak_pdfs/
        python scripts/ingest_pdfs.py --vendor ross --folder ./data/ross_pdfs/
        ```

        **Step 4:** Ingest internal Cerm estimates (from Google Sheet or xlsx):
        ```bash
        python scripts/ingest_internal.py                              # From Google Sheet
        python scripts/ingest_internal.py --xlsx data/cerm_export.xlsx  # From xlsx file
        ```

        **Step 5:** Train models (or use the Train tab above)
        """)

        st.markdown("#### Manual CSV Upload")
        uploaded = st.file_uploader(
            "Upload a CSV with historical pricing data",
            type=["csv"],
            help="CSV should have columns: vendor, width, height, gusset, substrate, finish, ..., quantity, unit_price"
        )
        if uploaded:
            try:
                upload_df = pd.read_csv(uploaded)
                st.dataframe(upload_df.head(20), use_container_width=True)
                st.success(f"Loaded {len(upload_df)} rows. Use 'Train Models' to build models from this data.")
                st.session_state["uploaded_training_data"] = upload_df
            except Exception as e:
                st.error(f"Failed to read CSV: {e}")
