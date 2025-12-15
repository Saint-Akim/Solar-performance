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

# ------------------ SIDEBAR (REFINED & PROFESSIONAL) ------------------
with st.sidebar:
    st.markdown("## ⚡ Durr Bottling")
    st.caption("Electrical & Energy Intelligence")

    st.success("Fuel SA API Connected")
    st.caption("Trial Key • Expires 17 Dec 2025")

    st.markdown("---")

    # GLOBAL CONTROLS
    st.subheader("Appearance")
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.caption("Dark Mode")
    with col2:
        dark_mode = st.toggle("", value=(st.session_state.theme == 'dark'), key="theme_toggle")
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

# ------------------ LIVE FUEL SA API (CURRENT ONLY - SAFER) ------------------
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
            location = item['location']
            value = float(item['value'])
            prices.append({"location": location.lower(), "price": value})
        df = pd.DataFrame(prices)
        match = df[df['location'] == region.lower()]
        if match.empty:
            raise ValueError(f"Region '{region}' not found in Fuel SA response")
        return match['price'].iloc[0]
    except Exception as e:
        st.warning(f"Fuel SA API error: {e}. Using fallback R22.52/L (Dec 2025).")
        return 22.52

current_price = get_current_diesel_price(fuel_region)

# ------------------ DATA LOADING ------------------
NEW_GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).csv"
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
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

gen_df = pd.read_csv(uploaded_gen_file) if uploaded_gen_file else gen_github_df

# ------------------ ROBUST GENERATOR PROCESSING (WITH CACHE FIX) ------------------
@st.cache_data(show_spinner=False)
def process_generator_data(_gen_df: pd.DataFrame):
    if _gen_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    required_cols = {'entity_id', 'state', 'last_changed'}
    missing = required_cols - set(_gen_df.columns)
    if missing:
        st.error(f"Generator CSV missing columns: {', '.join(missing)}")
        return pd.DataFrame(), pd.DataFrame()

    _gen_df = _gen_df[list(required_cols)].copy()
    _gen_df['last_changed'] = pd.to_datetime(_gen_df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    _gen_df['state'] = pd.to_numeric(_gen_df['state'], errors='coerce')

    _gen_df = _gen_df.dropna(subset=['state']).sort_values('last_changed')

    pivot = _gen_df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last')

    def clean_cumulative(series):
        series = series.ffill()
        diff = series.diff()
        series = series.where(diff >= 0, series.shift(1))
        return series.fillna(method='ffill').fillna(0)

    pivot['fuel_liters_cum'] = clean_cumulative(pivot.get('sensor.generator_fuel_consumed'))
    pivot['runtime_hours_cum'] = clean_cumulative(pivot.get('sensor.generator_runtime_duration'))

    pivot['fuel_per_kwh'] = pivot.get('sensor.generator_fuel_per_kwh')
    pivot['fuel_efficiency'] = pivot.get('sensor.generator_fuel_efficiency')

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

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs(["Generator Analysis", "Solar Performance", "Factory Load", "Billing Editor"])

# ==================== GENERATOR ANALYSIS TAB ====================
with tab1:
    st.markdown("## 🔌 Generator Performance Overview")
    st.caption("Fuel usage, runtime and estimated operating cost")

    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.markdown(f"### Current Diesel Price: **R {current_price:.2f}/L** ({fuel_region})")
    st.caption("⚠️ Cost calculated using today's diesel price (not historical pricing)")

    if not filtered_gen.empty:
        period_fuel = filtered_gen['fuel_used_l'].sum()
        period_runtime = filtered_gen['runtime_used_h'].sum()
        period_cost = filtered_gen['daily_cost_r'].sum()
        avg_eff = filtered_gen['fuel_efficiency'].mean()
        avg_l_per_kwh = filtered_gen['fuel_per_kwh'].mean()

        # KPI Cards – Executive-ready
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-lbl'>Total Cost</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-val'>R {period_cost:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-lbl'>Fuel Used</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-val'>{period_fuel:.1f} L</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-lbl'>Runtime</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-val'>{period_runtime:.1f} h</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col4:
            st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-lbl'>Efficiency</div>", unsafe_allow_html=True)
            eff_text = f"{avg_eff:.1f} kWh/L" if not pd.isna(avg_eff) else "N/A"
            st.markdown(f"<div class='metric-val'>{eff_text}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Trends Section
        st.markdown("### 📈 Daily Generator Trends")
        st.caption("Fuel consumption, runtime and estimated cost")

        fig = go.Figure()
        fig.add_trace(go.Bar(x=filtered_gen['last_changed'], y=filtered_gen['fuel_used_l'], name="Daily Fuel (L)", marker_color="orange"))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['runtime_used_h'], name="Runtime (h)", mode="lines+markers", yaxis="y2", line=dict(color="lightblue")))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['daily_cost_r'], name="Daily Cost (R)", mode="lines+markers", yaxis="y3", line=dict(color=theme['accent'], width=4)))

        fig.update_layout(
            title="Generator Daily Fuel Burn, Runtime & Estimated Cost",
            yaxis=dict(title="Fuel (L)"),
            yaxis2=dict(title="Runtime (h)", overlaying="y", side="right"),
            yaxis3=dict(title="Cost (R)", overlaying="y", side="right", position=0.85),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Data Section
        with st.expander("📄 View Daily Generator Data"):
            st.dataframe(filtered_gen.style.format({
                'fuel_used_l': '{:.1f}',
                'runtime_used_h': '{:.2f}',
                'daily_cost_r': 'R {:.0f}',
                'fuel_per_kwh': '{:.3f}',
                'fuel_efficiency': '{:.1f}'
            }))

    else:
        st.info("No generator data available for selected period or upload a GEN.csv file.")

    st.markdown("</div>", unsafe_allow_html=True)

# Keep your existing Solar, Factory, and Billing tabs unchanged...

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#E74C3C; font-weight:bold;'>built by Electrical@durrbottling.com</p>", unsafe_allow_html=True)
