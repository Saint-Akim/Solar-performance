import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
import io

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & THEME STATE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Southern Paarl Energy",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State for Theme
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

def toggle_theme():
    if st.session_state.theme == 'light':
        st.session_state.theme = 'dark'
    else:
        st.session_state.theme = 'light'

# -----------------------------------------------------------------------------
# 2. CSS STYLING (DYNAMIC LIGHT/DARK)
# -----------------------------------------------------------------------------
# Define colors based on state
if st.session_state.theme == 'dark':
    bg_color = "#0e1117"
    card_color = "#262730"
    text_color = "#fafafa"
    sidebar_bg = "#161b22"
    border_color = "rgba(255,255,255,0.1)"
    chart_template = "plotly_dark"
    shadow = "0 4px 20px rgba(0,0,0,0.5)"
    title_gradient = "linear-gradient(90deg, #00D4FF, #00FF88)"
else:
    bg_color = "#f8f9fb"
    card_color = "#ffffff"
    text_color = "#1d1d1f"
    sidebar_bg = "#ffffff"
    border_color = "#e8e8e8"
    chart_template = "plotly_white"
    shadow = "0 8px 30px rgba(0,0,0,0.08)"
    title_gradient = "linear-gradient(90deg, #007AFF, #00C853)"

st.markdown(f"""
<style>
    /* Main Background */
    .stApp {{
        background-color: {bg_color} !important;
    }}
    
    /* Sidebar Background */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 1px solid {border_color} !important;
    }}
    
    /* Card Style */
    .energy-card {{
        background-color: {card_color} !important;
        border-radius: 20px !important;
        padding: 24px !important;
        margin-bottom: 20px !important;
        box-shadow: {shadow} !important;
        border: 1px solid {border_color} !important;
    }}
    
    /* Typography */
    h1, h2, h3, p, div, span, label {{
        color: {text_color} !important;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}
    
    /* Header Gradient */
    .header-title {{
        font-size: 42px !important;
        font-weight: 800 !important;
        background: {title_gradient} !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-align: center !important;
        margin-top: 20px !important;
    }}
    
    /* Metrics */
    .metric-value {{
        font-size: 32px !important;
        font-weight: 700 !important;
        color: {text_color} !important;
    }}
    .metric-label {{
        font-size: 14px !important;
        color: #888 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }}

</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS (DATA LOADING)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300) # Cache for 5 minutes
def load_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text))
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# URLs
SOLAR_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    # Profile
    st.markdown(f"""
    <div style="text-align:center; padding:20px 0;">
        <div style="width:70px; height:70px; background:{title_gradient}; border-radius:50%; margin:0 auto 15px; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:24px;">
            HA
        </div>
        <div style="font-weight:700; font-size:20px; color:{text_color};">Hussein Akim</div>
    </div>
    """, unsafe_allow_html=True)

    # Theme Switcher
    st.markdown("### Appearance")
    is_dark = st.session_state.theme == 'dark'
    if st.toggle("Dark Mode", value=is_dark):
        if st.session_state.theme == 'light':
            st.session_state.theme = 'dark'
            st.rerun()
    else:
        if st.session_state.theme == 'dark':
            st.session_state.theme = 'light'
            st.rerun()

    st.markdown("---")
    
    # Inputs (FIXED LABELS)
    st.markdown("### Settings")
    gti_factor = st.slider("GTI Factor", 0.50, 1.50, 1.00, 0.01)
    pr_ratio = st.slider("Performance Ratio", 0.50, 1.00, 0.80, 0.01)
    cost_per_unit = st.number_input("Cost per kWh (ZAR)", min_value=0.0, value=2.98, step=0.01)
    
    st.markdown("### Date Filter")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime(2025, 5, 1))
    with col2:
        end_date = st.date_input("End Date", datetime(2025, 5, 31))

    st.markdown("---")
    page = st.radio("Navigation", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")

# -----------------------------------------------------------------------------
# 5. MAIN CONTENT
# -----------------------------------------------------------------------------
st.markdown("<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:#888; font-size:18px; margin-bottom:30px;'>Dashboard • {page}</p>", unsafe_allow_html=True)

# --- SOLAR TAB ---
if page == "Solar":
    df = load_data(SOLAR_URL)
    if not df.empty:
        # Process
        df['last_changed'] = pd.to_datetime(df['last_changed'])
        mask = (df['last_changed'].dt.date >= start_date) & (df['last_changed'].dt.date <= end_date)
        df_filtered = df.loc[mask].copy()
        
        df_filtered['total_power_kw'] = (df_filtered['sensor.goodwe_grid_power'].fillna(0) + df_filtered['sensor.fronius_grid_power'].fillna(0)) / 1000

        # KPI Cards
        avg_power = df_filtered['total_power_kw'].mean()
        max_power = df_filtered['total_power_kw'].max()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class='energy-card'><div class='metric-label'>Avg Output</div><div class='metric-value'>{avg_power:.2f} kW</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class='energy-card'><div class='metric-label'>Max Peak</div><div class='metric-value'>{max_power:.2f} kW</div></div>""", unsafe_allow_html=True)
        with c3:
            cost = (df_filtered['total_power_kw'].sum() / 60) * cost_per_unit # Approximation
            st.markdown(f"""<div class='energy-card'><div class='metric-label'>Est. Savings</div><div class='metric-value'>R {cost:.2f}</div></div>""", unsafe_allow_html=True)

        # Chart
        st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
        st.subheader("Solar Output (Goodwe + Fronius)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_filtered['last_changed'], y=df_filtered['total_power_kw'], 
                                 mode='lines', name='Total kW', line=dict(color='#00C853', width=2)))
        fig.update_layout(template=chart_template, height=450, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# --- GENERATOR TAB ---
elif page == "Generator":
    df = load_data(GEN_URL)
    if not df.empty:
        df['last_changed'] = pd.to_datetime(df['last_changed'])
        mask = (df['last_changed'].dt.date >= start_date) & (df['last_changed'].dt.date <= end_date)
        df_filtered = df.loc[mask].copy()

        st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
        st.subheader("Fuel Consumption")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_filtered['last_changed'], y=df_filtered['sensor.generator_fuel_consumed'], 
                                 line=dict(color='#FF3B30', width=2), name="Fuel (L)"))
        fig.update_layout(template=chart_template, height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# --- FACTORY TAB ---
elif page == "Factory":
    df = load_data(FACTORY_URL)
    if not df.empty:
        df['last_changed'] = pd.to_datetime(df['last_changed'])
        mask = (df['last_changed'].dt.date >= start_date) & (df['last_changed'].dt.date <= end_date)
        df_filtered = df.loc[mask].copy()
        
        # Calculate daily usage from cumulative
        df_filtered['daily_usage'] = df_filtered['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)
        df_filtered = df_filtered[df_filtered['daily_usage'] >= 0] # Remove reset spikes

        st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
        st.subheader("Factory Consumption (Daily kWh)")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_filtered['last_changed'], y=df_filtered['daily_usage'], 
                             marker_color='#007AFF', name="kWh"))
        fig.update_layout(template=chart_template, height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# --- KEHUA TAB ---
elif page == "Kehua":
    df = load_data(KEHUA_URL)
    if not df.empty:
        df['last_changed'] = pd.to_datetime(df['last_changed'])
        mask = (df['last_changed'].dt.date >= start_date) & (df['last_changed'].dt.date <= end_date)
        df_filtered = df.loc[mask].copy()
        
        st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
        st.subheader("Internal Power Load")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_filtered['last_changed'], y=df_filtered['sensor.kehua_internal_power']/1000, 
                                 line=dict(color='#5856D6', width=2), fill='tozeroy', name="kW"))
        fig.update_layout(template=chart_template, height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# --- BILLING TAB ---
elif page == "Billing":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Billing Editor")
    # Using a placeholder Google Sheet - replace 'src' with your actual embed link if you have it
    # To get your link: Open Sheet -> File -> Share -> Publish to Web -> Embed
    st.markdown("""
        <iframe src="https://docs.google.com/spreadsheets/d/e/2PACX-1vR_sO-mIXXCqgVwS5a4iJjK6l-gG7nFk/pubhtml?widget=true&headers=false" 
        style="width:100%; height:600px; border-radius:12px; border:none;"></iframe>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(f"<div style='text-align:center; color:#888; padding:20px;'>   • Durr Bottling • December 2025</div>", unsafe_allow_html=True)
