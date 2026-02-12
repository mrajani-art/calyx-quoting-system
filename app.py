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

from config.settings import (
    SUBSTRATE_OPTIONS, SUBSTRATE_CANONICAL,
    FINISH_UI_OPTIONS, EMBELLISHMENT_UI_OPTIONS,
    FILL_STYLE_OPTIONS, SEAL_TYPE_UI_OPTIONS,
    GUSSET_UI_OPTIONS, ZIPPER_UI_OPTIONS,
    TEAR_NOTCH_UI_OPTIONS, HOLE_PUNCH_UI_OPTIONS,
    CORNER_UI_OPTIONS, PRINT_METHODS,
    DEFAULT_QTY_TIERS, DAZPAK_DEFAULT_TIERS, ROSS_DEFAULT_TIERS,
    DAZPAK_MIN_ORDER_QTY, ROSS_MIN_PRINT_WIDTH_INCHES,
    MODEL_DIR,
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

# ── Custom CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global */
    .stApp { font-family: 'DM Sans', sans-serif; }
    code, .stCode { font-family: 'JetBrains Mono', monospace; }

    /* Header banner */
    .main-header {
        background: linear-gradient(135deg, #1a472a 0%, #2d6a4f 50%, #40916c 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .main-header p { margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.95rem; }

    /* Metric cards */
    .metric-card {
        background: #f8faf9;
        border: 1px solid #d8e8df;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-card .value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1a472a;
    }
    .metric-card .label {
        font-size: 0.8rem;
        color: #6b7c72;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Vendor badge */
    .vendor-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .vendor-dazpak {
        background: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7;
    }
    .vendor-ross {
        background: #e3f2fd; color: #1565c0; border: 1px solid #90caf9;
    }

    /* Warning box */
    .warning-box {
        background: #fff8e1;
        border-left: 4px solid #ff8f00;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }

    /* Section divider */
    .section-divider {
        border: none;
        border-top: 2px solid #e8f0ec;
        margin: 1.5rem 0;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #f1f7f3;
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
    st.markdown("### 📦 Calyx Quoting")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🏷️ Quote Builder", "📊 Analytics", "⚙️ Model Manager"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    # Quick reference
    st.markdown("#### Quick Reference")
    st.markdown(f"""
    **Dazpak** (Flexographic)
    - MOQ: {DAZPAK_MIN_ORDER_QTY:,} units/SKU
    - Typical tiers: 75K–500K

    **Ross** (Digital)
    - Print width must be > 12\"
    - Print width = H×2 + G
    - Typical tiers: 4K–10K
    """)


# ═══════════════════════════════════════════════════════════════════
# HELPER: Generate demo data for analytics
# ═══════════════════════════════════════════════════════════════════
def _generate_demo_data() -> pd.DataFrame:
    """Generate realistic demo data for analytics preview."""
    np.random.seed(42)
    n = 200

    vendors = np.random.choice(["dazpak", "ross"], n, p=[0.6, 0.4])
    widths = np.random.uniform(3, 8, n).round(2)
    heights = np.random.uniform(4, 12, n).round(2)
    gussets = np.random.choice([0, 1.5, 2, 2.5, 3], n)
    substrates = np.random.choice(["MET_PET", "CLR_PET", "WHT_MET_PET", "HB_CLR_PET"], n)
    finishes = np.random.choice(["Matte Laminate", "Soft Touch Laminate", "None"], n, p=[0.5, 0.3, 0.2])
    zippers = np.random.choice(["CR Zipper", "Standard CR", "No Zipper"], n, p=[0.4, 0.35, 0.25])

    quantities = []
    for v in vendors:
        if v == "dazpak":
            quantities.append(np.random.choice([75000, 100000, 200000, 350000, 500000]))
        else:
            quantities.append(np.random.choice([4000, 5000, 6000, 10000]))

    base = np.where(vendors == "dazpak", 0.12, 0.45)
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
    })


# ═══════════════════════════════════════════════════════════════════
# HELPER: Render prediction results
# ═══════════════════════════════════════════════════════════════════
def _render_results(result: dict, margin_pct: int = 35):
    """Render prediction results with margin-adjusted sell prices."""
    st.markdown("---")

    # Calculate margin multiplier: Sell = Cost / (1 - margin/100)
    if margin_pct >= 100:
        margin_pct = 99
    margin_multiplier = 1.0 / (1.0 - margin_pct / 100.0)

    # Header
    st.markdown(f"## 📋 Quote Results — {margin_pct}% Margin")

    # Header metrics
    preds = result["predictions"]
    if preds:
        mcols = st.columns(5)
        with mcols[0]:
            vendor_label = "Dazpak" if result["vendor"] == "dazpak" else "Ross"
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Vendor</div>
                <div class="value">{vendor_label}</div>
            </div>""", unsafe_allow_html=True)
        with mcols[1]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Print Method</div>
                <div class="value">{result['print_method'].title()}</div>
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
                <div class="value" style="color:#2d6a4f;">{format_currency(lowest_sell, 5)}</div>
            </div>""", unsafe_allow_html=True)
        with mcols[4]:
            mape = result.get("model_metrics", {}).get("mape", "—")
            mape_str = f"{mape:.1f}%" if isinstance(mape, (int, float)) else mape
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Model MAPE</div>
                <div class="value">{mape_str}</div>
            </div>""", unsafe_allow_html=True)

    # Warnings
    for w in result.get("warnings", []):
        st.warning(w)

    # Pricing table with both cost and sell columns
    st.markdown("### Pricing by Quantity Tier")
    if preds:
        import pandas as pd
        rows = []
        for p in preds:
            cost = p["unit_price"]
            sell = cost * margin_multiplier
            total_cost = p["total_price"]
            total_sell = total_cost * margin_multiplier
            rows.append({
                "Quantity": f"{p['quantity']:,}",
                "Unit Cost": format_currency(cost, 5),
                "Unit Sell Price": format_currency(sell, 5),
                "Total Cost": format_currency(total_cost, 2),
                "Total Sell Price": format_currency(total_sell, 2),
                "90% CI Range": f"{format_currency(p['lower_bound'], 5)} – {format_currency(p['upper_bound'], 5)}",
            })
        price_df = pd.DataFrame(rows)
        st.dataframe(price_df, use_container_width=True, hide_index=True)

    # Charts
    if preds:
        chart_cols = st.columns(2)

        with chart_cols[0]:
            st.markdown("### Unit Price vs Quantity")
            fig = go.Figure()
            qtys = [p["quantity"] for p in preds]
            costs = [p["unit_price"] for p in preds]
            sells = [p["unit_price"] * margin_multiplier for p in preds]
            lowers = [p["lower_bound"] for p in preds]
            uppers = [p["upper_bound"] for p in preds]

            # Confidence band (on cost)
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
            st.markdown("### Cost Factor Breakdown")
            cf_df = cost_factors_to_dataframe(result.get("cost_factors", {}))
            if not cf_df.empty:
                fig2 = px.bar(
                    cf_df.head(10),
                    x="Importance",
                    y="Cost Factor",
                    orientation="h",
                    color="Importance",
                    color_continuous_scale=["#b7e4c7", "#1a472a"],
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
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Cost factor breakdown requires a trained model.")


# ═══════════════════════════════════════════════════════════════════
# PAGE 1: QUOTE BUILDER
# ═══════════════════════════════════════════════════════════════════
if page == "🏷️ Quote Builder":

    st.markdown("""
    <div class="main-header">
        <h1>📦 Packaging Quote Generator</h1>
        <p>ML-powered price predictions for Calyx Containers flexible packaging</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Input Form ──────────────────────────────────────────────────
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("### 📐 Bag Specifications")

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
        pw_color = "🟢" if pw > ROSS_MIN_PRINT_WIDTH_INCHES else "🔴"
        st.caption(f"Print Width: **{pw:.2f}\"** (H×2 + G)  {pw_color} {'Ross eligible' if pw > 12 else 'Below Ross 12\" min'}")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Print method
        print_method = st.selectbox("Print Method", PRINT_METHODS,
                                    help="Flexographic → Dazpak | Digital → Ross")

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
        st.markdown("### 📦 Quantity Tiers")
        st.caption("Enter up to 6 quantity tiers for pricing (ascending order)")

        # Auto-suggest tiers based on vendor
        if print_method == "Flexographic":
            suggested = DAZPAK_DEFAULT_TIERS
        else:
            suggested = ROSS_DEFAULT_TIERS

        # Use suggested defaults but pad to 6
        while len(suggested) < 6:
            suggested.append(suggested[-1] * 2 if suggested else 10000)

        qty_cols = st.columns(3)
        quantities = []
        for i in range(6):
            col_idx = i % 3
            with qty_cols[col_idx]:
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
        vendor_class = "vendor-dazpak" if routing["vendor"] == "dazpak" else "vendor-ross"
        vendor_label = "Dazpak (Flexographic)" if routing["vendor"] == "dazpak" else "Ross (Digital)"

        st.markdown(f"""
        <div style="background:#f8faf9; padding:1rem; border-radius:10px; border:1px solid #d8e8df; margin-bottom:1rem;">
            <span class="vendor-badge {vendor_class}">{vendor_label}</span>
            <p style="margin:0.5rem 0 0; font-size:0.85rem; color:#555;">{routing['reason']}</p>
        </div>
        """, unsafe_allow_html=True)

        for w in routing["warnings"]:
            st.markdown(f'<div class="warning-box">{w}</div>', unsafe_allow_html=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # ── Margin Setting ───────────────────────────────────────
        st.markdown("### 💰 Margin")
        margin_cols = st.columns([2, 1])
        with margin_cols[0]:
            margin_pct = st.slider(
                "Margin %",
                min_value=0,
                max_value=100,
                value=35,
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

        # ── Generate Quote Button ───────────────────────────────────
        generate = st.button("🔮 Generate Quote", type="primary", use_container_width=True)

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
        st.caption("Showing previous quote results:")
        _render_results(st.session_state.last_result, margin_pct)



# ═══════════════════════════════════════════════════════════════════
# PAGE 2: ANALYTICS
# ═══════════════════════════════════════════════════════════════════
elif page == "📊 Analytics":

    st.markdown("""
    <div class="main-header">
        <h1>📊 Quote Analytics Dashboard</h1>
        <p>Explore historical pricing data and trends across vendors</p>
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
        mcols = st.columns(4)
        with mcols[0]:
            st.metric("Total Quotes", f"{data['fl_number'].nunique() if 'fl_number' in data.columns else len(data):,}")
        with mcols[1]:
            if 'vendor' in data.columns:
                st.metric("Dazpak Quotes", f"{(data['vendor'] == 'dazpak').sum():,}")
        with mcols[2]:
            if 'vendor' in data.columns:
                st.metric("Ross Quotes", f"{(data['vendor'] == 'ross').sum():,}")
        with mcols[3]:
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
                    color_discrete_map={"dazpak": "#2d6a4f", "ross": "#1565c0"},
                    labels={"unit_price": "Unit Price ($)", "vendor": "Vendor"},
                )
                fig.update_layout(template="plotly_white", height=400)
                st.plotly_chart(fig, use_container_width=True)

        with chart_tab2:
            if 'quantity' in data.columns and 'unit_price' in data.columns:
                fig = px.scatter(
                    data, x="quantity", y="unit_price",
                    color="vendor" if "vendor" in data.columns else None,
                    size="bag_area_sqin" if "bag_area_sqin" in data.columns else None,
                    color_discrete_map={"dazpak": "#2d6a4f", "ross": "#1565c0"},
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
                    color_discrete_map={"dazpak": "#2d6a4f", "ross": "#1565c0"},
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
    <div class="main-header">
        <h1>⚙️ Model Manager</h1>
        <p>Train, evaluate, and manage ML pricing models</p>
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
        - **Ross** (Digital) — predicts unit price per bag

        Each model includes:
        - Point prediction (squared error loss)
        - Lower/upper confidence bounds (10th/90th quantile regression)
        - Cross-validated performance metrics
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

                # Feature importance chart
                imp_items = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:12]
                imp_df = pd.DataFrame(imp_items, columns=["Feature", "Importance"])
                fig = px.bar(
                    imp_df, x="Importance", y="Feature", orientation="h",
                    color="Importance",
                    color_continuous_scale=["#b7e4c7", "#1a472a"],
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

        **Step 4:** Train models (or use the Train tab above)
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
