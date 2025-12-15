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
    with col1: start_date = st.date_input("From", datetime(2025, 5, 1))
    with col2: end_date = st.date_input("To", datetime(2025, 5, 31))

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
        st.warning(f"Fuel SA API error: {e}. Using fallback price R20.50/L.")
        return pd.DataFrame({'price': [20.50]})

fuel_price_df = get_live_diesel_prices(fuel_region)
current_price = fuel_price_df.iloc[-1]['price'] if not fuel_price_df.empty else 20.50

# ------------------ DATA LOADING ------------------
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
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
    urls = SOLAR_URLS + [GEN_URL, FACTORY_URL, KEHUA_URL, WEATHER_URL]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_clean_data, urls))
    solar_df = pd.concat([r for r in results[:len(SOLAR_URLS)] if not r.empty], ignore_index=True) if results[:len(SOLAR_URLS)] else pd.DataFrame()
    gen_df = results[len(SOLAR_URLS)]
    factory_df = results[len(SOLAR_URLS)+1]
    kehua_df = results[len(SOLAR_URLS)+2]
    weather_df = results[-1]
    return solar_df, gen_df, factory_df, kehua_df, weather_df

solar_df, gen_github_df, factory_df, kehua_df, weather_df = load_data_engine()

# Use uploaded GEN file if provided, otherwise GitHub
gen_df = pd.read_csv(uploaded_gen_file) if uploaded_gen_file else gen_github_df

