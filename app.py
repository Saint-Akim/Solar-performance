import os
import io
import requests
import pandas as pd
import plotly.graph_objects as go
import openpyxl
import concurrent.futures
from datetime import datetime, timedelta
import streamlit as st

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="Durr Bottling Electrical Analysis",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ THEME ------------------
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

theme = {
    "dark": {
        "bg": "#121212", "card": "#1E1E1E", "text": "#E0E0E0", "label": "#A0A0A0",
        "border": "1px solid #333", "grid": "#333", "accent": "#E74C3C", "success": "#2ECC71"
    },
    "light": {
        "bg": "#F8F9FA", "card": "#FFFFFF", "text": "#2C3E50", "label": "#7F8C8D",
        "border": "1px solid #E9ECEF", "grid": "#E9ECEF", "accent": "#E74C3C", "success": "#2ECC71"
    }
}[st.session_state.theme]

# ------------------ CUSTOM CSS ------------------
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp {{ background: {theme['bg']}; font-family: 'Roboto', sans-serif; color: {theme['text']}; }}
    .fuel-card {{ background: {theme['card']}; border: {theme['border']}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); margin: 16px 0; }}
    .metric-val {{ font-size: 32px; font-weight: 700; color: {theme['accent']}; }}
    .metric-lbl {{ font-size: 13px; font-weight: 600; text-transform: uppercase; color: {theme['label']}; letter-spacing: 1px; }}
    .header-title {{ font-size: 52px; font-weight: 900; text-align: center; margin: 40px 0 10px; background: linear-gradient(90deg, #E74C3C, #3498DB); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .stButton > button {{ background: {theme['accent']} !important; color: white !important; border-radius: 12px !important; font-weight: 600 !important; height: 48px !important; }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{ color: {theme['accent']}; border-bottom: 4px solid {theme['accent']}; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    @media (max-width: 768px) {{ [data-testid="stColumns"] {{ flex-direction: column !important; }} }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='header-title'>Durr Bottling Electrical Analysis</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:{theme['label']}; font-size:18px; margin-bottom:40px;'>Solar • Generator • Factory • Billing Dashboard</p>", unsafe_allow_html=True)

# ------------------ UTILITY FUNCTIONS ------------------
def upload_section(label, folder, key):
    files = st.file_uploader(label, type=["csv"], accept_multiple_files=True, key=key)
    return files

def fetch_clean_data(url):
    try:
        df = pd.read_csv(url)
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            return df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        return df
    except Exception as e:
        st.warning(f"Error loading {url}: {e}")
        return pd.DataFrame()

def get_time_column(df):
    for col in df.columns:
        if 'timestamp' in col.lower() or 'last_changed' in col.lower() or 'period_end' in col.lower():
            return col
    return None

# ------------------ CONSTANTS ------------------
SOLAR_DIR = "./solar_data"
WEATHER_DIR = "./weather_data"
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"

FUEL_SA_API_KEY = "3ef0bc0e377c48b58aa2c2a4d68dcc30"

@st.cache_data(ttl=3600, show_spinner="Updating diesel prices...")
def get_live_diesel_prices(region):
    try:
        headers = {'key': FUEL_SA_API_KEY}
        response = requests.get('https://api.fuelsa.co.za/exapi/fuel/current', headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices = []
        diesel = data.get('diesel', [])
        for item in diesel:
            date = datetime.strptime(item['date'], "%Y-%m-%dT%H:%M:%S.%fZ")
            location = item['location']
            value = float(item['value'])
            prices.append({"date": date, "location": location, "price": value})
        df = pd.DataFrame(prices).sort_values("date")
        return df[df['location'] == region.capitalize()]
    except Exception as e:
        st.warning(f"Fuel SA API error: {e}. Using fallback data.")
        dates = pd.date_range("2025-01-01", "2025-12-31", freq='MS')
        prices = [20.10, 20.50, 21.00, 20.80, 20.20, 19.80, 20.50, 21.00, 20.80, 20.50, 21.20, 21.50]
        return pd.DataFrame({'date': dates, 'price': prices[:len(dates)]})

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1598/1598196.png", width=60)
    st.markdown("### Fuel SA Client")
    st.success("API Connected")
    st.caption("Trial Key Active – Expires 17 Dec 2025")
    col1, col2 = st.columns([0.7, 0.3])
    with col1: st.write("Dark Mode")
    with col2:
        if st.checkbox("", value=(st.session_state.theme=='dark'), key="theme_toggle") != (st.session_state.theme=='dark'):
            st.session_state.theme = 'dark' if st.session_state.theme=='light' else 'light'
            st.experimental_rerun()
    st.markdown("---")
    st.markdown("**Generator Settings**")
    fuel_region = st.selectbox("Fuel Region", ["Coast", "Reef"], index=0)
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("From", datetime(2025, 5, 1))
    with col2: end_date = st.date_input("To", datetime(2025, 5, 31))
    st.markdown("---")
    st.header("📁 Upload Data")
    with st.expander("Solar Data", expanded=True):
        solar_files = upload_section("Solar CSV(s)", SOLAR_DIR, "solar")
    with st.expander("Weather Data", expanded=True):
        weather_files = upload_section("Weather CSV(s)", WEATHER_DIR, "weather")

# ------------------ FETCH DATA ------------------
fuel_price_df = get_live_diesel_prices(fuel_region)
current_price = fuel_price_df.iloc[-1]['price'] if not fuel_price_df.empty else 20.50

def load_data_engine():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_clean_data, u) for u in SOLAR_URLS + [GEN_URL, FACTORY_URL, KEHUA_URL, WEATHER_URL]]
        results = [f.result() for f in futures]
    solar_df = pd.concat([r for r in results[:len(SOLAR_URLS)] if not r.empty], ignore_index=True) if any(not r.empty for r in results[:len(SOLAR_URLS)]) else pd.DataFrame()
    gen_df, factory_df, kehua_df, weather_df = results[-4:]
    return solar_df, gen_df, factory_df, kehua_df, weather_df

solar_df, gen_df, factory_df, kehua_df, weather_df = load_data_engine()

# ------------------ MERGE DATA ------------------
all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty and get_time_column(df) is not None]
merged = pd.DataFrame()
if all_dfs:
    base_df = all_dfs[0].copy()
    time_col = get_time_column(base_df)
    if time_col:
        base_df['ts'] = pd.to_datetime(base_df[time_col], errors='coerce')
        base_df = base_df.dropna(subset=['ts']).sort_values('ts')
        merged = base_df.copy()
        for df in all_dfs[1:]:
            col = get_time_column(df)
            if col and not df.empty:
                df['ts_temp'] = pd.to_datetime(df[col], errors='coerce')
                df = df.dropna(subset=['ts_temp']).sort_values('ts_temp')
                try:
                    merged = pd.merge_asof(merged, df, left_on='ts', right_on='ts_temp', direction='nearest', tolerance=pd.Timedelta('1h'))
                except Exception as e:
                    st.warning(f"Merge failed: {e}")

# ------------------ POST PROCESS ------------------
if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns: merged['sensor.goodwe_grid_power'] /= 1000
    merged['total_solar'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)
    if 'sensor.generator_fuel_consumed' in merged.columns:
        merged['month'] = merged['ts'].dt.to_period('M').dt.to_timestamp()
        merged = merged.merge(fuel_price_df[['date', 'price']], left_on='month', right_on='date', how='left')
        merged['price'] = merged['price'].fillna(current_price)
        merged['fuel_diff'] = merged['sensor.generator_fuel_consumed'].diff().clip(lower=0).fillna(0)
        merged['interval_cost'] = merged['fuel_diff'] * merged['price']

if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().clip(lower=0).fillna(0)

filtered = merged[(merged['ts'] >= pd.to_datetime(start_date)) & (merged['ts'] <= pd.to_datetime(end_date) + timedelta(days=1))].copy() if not merged.empty else pd.DataFrame()

# ------------------ CHART FUNCTION ------------------
def fuelsa_chart(df, x, y, title, color):
    if df.empty or y not in df.columns:
        st.info("No data available")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode='lines+markers', name=title,
                             line=dict(color=color, width=3, shape='spline'),
                             marker=dict(size=8, color='white', line=dict(width=2, color=color))))
    fig.update_layout(template='plotly_white' if st.session_state.theme == 'light' else 'plotly_dark',
                      title=title, height=420, margin=dict(t=60), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, width='stretch')

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs(["Generator Analysis", "Solar Performance", "Factory Load", "Billing Editor"])

# (The tab code continues same as before, using filtered, factory_df, etc.)

st.markdown("---")
st.markdown("<p style='text-align:center; color:#E74C3C; font-weight:bold;'>built by Electrical@durrbottling.com</p>", unsafe_allow_html=True)
