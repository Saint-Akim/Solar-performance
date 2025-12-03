# app.py — Southern Paarl Energy Dashboard (Professional Edition)
# 🚀 Performance: Parallel Data Loading added
# 🎨 UI: Clean Corporate Design + Fixed Calendar Contrast

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
import concurrent.futures
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
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

# -----------------------------------------------------------------------------
# 2. PROFESSIONAL UI DESIGN SYSTEM (CSS)
# -----------------------------------------------------------------------------
# Design Tokens
if st.session_state.theme == 'dark':
    # Dark Mode (Gunmetal & Slate)
    colors = {
        "bg": "#0e1117",
        "sidebar": "#161b22",
        "card": "#1f242d",
        "text": "#f0f6fc",
        "subtext": "#8b949e",
        "border": "1px solid #30363d",
        "primary": "#238636", # Professional Green
        "chart_theme": "plotly_dark",
        "shadow": "0 4px 12px rgba(0,0,0,0.5)"
    }
else:
    # Light Mode (Clean White & Royal Blue)
    colors = {
        "bg": "#f4f6f8",
        "sidebar": "#ffffff",
        "card": "#ffffff",
        "text": "#1a1c20",
        "subtext": "#5e6c84",
        "border": "1px solid #e1e4e8",
        "primary": "#0052cc", # Royal Blue
        "chart_theme": "plotly_white",
        "shadow": "0 2px 8px rgba(0,0,0,0.04)"
    }

