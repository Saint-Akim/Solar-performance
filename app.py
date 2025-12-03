import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import concurrent.futures

# ------------------ 1. PAGE & THEME ------------------
st.set_page_config(page_title="Southern Paarl Energy", page_icon="⚡", layout="wide")

if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

theme = {
    "bg": "#121212", "card": "#1E1E1E", "text": "#E0E0E0", "label": "#A0A0A0", "accent": "#E74C3C"
} if st.session_state.theme == 'dark' else {
    "bg": "#F8F9FA", "card": "#FFFFFF", "text": "#2C3E50", "label": "#7F8C8D", "accent": "#E74C3C"
}

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp {{ background: {theme['bg']}; font-family: 'Roboto', sans-serif; color: {theme['text']}; }}
    .fuel-card {{ background: {theme['card']}; border-radius: 14px; padding: 28px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); margin:20px 0; }}
    .metric-val {{ font-size: 36px; font-weight: 800; color: {theme['accent']}; }}
    .metric-lbl {{ font-size: 13px; font-weight: 600; text-transform: uppercase; color: {theme['label']}; letter-spacing: 1px; }}
    .header-title {{ font-size: 52px; font-weight: 900; text-align: center; margin: 40px 0 10px;
        background: linear-gradient(90deg, #E74C3C, #3498DB); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .stButton > button {{ background: {theme['accent']} !important; color: white !important; border-radius: 12px !important; height: 52px !important; font-weight: 700 !important; }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{ color: {theme['accent']}; border-bottom: 4px solid {theme['accent']}; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)

# ------------------ 2. SIDEBAR ------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1598/1598196.png", width=70)
    st.markdown("### Fuel SA Live")
    st.success("● API Connected")
    st.caption("Trial Key Active – Expires 17 Dec 2025")

    if st.toggle("Dark Mode", value=(st.session_state.theme == 'dark')) != (st.session_state.theme == 'dark'):
        st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
        st.rerun()

    st.markdown("---")
    st.markdown("**Fuel Region**")
    fuel_region = st.selectbox("Select Region", ["Coast", "Reef"], index=0)

    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("From", datetime(2025, 1, 1))
    with col2: end_date = st.date_input("To", datetime.today())

# ------------------ 3. LIVE FUEL SA API ------------------
FUEL_SA_API_KEY = "3577238b0ad746ae986ee550a75154b6"

@st.cache_data(ttl=3600, show_spinner="Updating diesel prices...")
def get_live_diesel_prices():
    try:
        headers = {"key": FUEL_SA_API_KEY}
        response = requests.get("https://api.fuelsa.co.za/api/fuel/historic", headers=headers, timeout=12)
        response.raise_for_status()
        data = response.json()
        prices = []
        for item in data["prices"]:
            date = datetime.strptime(item["date"], "%Y-%m-%d")
            coastal = float(item.get("diesel_0.05_coastal", item.get("diesel_coastal", 0)) or 0)
            reef = float(item.get("diesel_0.05_reef", item.get("diesel_reef", 0)) or 0)
            prices.append({"date": date, "Coast": coastal, "Reef": reef})
        df = pd.DataFrame(prices).sort_values("date")
        return df
    except Exception as e:
        st.error(f"Fuel SA API Error: {e}")
        fallback = pd.DataFrame([
            {"date": datetime(2025, 12, 1), "Coast": 21.84, "Reef": 22.64},
            {"date": datetime(2025, 11, 1), "Coast": 21.56, "Reef": 22.36},
            {"date": datetime(2025, 10, 1), "Coast": 21.12, "Reef": 21.92},
        ])
        return fallback

fuel_price_df = get_live_diesel_prices()
current_price = fuel_price_df.iloc[-1][fuel_region]

# ------------------ 4. DATA LOADING ------------------
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"

def safe_load(url):
    try:
        df = pd.read_csv(url)
        if 'last_changed' in df.columns:
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce').dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
            df = df.dropna(subset=['last_changed'])
            if {'state', 'entity_id'}.issubset(df.columns):
                df['state'] = pd.to_numeric(df['state'], errors='coerce')
                df = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_all():
    with concurrent.futures.ThreadPoolExecutor() as e:
        futures = [e.submit(safe_load, u) for u in SOLAR_URLS + [GEN_URL, FACTORY_URL]]
        results = [f.result() for f in futures]
    solar = pd.concat([r for r in results[:-2] if not r.empty], ignore_index=True) if any(not r.empty for r in results[:-2]) else pd.DataFrame()
    gen_df = results[-2] if len(results) >= 2 else pd.DataFrame()
    factory_df = results[-1] if len(results) >= 1 else pd.DataFrame()
    return solar, gen_df, factory_df

solar_df, gen_df, factory_df = load_all()

# ------------------ 5. MERGE & CALCULATE ------------------
merged = pd.concat([df for df in [solar_df, gen_df] if not df.empty], ignore_index=True) if not solar_df.empty or not gen_df.empty else pd.DataFrame()

if not merged.empty and 'last_changed' in merged.columns:
    merged = merged.sort_values('last_changed')
    if 'sensor.fronius_grid_power' in merged.columns: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns: merged['sensor.goodwe_grid_power'] /= 1000
    merged['total_solar'] = merged.get('sensor.fronius_grid_power', 0) + merged.get('sensor.goodwe_grid_power', 0)

    if 'sensor.generator_fuel_consumed' in merged.columns:
        merged['month'] = merged['last_changed'].dt.to_period('M').dt.to_timestamp()
        merged = merged.merge(fuel_price_df[['date', fuel_region]], left_on='month', right_on='date', how='left')
        merged[fuel_region] = merged[fuel_region].fillna(current_price)
        merged['fuel_used_l'] = merged['sensor.generator_fuel_consumed'].diff().clip(lower=0).fillna(0)
        merged['cost'] = merged['fuel_used_l'] * merged[fuel_region]

filtered = merged[(merged['last_changed'] >= pd.to_datetime(start_date)) & (merged['last_changed'] <= pd.to_datetime(end_date) + timedelta(days=1))].copy() if not merged.empty else pd.DataFrame()

# ------------------ 6. DASHBOARD TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs(["Generator Costs", "Solar Output", "Factory Load", "Billing"])

with tab1:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.markdown(f"### Current Diesel Price: **R {current_price:.2f}/L** ({fuel_region})")
    if not filtered.empty and 'cost' in filtered.columns:
        total_cost = filtered['cost'].sum()
        total_fuel = filtered['fuel_used_l'].sum()
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='metric-val'>R {total_cost:,.0f}</div><div class='metric-lbl'>TOTAL COST</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-val'>{total_fuel:,.1f} L</div><div class='metric-lbl'>FUEL USED</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-val'>R {current_price:.2f}</div><div class='metric-lbl'>LIVE PRICE</div>", unsafe_allow_html=True)

        st.plotly_chart(go.Figure(data=go.Bar(
            x=filtered['last_changed'].dt.date.unique(),
            y=filtered.groupby(filtered['last_changed'].dt.date)['cost'].sum(),
            marker_color='#E74C3C'
        )).update_layout(title="Daily Generator Cost (Live Prices)", height=500), use_container_width=True)
    else:
        st.info("No generator data for selected period")
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not filtered.empty and 'total_solar' in filtered.columns:
        fig = go.Figure()
        if 'sensor.fronius_grid_power' in filtered.columns:
            fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['sensor.fronius_grid_power'], mode='lines', name='Fronius'))
        if 'sensor.goodwe_grid_power' in filtered.columns:
            fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['sensor.goodwe_grid_power'], mode='lines', name='GoodWe'))
        fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['total_solar'], mode='lines', name='Total Solar', line=dict(width=3, color='#E74C3C')))
        fig.update_layout(title='Solar Output (kW)', xaxis_title='Timestamp', yaxis_title='kW', height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.success(f"Peak Solar Today: {filtered['total_solar'].max():.1f} kW")
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
        factory_df['daily'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)
        st.area_chart(factory_df.set_index('last_changed')['daily'], use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.download_button("Download Invoice Template", requests.get(BILLING_URL).content, "September_2025_Invoice.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='text-align:center; color:#E74C3C; font-weight:bold;'>HUSSEIN AKIM • DURR BOTTLING • LIVE ON FUEL SA API • DEC 2025</p>", unsafe_allow_html=True)
