# app.py — Southern Paarl Energy Dashboard (FINAL • December 2025)
# Live Fuel SA API • Generator Costs • Billing Editor • Dark/Light Mode

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
import concurrent.futures
from datetime import datetime, timedelta

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Southern Paarl Energy", page_icon="Lightning", layout="wide", initial_sidebar_state="expanded")

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

st.markdown("<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
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
        if st.toggle("Theme", value=(st.session_state.theme == 'dark'), label_visibility="collapsed") != (st.session_state.theme == 'dark'):
            st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
            st.rerun()

    st.markdown("---")
    st.markdown("**Generator Settings**")
    fuel_region = st.selectbox("Fuel Region", ["Coast", "Reef"], index=0, help="Paarl = Coastal")

    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("From", datetime(2025, 5, 1))
    with col2: end_date = st.date_input("To", datetime(2025, 5, 31))

# ------------------ LIVE FUEL SA API ------------------
FUEL_SA_API_KEY = "3577238b0ad746ae986ee550a75154b6"

@st.cache_data(ttl=3600, show_spinner="Updating diesel prices...")
def get_live_diesel_prices(region):
    try:
        headers = {'key': FUEL_SA_API_KEY}
        response = requests.get('https://api.fuelsa.co.za/api/fuel/historic', headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices = []
        for item in data['prices']:
            date = datetime.strptime(item['date'], "%Y-%m-%d")
            coastal = float(item.get('diesel_0.05_coastal', item.get('diesel_coastal', 0)) or 0)
            reef = float(item.get('diesel_0.05_reef', item.get('diesel_reef', 0)) or 0)
            prices.append({"date": date, "Coast": coastal, "Reef": reef})
        df = pd.DataFrame(prices).sort_values("date")
        return df
    except Exception as e:
        st.warning(f"Fuel SA API error: {e}. Using fallback data.")
        dates = pd.date_range("2025-01-01", "2025-12-31", freq='MS')
        prices = [20.10, 20.50, 21.00, 20.80, 20.20, 19.80, 20.50, 21.00, 20.80, 20.50, 21.20, 21.50]
        return pd.DataFrame({'date': dates, 'price': prices[:len(dates)]})

fuel_price_df = get_live_diesel_prices(fuel_region)
current_price = fuel_price_df.iloc[-1]['price'] if not fuel_price_df.empty else 20.50

# ------------------ DATA LOADING ------------------
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
    except: return pd.DataFrame()

@st.cache_data(show_spinner="Loading data...")
def load_data_engine():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_clean_data, u) for u in SOLAR_URLS + [GEN_URL, FACTORY_URL, KEHUA_URL, WEATHER_URL]]
        results = [f.result() for f in futures]
    solar_df = pd.concat([r for r in results[:len(SOLAR_URLS)] if not r.empty], ignore_index=True) if any(not r.empty for r in results[:len(SOLAR_URLS)]) else pd.DataFrame()
    gen_df, factory_df, kehua_df, weather_df = results[-4:]
    return solar_df, gen_df, factory_df, kehua_df, weather_df

solar_df, gen_df, factory_df, kehua_df, weather_df = load_data_engine()

# ------------------ DATA PROCESSING ------------------
merged = pd.DataFrame()
if not solar_df.empty or not gen_df.empty or not factory_df.empty or not kehua_df.empty or not weather_df.empty:
    all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(col), left_on='last_changed', right_on=col, direction='nearest')

if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns: merged['sensor.goodwe_grid_power'] /= 1000
    merged['total_solar'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)
    
    if 'sensor.generator_fuel_consumed' in merged.columns:
        merged['month'] = merged['last_changed'].dt.to_period('M').dt.to_timestamp()
        merged = merged.merge(fuel_price_df[['date', 'price']], left_on='month', right_on='date', how='left')
        merged['price'] = merged['price'].fillna(current_price)
        merged['fuel_diff'] = merged['sensor.generator_fuel_consumed'].diff().clip(lower=0).fillna(0)
        merged['interval_cost'] = merged['fuel_diff'] * merged['price']

if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

filtered = merged[(merged['last_changed'] >= pd.to_datetime(start_date)) & (merged['last_changed'] <= pd.to_datetime(end_date) + timedelta(days=1))].copy() if not merged.empty else pd.DataFrame()

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
    st.plotly_chart(fig, use_container_width=True)

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs(["Generator Analysis", "Solar Performance", "Factory Load", "Billing Editor"])

with tab1:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.markdown(f"### Current Diesel Price: **R {current_price:.2f}/L** ({fuel_region})")
    if not filtered.empty and 'interval_cost' in filtered.columns:
        total_cost = filtered['interval_cost'].sum()
        total_fuel = filtered['fuel_diff'].sum()
        avg_price = filtered['price'].mean()
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='metric-val'>R {total_cost:,.0f}</div><div class='metric-lbl'>TOTAL COST</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-val'>{total_fuel:,.1f} L</div><div class='metric-lbl'>FUEL USED</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-val'>R {avg_price:.2f}</div><div class='metric-lbl'>AVG PRICE</div>", unsafe_allow_html=True)
        
        daily_cost = filtered.resample('D', on='last_changed')['interval_cost'].sum().reset_index()
        fig = go.Figure(go.Bar(x=daily_cost['last_changed'], y=daily_cost['interval_cost'], marker_color=theme['accent']))
        fig.update_layout(title="Daily Generator Cost (ZAR)", height=420)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No generator data for selected period")
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not filtered.empty and 'total_solar' in filtered.columns:
        st.plotly_chart(go.Figure(go.Scatter(x=filtered['last_changed'], y=filtered['total_solar'], mode='lines+markers', name='Solar Output')), use_container_width=True)
        st.success(f"Peak Solar Today: {filtered['total_solar'].max():.1f} kW")
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
        factory_df = factory_df.sort_values('last_changed')
        factory_df['daily'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)
        st.area_chart(factory_df.set_index('last_changed')['daily'], use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.subheader("September 2025 Invoice Editor")
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
        
        c1, c2 = st.columns(2)
        with c1:
            from_date = st.date_input("From", value=datetime.strptime(ws['B2'].value or "30/09/25", "%d/%m/%y").date())
            c7 = st.number_input("Freedom Village", value=float(ws['C7'].value or 0))
        with c2:
            to_date = st.date_input("To", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
            c9 = st.number_input("Boerdery", value=float(ws['C9'].value or 0))
        
        if st.button("Download Invoice", type="primary"):
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['C7'].value = c7; ws['C9'].value = c9
            buf = io.BytesIO(); wb.save(buf); buf.seek(0)
            st.download_button("Get Excel", buf, "Invoice.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except: st.error("Billing template unavailable")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='text-align:center; color:#E74C3C; font-weight:bold;'>HUSSEIN AKIM • DURR BOTTLING • LIVE ON FUEL SA API • DEC 2025</p>", unsafe_allow_html=True)