# Inject CSS
st.markdown(f"""
<style>
    /* Global App Background */
    .stApp {{
        background-color: {colors['bg']};
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {colors['sidebar']};
        border-right: {colors['border']};
    }}
    
    /* Typography */
    h1, h2, h3, p, div, span, label, .stMarkdown {{
        color: {colors['text']} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}
    
    /* Professional Cards */
    .energy-card {{
        background-color: {colors['card']};
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: {colors['shadow']};
        border: {colors['border']};
    }}
    
    /* Header Styling */
    .header-title {{
        font-size: 36px;
        font-weight: 700;
        color: {colors['text']} !important;
        margin-top: 10px;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }}
    
    /* Input Fields (Fixing the Black Calendar Issue) */
    /* We style the CONTAINER, not the internal input, to avoid breaking calendars */
    .stTextInput, .stNumberInput, .stDateInput {{
        color: {colors['text']};
    }}
    
    /* Buttons */
    .stButton > button {{
        background-color: {colors['primary']} !important;
        color: white !important;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: opacity 0.2s;
    }}
    .stButton > button:hover {{
        opacity: 0.9;
    }}

    /* Hide Streamlit Branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    # Profile Section
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; padding: 20px 0; border-bottom: {colors['border']}; margin-bottom: 20px;">
        <div style="width:48px; height:48px; background:{colors['primary']}; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:18px;">HA</div>
        <div>
            <div style="font-weight:600; font-size:16px; color:{colors['text']}">Hussein Akim</div>
            <div style="font-size:12px; color:{colors['subtext']}">Admin • Durr Bottling</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Dark Mode Toggle
    col_t1, col_t2 = st.columns([0.8, 0.2])
    with col_t1: st.write("Dark Mode")
    with col_t2: 
        if st.toggle("Theme", value=(st.session_state.theme == 'dark'), label_visibility="collapsed"):
            if st.session_state.theme == 'light':
                st.session_state.theme = 'dark'
                st.rerun()
        else:
            if st.session_state.theme == 'dark':
                st.session_state.theme = 'light'
                st.rerun()
    
    st.markdown(f"<div style='margin: 20px 0; border-top: {colors['border']}'></div>", unsafe_allow_html=True)

    # Controls
    st.caption("PARAMETERS")
    gti_factor = st.slider("GTI Factor", 0.50, 1.50, 1.00, 0.01)
    pr_ratio = st.slider("Performance Ratio", 0.50, 1.00, 0.80, 0.01)
    cost_per_unit = st.number_input("Cost (ZAR/kWh)", min_value=0.0, value=2.98, step=0.01)
    
    st.caption("TIMEFRAME")
    start_date = st.date_input("From", datetime(2025, 5, 1))
    end_date = st.date_input("To", datetime(2025, 5, 31))

    st.markdown(f"<div style='margin: 20px 0; border-top: {colors['border']}'></div>", unsafe_allow_html=True)
    
    # Navigation
    page = st.radio("DASHBOARD", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")

# -----------------------------------------------------------------------------
# 4. OPTIMIZED DATA LOADING (PARALLEL PROCESSING)
# -----------------------------------------------------------------------------
TOTAL_CAPACITY_KW = 221.43
TZ = 'Africa/Johannesburg'

SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"

# Helper to fetch single URL
def fetch_url(url):
    try:
        df = pd.read_csv(url)
        # Pre-process immediately to save memory/time later
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            piv = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            return piv
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner="Syncing Data...")
def load_all_data_parallel():
    # Use ThreadPool to download all CSVs at once (Faster)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Solar
        solar_futures = [executor.submit(fetch_url, url) for url in SOLAR_URLS]
        # Others
        gen_future = executor.submit(fetch_url, GEN_URL)
        factory_future = executor.submit(fetch_url, FACTORY_URL)
        kehua_future = executor.submit(fetch_url, KEHUA_URL)
        
        # Gather Solar
        solar_dfs = [f.result() for f in solar_futures if not f.result().empty]
        solar_final = pd.concat(solar_dfs, ignore_index=True) if solar_dfs else pd.DataFrame()
        
        return solar_final, gen_future.result(), factory_future.result(), kehua_future.result()

@st.cache_data
def load_weather_data(gti, pr):
    try:
        df = pd.read_csv(WEATHER_URL)
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        df['expected_power_kw'] = df['gti'] * gti * TOTAL_CAPACITY_KW * pr / 1000
        return df
    except Exception:
        return pd.DataFrame()

# Execute Data Load
solar_df, gen_df, factory_df, kehua_df = load_all_data_parallel()
weather_df = load_weather_data(gti_factor, pr_ratio)

# Post-processing Logic (Preserved)
if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
merged = pd.DataFrame()
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(col),
                               left_on='last_changed', right_on=col, direction='nearest')

if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns: merged['sensor.goodwe_grid_power'] /= 1000
    merged['sum_grid_power'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

# Time Filter
filtered = pd.DataFrame()
if not merged.empty:
    mask = (merged['last_changed'] >= pd.to_datetime(start_date)) & \
           (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged.loc[mask].copy()

# -----------------------------------------------------------------------------
# 5. UI COMPONENTS (CHARTS & CARDS)
# -----------------------------------------------------------------------------

def plot_metric(df, x, y, title, line_color):
    if df.empty or y not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No Data", showarrow=False)
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, 
                                 line=dict(color=line_color, width=3), fill='tozeroy', fillcolor=f"rgba{line_color[3:-1]}, 0.1)"))
        
        # Add Expected line only for Solar
        if 'expected_power_kw' in df.columns and "Actual" in title:
            fig.add_trace(go.Scatter(x=df[x], y=df['expected_power_kw'], name="Expected", 
                                     line=dict(color="#999", width=2, dash="dot")))

    fig.update_layout(
        template=colors['chart_theme'],
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=20, t=40, b=40),
        height=400,
        title=dict(text=title, font=dict(size=18, color=colors['text'])),
        hovermode="x unified",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=colors['subtext'], gridwidth=0.1)
    )
    return fig

# -----------------------------------------------------------------------------
# 6. LAYOUT RENDERING
# -----------------------------------------------------------------------------

# Title Section
st.markdown(f"""
    <div style="margin-bottom: 30px;">
        <h1 class="header-title">Southern Paarl Energy</h1>
        <p style="color:{colors['subtext']}; font-size:16px;">Overview • {page}</p>
    </div>
""", unsafe_allow_html=True)

# Content
if page == "Solar":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.plotly_chart(plot_metric(filtered, 'last_changed', 'sum_grid_power', "Solar Output (kW)", colors['primary']), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Fuel Consumption")
        st.plotly_chart(plot_metric(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel (L)", "#d32f2f"), use_container_width=True)
    with col2:
        st.subheader("Runtime")
        st.plotly_chart(plot_metric(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Hours", "#7b1fa2"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.plotly_chart(plot_metric(filtered, 'last_changed', 'daily_factory_kwh', "Factory Daily Load (kWh)", "#0288d1"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.plotly_chart(plot_metric(filtered, 'last_changed', 'sensor.kehua_internal_power', "Kehua Internal (kW)", "#00796b"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.markdown("### 📝 Invoice Editor")
    st.caption("September 2025 Cycle")
    
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
    except Exception:
        ws = None
        st.error("Billing file unavailable.")

    if ws:
        c1, c2, c3 = st.columns(3)
        with c1:
            b2 = ws['B2'].value or "30/09/25"
            from_date = st.date_input("From Date", value=datetime.strptime(b2, "%d/%m/%y").date())
            c7 = st.number_input("Freedom Village", value=float(ws['C7'].value or 0))
        with c2:
            to_date = st.date_input("To Date", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
            c9 = st.number_input("Boerdery", value=float(ws['C9'].value or 0))
        with c3:
            e9 = st.number_input("Boerdery Cost", value=float(ws['E9'].value or 0))
            g21 = st.number_input("Drakenstein", value=float(ws['G21'].value or 0))

        st.markdown("---")
        if st.button("Generate Invoice Preview"):
            # Update Logic Preserved
            ws['A1'].value = from_date.strftime("%b'%y")
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['C7'].value = c7; ws['C9'].value = c9
            ws['E9'].value = e9; ws['G21'].value = g21
            
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.session_state.edited = buf.getvalue()
            st.success("Invoice Updated!")
            
        if 'edited' in st.session_state:
            st.download_button("Download Updated XLSX", st.session_state.edited, file_name="Invoice_Sep25.xlsx")
    
    st.markdown("</div>", unsafe_allow_html=True)
