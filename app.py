"""
Non-Conformance (NC) Data Analysis Dashboard
Main Streamlit Application Entry Point

Author: Xander @ Calyx Containers
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging

# Local imports
from src.data_loader import load_nc_data, refresh_data
from src.kpi_cards import render_open_nc_status_tracker
from src.aging_analysis import render_aging_dashboard
from src.cost_analysis import render_cost_of_rework, render_cost_avoided
from src.customer_analysis import render_customer_analysis
from src.pareto_chart import render_issue_type_pareto
from src.utils import setup_logging, export_dataframe

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="NC Data Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        background-color: #f0f2f6;
        border-radius: 5px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A5F;
        color: white;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<h1 class="main-header">📊 Non-Conformance Analysis Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Calyx Containers Quality Management System</p>', unsafe_allow_html=True)
    
    # Sidebar controls
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80?text=Calyx+Containers", width=200)
        st.markdown("---")
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            refresh_data()
            st.success("Data refreshed successfully!")
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📅 Global Filters")
        
        # Load data for filter options
        try:
            df = load_nc_data()
            
            if df is not None and not df.empty:
                # Date range filter
                min_date = pd.to_datetime(df['Date Submitted']).min()
                max_date = pd.to_datetime(df['Date Submitted']).max()
                
                if pd.notna(min_date) and pd.notna(max_date):
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date()
                    )
                else:
                    date_range = None
                    st.warning("Date range unavailable")
                
                # External/Internal filter
                ext_int_options = ["All"] + sorted(df['External Or Internal'].dropna().unique().tolist())
                ext_int_filter = st.selectbox(
                    "External/Internal",
                    options=ext_int_options,
                    index=0
                )
                
                # Status filter
                status_options = ["All"] + sorted(df['Status'].dropna().unique().tolist())
                status_filter = st.selectbox(
                    "Status",
                    options=status_options,
                    index=0
                )
                
                # Priority filter
                priority_options = ["All"] + sorted(df['Priority'].dropna().unique().tolist())
                priority_filter = st.selectbox(
                    "Priority",
                    options=priority_options,
                    index=0
                )
                
                st.markdown("---")
                
                # Data info
                st.markdown("### 📈 Data Summary")
                st.metric("Total Records", len(df))
                st.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M"))
                
                # Export button
                st.markdown("---")
                if st.button("📥 Export Raw Data", use_container_width=True):
                    csv = export_dataframe(df)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"nc_data_export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                df = pd.DataFrame()
                date_range = None
                ext_int_filter = "All"
                status_filter = "All"
                priority_filter = "All"
                st.error("No data available. Check your connection.")
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            st.error(f"Error loading data: {str(e)}")
            df = pd.DataFrame()
            date_range = None
            ext_int_filter = "All"
            status_filter = "All"
            priority_filter = "All"
    
    # Apply filters to dataframe
    if not df.empty:
        filtered_df = df.copy()
        
        # Apply date filter
        if date_range and len(date_range) == 2:
            filtered_df['Date Submitted'] = pd.to_datetime(filtered_df['Date Submitted'], errors='coerce')
            mask = (
                (filtered_df['Date Submitted'].dt.date >= date_range[0]) &
                (filtered_df['Date Submitted'].dt.date <= date_range[1])
            )
            filtered_df = filtered_df[mask]
        
        # Apply External/Internal filter
        if ext_int_filter != "All":
            filtered_df = filtered_df[filtered_df['External Or Internal'] == ext_int_filter]
        
        # Apply Status filter
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['Status'] == status_filter]
        
        # Apply Priority filter
        if priority_filter != "All":
            filtered_df = filtered_df[filtered_df['Priority'] == priority_filter]
        
        # Store filtered data in session state
        st.session_state['filtered_df'] = filtered_df
        st.session_state['raw_df'] = df
        
        # Display filtered record count
        st.info(f"Showing {len(filtered_df):,} of {len(df):,} records based on filters")
        
        # Main dashboard tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📋 Open NCs Status",
            "⏱️ Aging Analysis",
            "💰 Cost of Rework",
            "✅ Cost Avoided",
            "👥 Customer Analysis",
            "📊 Issue Type Pareto"
        ])
        
        with tab1:
            render_open_nc_status_tracker(filtered_df)
        
        with tab2:
            render_aging_dashboard(filtered_df)
        
        with tab3:
            render_cost_of_rework(filtered_df)
        
        with tab4:
            render_cost_avoided(filtered_df)
        
        with tab5:
            render_customer_analysis(filtered_df)
        
        with tab6:
            render_issue_type_pareto(df, ext_int_filter)  # Pass raw df for internal filter
    
    else:
        st.warning("⚠️ No data available. Please check your Google Sheets connection and credentials.")
        
        with st.expander("🔧 Setup Instructions"):
            st.markdown("""
            ### How to Connect to Google Sheets
            
            1. **Create a Service Account** in Google Cloud Console
            2. **Enable Google Sheets API** for your project
            3. **Download the JSON credentials** file
            4. **Share your Google Sheet** with the service account email
            5. **Configure Streamlit Secrets** with your credentials
            
            See the README.md for detailed setup instructions.
            """)


if __name__ == "__main__":
    main()
