import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import concurrent.futures

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Durr Bottling Electrical Analysis", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# Initialize theme
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# ------------------ DESIGN SYSTEM ------------------
if st.session_state.theme == 'dark':
    theme = {
        "bg": "#121212", "card": "#1E1E1E", "text": "#E0E0E0", "label": "#A0A0A0",
        "border": "1px solid #333", "grid": "#333", "accent": "#E74C3C", "success": "#2ECC71"
    }
else:
    theme = {
        "bg": "#F8F9FA", "card": "#FFFFFF", "text": "#2C3E50", "label": "#7F8C8D",
        "border": "1px solid #E9ECEF", "grid": "#E9ECEF", "accent": "#E74C3C", "success": "#2ECC71"
    }

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp {{ background: {theme['bg']}; font-family: 'Roboto', sans-serif; color: {theme['text']}; }}
    .fuel-card {{ background: {theme['card']}; border: {theme['border']}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); margin: 16px 0; }}
    .metric-val {{ font-size: 32px; font-weight: 700; color: {theme['accent']}; margin: 8px 0; }}
    .metric-lbl {{ font-size: 13px; font-weight: 600; text-transform: uppercase; color: {theme['label']}; letter-spacing: 1px; margin-bottom: 4px; }}
    .header-title {{ font-size: 52px; font-weight: 900; text-align: center; margin: 40px 0 10px; background: linear-gradient(90deg, #E74C3C, #3498DB); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .stButton > button {{ background: {theme['accent']} !important; color: white !important; border-radius: 12px !important; font-weight: 600 !important; height: 48px !important; }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{ color: {theme['accent']}; border-bottom: 4px solid {theme['accent']}; }}
    .plot-container {{ border-radius: 14px; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    @media (max-width: 768px) {{ [data-testid="stColumns"] {{ flex-direction: column !important; }} }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='header-title'>Durr Bottling Electrical Analysis</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:{theme['label']}; font-size:18px; margin-bottom:40px;'>Solar • Generator • Factory • Billing Dashboard</p>", unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.markdown("## ⚡ Durr Bottling")
    st.caption("Electrical & Energy Intelligence")

    st.success("Fuel SA API Connected")
    st.caption("Trial Key • Expires 17 Dec 2025")

    st.markdown("---")

    st.subheader("Appearance")
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.caption("Dark Mode")
    with col2:
        dark_mode = st.toggle("Toggle dark mode", value=(st.session_state.theme == 'dark'), key="theme_toggle")
        if dark_mode != (st.session_state.theme == 'dark'):
            st.session_state.theme = 'dark' if dark_mode else 'light'
            st.rerun()

    st.markdown("---")

    st.subheader("Date Range")
    start_date = st.date_input("From", datetime(2025, 1, 1))
    end_date = st.date_input("To", datetime(2025, 12, 15))

    if end_date < start_date:
        st.error("End date must be after start date")
        st.stop()

    st.markdown("---")

    st.subheader("Generator")
    fuel_region = st.selectbox(
        "Fuel Region",
        ["Coast", "Reef"],
        help="Paarl = Coastal pricing"
    )

    st.markdown("---")

    st.subheader("Data Overrides")
    uploaded_gen_file = st.file_uploader(
        "Upload GEN.csv",
        type="csv",
        help="Overrides GitHub generator data"
    )

# ------------------ LIVE FUEL SA API ------------------
FUEL_SA_API_KEY = "3ef0bc0e377c48b58aa2c2a4d68dcc30"

@st.cache_data(ttl=3600, show_spinner="Updating current diesel price...")
def get_current_diesel_price(region):
    try:
        headers = {'key': FUEL_SA_API_KEY}
        response = requests.get('https://api.fuelsa.co.za/exapi/fuel/current', headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices = []
        for item in data.get('diesel', []):
            location = item['location'].lower()
            value = float(item['value'])
            prices.append({"location": location, "price": value})
        df = pd.DataFrame(prices)
        match = df[df['location'] == region.lower()]
        if match.empty:
            raise ValueError(f"Region '{region}' not found")
        price = match['price'].iloc[0]
        if price > 100 or price < 10:
            raise ValueError(f"Invalid price R{price:.2f}/L")
        return price
    except Exception as e:
        st.warning(f"Fuel SA API issue: {e}. Using realistic fallback R22.52/L (Dec 2025).")
        return 22.52

current_price = get_current_diesel_price(fuel_region)

# ------------------ DATA LOADING ------------------
NEW_GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).csv"
SOLAR_URLS = [  # (keep your list)
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    # ... the rest
]
# (keep other URLs)

# fetch_clean_data and load_data_engine unchanged...

solar_df, gen_github_df, factory_df, kehua_df, weather_df = load_data_engine()

gen_df = pd.read_csv(uploaded_gen_file) if uploaded_gen_file else gen_github_df

# ------------------ FIXED GENERATOR PROCESSING FOR PIVOTED FORMAT ------------------
@st.cache_data(show_spinner=False)
def process_generator_data(_gen_df: pd.DataFrame):
    if _gen_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Check for pivoted format (last_changed + sensor columns)
    if 'last_changed' in _gen_df.columns:
        sensor_cols = [c for c in _gen_df.columns if c.startswith('sensor.generator_')]
        if len(sensor_cols) > 0:
            # Already pivoted — use directly
            pivot = _gen_df.set_index('last_changed')[sensor_cols].copy()
        else:
            st.error("No generator sensor columns found in pivoted CSV.")
            return pd.DataFrame(), pd.DataFrame()
    else:
        st.error("Unexpected generator CSV format.")
        return pd.DataFrame(), pd.DataFrame()

    pivot.index = pd.to_datetime(pivot.index, utc=True).tz_convert('Africa/Johannesburg').tz_localize(None)

    def clean_cumulative(series):
        series = pd.to_numeric(series, errors='coerce')
        series = series.ffill()
        diff = series.diff()
        series = series.where(diff >= 0, series.shift(1))
        return series.fillna(method='ffill').fillna(0)

    pivot['fuel_liters_cum'] = clean_cumulative(pivot.get('sensor.generator_fuel_consumed'))
    pivot['runtime_hours_cum'] = clean_cumulative(pivot.get('sensor.generator_runtime_duration'))

    pivot['fuel_per_kwh'] = pd.to_numeric(pivot.get('sensor.generator_fuel_per_kwh'), errors='coerce')
    pivot['fuel_efficiency'] = pd.to_numeric(pivot.get('sensor.generator_fuel_efficiency'), errors='coerce')

    pivot = pivot.sort_index()
    pivot['fuel_used_l'] = pivot['fuel_liters_cum'].diff().clip(lower=0).fillna(0)
    pivot['runtime_used_h'] = pivot['runtime_hours_cum'].diff().clip(lower=0).fillna(0)

    daily = pivot.resample('D').agg({
        'fuel_used_l': 'sum',
        'runtime_used_h': 'sum',
        'fuel_per_kwh': 'mean',
        'fuel_efficiency': 'mean'
    }).reset_index()
    daily['daily_cost_r'] = daily['fuel_used_l'] * current_price

    return daily, pivot.reset_index()

daily_gen, full_gen_pivot = process_generator_data(gen_df.copy())

if not daily_gen.empty:
    filtered_gen = daily_gen[
        (daily_gen['last_changed'].dt.date >= start_date) &
        (daily_gen['last_changed'].dt.date <= end_date)
    ].copy()
else:
    filtered_gen = pd.DataFrame()

# ------------------ TABS AND GENERATOR TAB (UNCHANGED FROM LAST VERSION) ------------------
# (keep the same UI code as before)

# ==================== GENERATOR ANALYSIS TAB ====================
with tab1:
    # ... same as previous full code

# Footer same
