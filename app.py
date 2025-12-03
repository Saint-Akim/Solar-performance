import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
import concurrent.futures
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. APP CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Durr Bottling Energy",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed" # Collapsed for a cleaner "Web App" feel
)

# Custom CSS for "Platinum" Look
st.markdown("""
<style>
    /* IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* GLOBAL STYLES */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* HIDE STREAMLIT CHROME */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* CUSTOM METRIC CARDS */
    .metric-card {
        background-color: var(--background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.1);
        border-color: #007AFF;
    }
    .metric-label {
        font-size: 14px;
        color: #888;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        margin: 10px 0;
        color: var(--text-color);
    }

    /* TABS STYLING (Pills) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 10px;
        background-color: rgba(128, 128, 128, 0.1);
        border: none;
        color: inherit;
        font-weight: 600;
        padding: 0 20px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #007AFF;
        color: white;
    }

    /* INPUT FIELD FIXES */
    /* Ensure inputs have high contrast backgrounds */
    .stDateInput input, .stSelectbox div, .stNumberInput input {
        background-color: rgba(128, 128, 128, 0.05) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
    }
    
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. FAST DATA LOADING (PARALLEL)
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
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"

def fetch_url(url):
    try:
        df = pd.read_csv(url)
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            return df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        return df
    except: return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_data():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        s_futures = [executor.submit(fetch_url, u) for u in SOLAR_URLS]
        gen_fut = executor.submit(fetch_url, GEN_URL)
        fac_fut = executor.submit(fetch_url, FACTORY_URL)
        keh_fut = executor.submit(fetch_url, KEHUA_URL)
        
        s_dfs = [f.result() for f in s_futures if not f.result().empty]
        solar = pd.concat(s_dfs, ignore_index=True) if s_dfs else pd.DataFrame()
        return solar, gen_fut.result(), fac_fut.result(), keh_fut.result()

# Load Data Background
with st.spinner("Connecting to Durr Bottling Energy Systems..."):
    solar_df, gen_df, factory_df, kehua_df = load_data()

# Process Data Logic
all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df] if not df.empty]
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values('last_changed'),
                               on='last_changed', direction='nearest')
    
    if 'sensor.fronius_grid_power' in merged: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged: merged['sensor.goodwe_grid_power'] /= 1000
    merged['total_solar'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)
else:
    merged = pd.DataFrame()

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONTROLS (Clean)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=50)
    st.title("Settings")
    
    st.markdown("### 📅 Timeframe")
    start_date = st.date_input("From", datetime(2025, 5, 1))
    end_date = st.date_input("To", datetime(2025, 5, 31))
    
    st.markdown("### ⚙️ Parameters")
    cost_per_unit = st.number_input("Energy Cost (R/kWh)", value=2.98, step=0.01)
    
    st.info("System Live • v2.4")

# Filter Data
mask = (merged['last_changed'] >= pd.to_datetime(start_date)) & (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
filtered = merged.loc[mask].copy()

# -----------------------------------------------------------------------------
# 4. MAIN DASHBOARD LAYOUT
# -----------------------------------------------------------------------------
st.title("Durr Bottling Energy Dashboard")
st.markdown("Monitor real-time performance of Solar, Generator, and Factory consumption.")

# KPI ROW (Top of page)
k1, k2, k3, k4 = st.columns(4)

# Calculate KPIs safely
solar_avg = filtered['total_solar'].mean() if 'total_solar' in filtered else 0
gen_fuel = filtered['sensor.generator_fuel_consumed'].max() - filtered['sensor.generator_fuel_consumed'].min() if 'sensor.generator_fuel_consumed' in filtered else 0
factory_total = filtered['sensor.bottling_factory_monthkwhtotal'].max() - filtered['sensor.bottling_factory_monthkwhtotal'].min() if 'sensor.bottling_factory_monthkwhtotal' in filtered else 0
savings = (filtered['total_solar'].sum() / 60) * cost_per_unit if 'total_solar' in filtered else 0

def kpi_card(col, label, value):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

kpi_card(k1, "Avg Solar Output", f"{solar_avg:.1f} kW")
kpi_card(k2, "Est. Savings", f"R {savings:,.0f}")
kpi_card(k3, "Generator Fuel", f"{gen_fuel:.0f} L")
kpi_card(k4, "Factory Load", f"{factory_total:,.0f} kWh")

st.markdown("---")

# TABS FOR DETAILED VIEWS
tab_solar, tab_gen, tab_fac, tab_bill = st.tabs(["☀️ Solar", "⛽ Generator", "🏭 Factory", "📝 Billing"])

def clean_chart(df, x, y, name, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode='lines', name=name, 
                             line=dict(color=color, width=2), fill='tozeroy', fillcolor=f"rgba{color[3:-1]}, 0.1)"))
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20),
        height=400,
        hovermode="x unified",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#f0f0f0")
    )
    return fig

with tab_solar:
    st.subheader("Solar Performance Analysis")
    if not filtered.empty and 'total_solar' in filtered:
        st.plotly_chart(clean_chart(filtered, 'last_changed', 'total_solar', 'Solar Output', 'rgb(0, 122, 255)'), use_container_width=True)

with tab_gen:
    st.subheader("Generator Usage")
    if not filtered.empty:
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(clean_chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', 'Fuel (L)', 'rgb(255, 59, 48)'), use_container_width=True)
        with c2: st.plotly_chart(clean_chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', 'Runtime (h)', 'rgb(175, 82, 222)'), use_container_width=True)

with tab_fac:
    st.subheader("Factory Consumption Profile")
    if not filtered.empty and 'sensor.bottling_factory_monthkwhtotal' in filtered:
        # Calculate daily
        daily = filtered.resample('D', on='last_changed')['sensor.bottling_factory_monthkwhtotal'].max().diff().fillna(0)
        fig = go.Figure(go.Bar(x=daily.index, y=daily.values, marker_color='rgb(52, 199, 89)'))
        fig.update_layout(title="Daily Consumption (kWh)", template="plotly_white", height=400)
        st.plotly_chart(fig, use_container_width=True)

with tab_bill:
    st.subheader("Monthly Billing Editor")
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        
        c1, c2 = st.columns(2)
        with c1:
            val_c7 = st.number_input("Freedom Village (Unit 7)", value=float(ws['C7'].value or 0))
            val_c9 = st.number_input("Boerdery (Unit 9)", value=float(ws['C9'].value or 0))
        with c2:
            val_e9 = st.number_input("Boerdery Cost (R)", value=float(ws['E9'].value or 0))
            
        if st.button("Update Invoice Preview", type="primary"):
            ws['C7'].value = val_c7
            ws['C9'].value = val_c9
            ws['E9'].value = val_e9
            
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.success("Invoice recalculated successfully!")
            st.download_button("Download Updated Invoice", buf, "Invoice_Sep25.xlsx")
            
    except Exception as e:
        st.error(f"Billing System Offline: {e}")
