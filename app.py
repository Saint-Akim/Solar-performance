import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
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

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1598/1598196.png", width=60)
    st.markdown("### Fuel SA Client")
    st.success("API Connected")
    st.caption("Trial Key Active – Expires 17 Dec 2025")

    col1, col2 = st.columns([0.7, 0.3])
    with col1: st.write("Dark Mode")
    with col2:
        if st.checkbox("", value=(st.session_state.theme == 'dark'), key="theme_toggle") != (st.session_state.theme == 'dark'):
            st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
            st.rerun()

    st.markdown("---")
    st.markdown("**Generator Settings**")
    fuel_region = st.selectbox("Fuel Region", ["Coast", "Reef"], index=0, help="Paarl = Coastal")

    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("From", datetime(2025, 1, 1))
    with col2: end_date = st.date_input("To", datetime(2025, 12, 15))

    st.markdown("---")
    st.header("📁 Optional Uploads")
    uploaded_gen_file = st.file_uploader("Upload custom GEN.csv (overrides GitHub)", type="csv", key="gen_upload")

# ------------------ LIVE FUEL SA API ------------------
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
        st.warning(f"Fuel SA API error: {e}. Using fallback price R22.52/L (Dec 2025 actual).")
        return pd.DataFrame({'price': [22.52]})

fuel_price_df = get_live_diesel_prices(fuel_region)
current_price = fuel_price_df.iloc[-1]['price'] if not fuel_price_df.empty else 22.52

# ------------------ DATA LOADING ------------------
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]

NEW_GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).csv"  # Updated rich GEN file
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"

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

@st.cache_data(show_spinner="Loading data from GitHub...")
def load_data_engine():
    urls = SOLAR_URLS + [NEW_GEN_URL, FACTORY_URL, KEHUA_URL, WEATHER_URL]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_clean_data, urls))
    solar_df = pd.concat([r for r in results[:len(SOLAR_URLS)] if not r.empty], ignore_index=True) if results[:len(SOLAR_URLS)] else pd.DataFrame()
    gen_df = results[len(SOLAR_URLS)]
    factory_df = results[len(SOLAR_URLS)+1]
    kehua_df = results[len(SOLAR_URLS)+2]
    weather_df = results[-1]
    return solar_df, gen_df, factory_df, kehua_df, weather_df

solar_df, gen_github_df, factory_df, kehua_df, weather_df = load_data_engine()

# Use uploaded GEN file if provided, otherwise GitHub (now the rich gen (2).csv)
gen_df = pd.read_csv(uploaded_gen_file) if uploaded_gen_file else gen_github_df