# ------------------ GENERATOR DETAILED ANALYSIS ------------------
@st.cache_data
def process_generator_data(_gen_df):
    if _gen_df.empty:
        return pd.DataFrame(), None
    
    required = ['last_changed', 'entity_id', 'state']
    if not all(col in _gen_df.columns for col in required):
        st.error("Generator CSV must have columns: last_changed, entity_id, state")
        return pd.DataFrame(), None
    
    _gen_df['last_changed'] = pd.to_datetime(_gen_df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    _gen_df['state'] = pd.to_numeric(_gen_df['state'], errors='coerce')
    _gen_df = _gen_df.dropna(subset=['last_changed', 'state']).sort_values('last_changed')
    
    pivot = _gen_df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last').reset_index()
    
    if 'sensor.generator_fuel_consumed' not in pivot.columns:
        st.error("Column 'sensor.generator_fuel_consumed' missing")
        return pd.DataFrame(), None
    
    pivot['fuel_liters_cum'] = pivot['sensor.generator_fuel_consumed']
    pivot['daily_fuel_l'] = pivot['fuel_liters_cum'].diff().clip(lower=0).fillna(0)
    
    pivot['runtime_hours_cum'] = pivot.get('sensor.generator_runtime_duration', 0)
    pivot['daily_runtime_h'] = pivot['runtime_hours_cum'].diff().clip(lower=0).fillna(0)
    
    daily = pivot.set_index('last_changed').resample('D').agg({
        'daily_fuel_l': 'sum',
        'daily_runtime_h': 'sum'
    }).reset_index()
    
    daily['daily_cost_r'] = daily['daily_fuel_l'] * current_price
    
    return daily, pivot

daily_gen, full_gen_pivot = process_generator_data(gen_df)

# Filter by date range
if not daily_gen.empty:
    filtered_gen = daily_gen[
        (daily_gen['last_changed'].dt.date >= start_date) &
        (daily_gen['last_changed'].dt.date <= end_date)
    ].copy()
else:
    filtered_gen = pd.DataFrame()

# ------------------ MERGING FOR OTHER TABS ------------------
def get_time_column(df):
    for col in df.columns:
        if any(k in col.lower() for k in ['timestamp', 'last_changed', 'period_end']):
            return col
    return None

all_dfs = [df for df in [solar_df, gen_github_df if uploaded_gen_file is None else pd.DataFrame(), factory_df, kehua_df, weather_df] if not df.empty and get_time_column(df)]
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
                    st.warning(f"Merge error: {e}")

if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns:
        merged['fronius_kw'] = merged['sensor.fronius_grid_power'] / 1000
    if 'sensor.goodwe_grid_power' in merged.columns:
        merged['goodwe_kw'] = merged['sensor.goodwe_grid_power'] / 1000
    merged['total_solar'] = merged.get('fronius_kw', 0).fillna(0) + merged.get('goodwe_kw', 0).fillna(0)

filtered_merged = merged[(merged['ts'] >= pd.to_datetime(start_date)) & (merged['ts'] <= pd.to_datetime(end_date) + timedelta(days=1))] if not merged.empty else pd.DataFrame()

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

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Fuel Used", f"{total_fuel:.1f} L")
        col2.metric("Total Cost", f"R {total_cost:,.0f}")
        col3.metric("Total Runtime", f"{total_runtime:.1f} hours")
        col4.metric("Avg Daily Cost", f"R {filtered_gen['daily_cost_r'].mean():,.0f}")

        # Peak days
        peak_fuel = filtered_gen.loc[filtered_gen['daily_fuel_l'].idxmax()]
        peak_runtime = filtered_gen.loc[filtered_gen['daily_runtime_h'].idxmax()]
        
        col5, col6 = st.columns(2)
        col5.metric("Highest Fuel Day", peak_fuel['last_changed'].strftime("%b %d"), f"{peak_fuel['daily_fuel_l']:.1f} L")
        col6.metric("Longest Runtime Day", peak_runtime['last_changed'].strftime("%b %d"), f"{peak_runtime['daily_runtime_h']:.1f} h")

        # Combined chart
        fig = go.Figure()
        fig.add_trace(go.Bar(x=filtered_gen['last_changed'], y=filtered_gen['daily_fuel_l'], name="Daily Fuel (L)", marker_color="orange"))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['daily_runtime_h'], name="Runtime (hours)", mode="lines+markers", yaxis="y2", line=dict(color="lightblue")))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['daily_cost_r'], name="Daily Cost (R)", mode="lines+markers", yaxis="y3", line=dict(color=theme['accent'], width=4)))

        fig.update_layout(
            title="Generator Daily Fuel, Runtime & Cost",
            yaxis=dict(title="Fuel (L)"),
            yaxis2=dict(title="Runtime (h)", overlaying="y", side="right"),
            yaxis3=dict(title="Cost (R)", overlaying="y", side="right", position=0.95, showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("View Raw Daily Data"):
            st.dataframe(filtered_gen.style.format({
                'daily_fuel_l': '{:.1f}',
                'daily_runtime_h': '{:.2f}',
                'daily_cost_r': 'R {:.0f}'
            }))
    else:
        st.info("No generator data available for selected period or upload a GEN.csv file.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== SOLAR PERFORMANCE TAB ====================
with tab2:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not filtered_merged.empty and 'total_solar' in filtered_merged.columns:
        fig = go.Figure(go.Scatter(
            x=filtered_merged['ts'], y=filtered_merged['total_solar'],
            mode='lines+markers', name='Total Solar Output',
            line=dict(color=theme['success'], width=3)
        ))
        fig.update_layout(title="Solar Power Output (kW)", height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.success(f"Peak Solar Output: {filtered_merged['total_solar'].max():.1f} kW")
    else:
        st.info("No solar data in selected period.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== FACTORY LOAD TAB ====================
with tab3:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
        factory_df = factory_df.sort_values('last_changed').copy()
        factory_df['daily_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().clip(lower=0).fillna(0)
        fig = go.Figure(go.Scatter(
            x=factory_df['last_changed'], y=factory_df['daily_kwh'],
            mode='lines+markers', name='Daily Factory Consumption',
            line=dict(color="#3498DB", width=3)
        ))
        fig.update_layout(title="Daily Factory Energy Consumption (kWh)", height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No factory consumption data available.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== BILLING EDITOR TAB ====================
with tab4:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.subheader("September 2025 Invoice Editor")
    try:
        resp = requests.get(BILLING_URL)
        resp.raise_for_status()
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active

        col1, col2 = st.columns(2)
        with col1:
            from_val = ws['B2'].value or "30/09/25"
            from_date = datetime.strptime(str(from_val).strip(), "%d/%m/%y").date() if isinstance(from_val, (str, datetime)) else datetime.now().date()
            from_date = st.date_input("Period From (B2)", value=from_date)
            freedom_units = float(ws['C7'].value or 0)
            freedom_units = st.number_input("Freedom Village Units (C7)", value=freedom_units)
        with col2:
            to_val = ws['B3'].value or "31/10/25"
            to_date = datetime.strptime(str(to_val).strip(), "%d/%m/%y").date() if isinstance(to_val, (str, datetime)) else datetime.now().date()
            to_date = st.date_input("Period To (B3)", value=to_date)
            boerdery_units = float(ws['C9'].value or 0)
            boerdery_units = st.number_input("Boerdery Units (C9)", value=boerdery_units)

        if st.button("Generate Updated Invoice", type="primary"):
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['C7'].value = freedom_units
            ws['C9'].value = boerdery_units

            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            st.download_button(
                label="Download Updated Invoice",
                data=buffer,
                file_name=f"Invoice_{from_date.strftime('%b%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Failed to load billing template: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#E74C3C; font-weight:bold;'>built by Electrical@durrbottling.com</p>", unsafe_allow_html=True)
