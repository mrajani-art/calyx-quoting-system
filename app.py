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
        mcols = st.columns(5)
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
            lowest_cost = min(p["unit_price"] for p in preds)
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Best Cost</div>
                <div class="value">{format_currency(lowest_cost, 5)}</div>
            </div>""", unsafe_allow_html=True)
        with mcols[3]:
            lowest_sell = lowest_cost * margin_multiplier
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Best Sell Price</div>
                <div class="value">{format_currency(lowest_sell, 5)}</div>
            </div>""", unsafe_allow_html=True)
        with mcols[4]:
            mape = result.get("model_metrics", {}).get("mape", None)
            is_det = result.get("is_deterministic", False)

            # Calculate confidence rating from MAPE
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
        st.markdown(table_html, unsafe_allow_html=True)

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

    # Charts
    if preds:
        is_det = result.get("is_deterministic", False)
        chart_cols = st.columns(2)

        with chart_cols[0]:
            st.markdown('<div class="results-header">Unit Price vs Quantity</div>', unsafe_allow_html=True)
            fig = go.Figure()
            qtys = [p["quantity"] for p in preds]
            costs = [p["unit_price"] for p in preds]
            sells = [p["unit_price"] * margin_multiplier for p in preds]

            if not is_det:
                # Confidence band (only for ML models)
                lowers = [p["lower_bound"] for p in preds]
                uppers = [p["upper_bound"] for p in preds]
                fig.add_trace(go.Scatter(
                    x=qtys + qtys[::-1],
                    y=uppers + lowers[::-1],
                    fill="toself",
                    fillcolor="rgba(45, 106, 79, 0.08)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="90% CI (Cost)",
                    showlegend=True,
                ))

            # Cost line
            fig.add_trace(go.Scatter(
                x=qtys, y=costs,
                mode="lines+markers",
                line=dict(color="#9e9e9e", width=2, dash="dot"),
                marker=dict(size=7, color="#9e9e9e"),
                name="Cost",
            ))
            # Sell price line
            fig.add_trace(go.Scatter(
                x=qtys, y=sells,
                mode="lines+markers",
                line=dict(color="#2d6a4f", width=3),
                marker=dict(size=10, color="#1a472a"),
                name=f"Sell Price ({margin_pct}% margin)",
            ))
            fig.update_layout(
                xaxis_title="Quantity",
                yaxis_title="Unit Price ($)",
                template="plotly_white",
                height=350,
                margin=dict(l=40, r=20, t=20, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

        with chart_cols[1]:
            st.markdown('<div class="results-header">Cost Factor Breakdown</div>', unsafe_allow_html=True)
            cf_df = cost_factors_to_dataframe(result.get("cost_factors", {}))
            if not cf_df.empty:
                fig2 = px.bar(
                    cf_df.head(10),
                    x="Importance",
                    y="Cost Factor",
                    orientation="h",
                    color="Importance",
                    color_continuous_scale=["#d1d5db", "#1a472a"],
                    text="Your Value",
                )
                fig2.update_layout(
                    template="plotly_white",
                    height=350,
                    margin=dict(l=40, r=20, t=20, b=40),
                    showlegend=False,
                    coloraxis_showscale=False,
                    yaxis=dict(autorange="reversed"),
                )
                if is_det:
                    fig2.update_layout(
                        xaxis_title="% of Total Cost",
                    )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Cost factor breakdown requires a trained model.")

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
    cust_cols = st.columns([2, 1])
    with cust_cols[0]:
        customer_name = st.text_input("Customer Name", value="", placeholder="Enter customer name")
    with cust_cols[1]:
        calyx_rep = st.selectbox("Calyx Rep", CALYX_REPS)

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

        # Print method
        print_method = st.selectbox("Print Method", PRINT_METHODS,
                                    help="Flexographic → Dazpak | Digital: ≤12\" → Internal, >12\" → Ross")

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
                    q = st.number_input(
                        f"Tier {i+1}",
                        min_value=0,
                        value=default,
                        step=1000,
                        key=f"qty_{i}",
                    )
                    if q > 0:
                        quantities.append(q)

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