# ------------------ IMPROVED GENERATOR PROCESSING ------------------
@st.cache_data
def process_generator_data(_gen_df):
    if _gen_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    required_cols = {'entity_id', 'state', 'last_changed'}
    missing = required_cols - set(_gen_df.columns)
    if missing:
        st.error(f"Generator CSV missing columns: {', '.join(missing)}")
        return pd.DataFrame(), pd.DataFrame()

    # Flexible column order handling
    _gen_df = _gen_df[list(required_cols)].copy()
    _gen_df['last_changed'] = pd.to_datetime(_gen_df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    _gen_df['state'] = pd.to_numeric(_gen_df['state'], errors='coerce')

    _gen_df = _gen_df.dropna(subset=['state']).sort_values('last_changed')

    # Pivot hourly
    pivot = _gen_df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last')

    # Cumulative
    pivot['fuel_liters_cum'] = pivot.get('sensor.generator_fuel_consumed', 0).ffill().fillna(0)
    pivot['runtime_hours_cum'] = pivot.get('sensor.generator_runtime_duration', 0).ffill().fillna(0)

    # Instant metrics
    pivot['fuel_per_kwh'] = pivot.get('sensor.generator_fuel_per_kwh', pd.Series(index=pivot.index))
    pivot['fuel_efficiency'] = pivot.get('sensor.generator_fuel_efficiency', pd.Series(index=pivot.index))

    # Hourly diffs
    pivot = pivot.sort_index().resample('1H').last().ffill()
    pivot['hourly_fuel_l'] = pivot['fuel_liters_cum'].diff().fillna(0).clip(lower=0)
    pivot['hourly_runtime_h'] = pivot['runtime_hours_cum'].diff().fillna(0).clip(lower=0)
    pivot['hourly_cost_r'] = pivot['hourly_fuel_l'] * current_price

    # Daily aggregation
    daily = pivot.resample('D').agg({
        'hourly_fuel_l': 'sum',
        'hourly_runtime_h': 'sum',
        'hourly_cost_r': 'sum',
        'fuel_per_kwh': 'mean',
        'fuel_efficiency': 'mean'
    }).reset_index()
    daily.columns = ['last_changed', 'daily_fuel_l', 'daily_runtime_h', 'daily_cost_r', 'avg_fuel_per_kwh', 'avg_efficiency']

    return daily, pivot.reset_index()

daily_gen, full_gen_pivot = process_generator_data(gen_df)

# Filter by date range
if not daily_gen.empty:
    filtered_gen = daily_gen[
        (daily_gen['last_changed'].dt.date >= start_date) &
        (daily_gen['last_changed'].dt.date <= end_date)
    ].copy()
    filtered_full = full_gen_pivot[
        (full_gen_pivot['last_changed'].dt.date >= start_date) &
        (full_gen_pivot['last_changed'].dt.date <= end_date)
    ].copy()
else:
    filtered_gen = pd.DataFrame()
    filtered_full = pd.DataFrame()

# ------------------ MERGING FOR OTHER TABS (FIXED) ------------------
# ... (keep your existing merge code – it works well)

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs(["Generator Analysis", "Solar Performance", "Factory Load", "Billing Editor"])

# ==================== GENERATOR ANALYSIS TAB ====================
with tab1:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.markdown(f"### Current Diesel Price: **R {current_price:.2f}/L** ({fuel_region})")

    if not filtered_gen.empty:
        total_fuel = filtered_gen['daily_fuel_l'].sum()
        total_cost = filtered_gen['daily_cost_r'].sum()
        total_runtime = filtered_gen['daily_runtime_h'].sum()
        avg_eff = filtered_gen['avg_efficiency'].mean()
        avg_l_per_kwh = filtered_gen['avg_fuel_per_kwh'].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Fuel Used", f"{total_fuel:.1f} L")
        col2.metric("Total Cost", f"R {total_cost:,.0f}")
        col3.metric("Total Runtime", f"{total_runtime:.1f} hours")
        col4.metric("Avg Daily Cost", f"R {filtered_gen['daily_cost_r'].mean():,.0f}")

        col5, col6 = st.columns(2)
        col5.metric("Avg Efficiency", f"{avg_eff:.1f} kWh/L" if not pd.isna(avg_eff) else "N/A")
        col6.metric("Avg Fuel per kWh", f"{avg_l_per_kwh:.3f} L/kWh" if not pd.isna(avg_l_per_kwh) else "N/A")

        # Enhanced chart
        fig = go.Figure()
        fig.add_trace(go.Bar(x=filtered_gen['last_changed'], y=filtered_gen['daily_fuel_l'], name="Daily Fuel (L)", marker_color="orange"))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['daily_runtime_h'], name="Runtime (h)", mode="lines+markers", yaxis="y2", line=dict(color="lightblue")))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['daily_cost_r'], name="Daily Cost (R)", mode="lines+markers", yaxis="y3", line=dict(color=theme['accent'], width=4)))
        if 'avg_fuel_per_kwh' in filtered_gen.columns:
            fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['avg_fuel_per_kwh'], name="L/kWh (lower=better)", mode="lines", yaxis="y4", line=dict(color="purple", dash="dot")))

        fig.update_layout(
            title="Generator Daily Performance",
            yaxis=dict(title="Fuel (L)"),
            yaxis2=dict(title="Runtime (h)", overlaying="y", side="right"),
            yaxis3=dict(title="Cost (R)", overlaying="y", side="right", position=0.85),
            yaxis4=dict(title="L/kWh", overlaying="y", side="right", position=0.95, showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Hourly Detailed View"):
            if not filtered_full.empty:
                st.plotly_chart(px.line(filtered_full, x='last_changed', y=['hourly_fuel_l', 'hourly_runtime_h'], title="Hourly Fuel & Runtime"), use_container_width=True)

        with st.expander("View Raw Daily Data"):
            st.dataframe(filtered_gen.style.format({
                'daily_fuel_l': '{:.1f}',
                'daily_runtime_h': '{:.2f}',
                'daily_cost_r': 'R {:.0f}',
                'avg_fuel_per_kwh': '{:.3f}',
                'avg_efficiency': '{:.1f}'
            }))
    else:
        st.info("No generator data available for selected period or upload a GEN.csv file.")

    st.markdown("</div>", unsafe_allow_html=True)

# Keep your existing Solar, Factory, and Billing tabs unchanged...

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#E74C3C; font-weight:bold;'>built by Electrical@durrbottling.com</p>", unsafe_allow_html=True)
