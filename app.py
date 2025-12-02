# app.py — Southern Paarl Energy Dashboard (Apple Design)
# Full working version • December 2025

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ APPLE-STYLE CONFIG ------------------
st.set_page_config(
    page_title="Southern Paarl Energy",
    page_icon="sunny",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={'About': "### Southern Paarl Solar Farm\nClean Energy Dashboard • December 2025"}
)

# ------------------ APPLE DESIGN CSS ------------------
st.markdown("""
<style>
    .main > div {padding-top: 2rem;}
    .css-1d391kg {padding-top: 1rem;}
    .stApp {background: linear-gradient(to bottom, #f9f9f9, #f0f0f0);}
    .css-1l02opa {background: white; border-right: 1px solid #e0e0e0;}
    
    h1, h2, h3 {font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;}
    h1 {font-size: 3rem; font-weight: 700; text-align: center;}
    h2 {font-size: 1.8rem; font-weight: 600; color: #1d1d1f;}
    
    .stMetric > div {background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);}
    .stDownloadButton > button, .stButton > button {
        background: #007aff !important; color: white !important; border-radius: 12px !important;
        font-weight: 600 !important; height: 48px !important; border: none !important;
    }
    .stDownloadButton > button:hover, .stButton > button:hover {background: #0066cc !important;}
    .stSlider > div > div > div {background: #007aff !important;}
</style>
""", unsafe_allow_html=True)

# ------------------ TITLE ------------------
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="margin:0; background: linear-gradient(90deg, #007aff, #00c853);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        Southern Paarl Energy
    </h1>
    <p style="color: #666; font-size: 1.2rem; margin-top: 8px;">
        Solar • Generator • Factory • Billing
    </p>
</div>
""", unsafe_allow_html=True)

# ------------------ SIDEBAR — APPLE STYLE ------------------
with st.sidebar:
    st.markdown("<h2 style='text-align:center; color:#1d1d1f;'>Configuration</h2>", unsafe_allow_html=True)
    
    st.markdown("**GTI Factor**")
    gti_factor = st.slider("", 0.50, 1.50, 1.00, 0.01, key="gti")
    
    st.markdown("**Performance Ratio**")
    pr_ratio = st.slider("", 0.50, 1.00, 0.80, 0.01, key="pr")
    
    st.markdown("**Cost per kWh (ZAR)**")
    cost_per_unit = st.number_input("", min_value=0.0, value=2.98, step=0.01, format="%.2f", key="cost")
    
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<small>From</small>", unsafe_allow_html=True)
        start_date = st.date_input("", datetime.today() - timedelta(days=30), key="from")
    with col2:
        st.markdown("<small>To</small>", unsafe_allow_html=True)
        end_date = st.date_input("", datetime.today(), key="to")
    
    st.markdown("---")
    st.markdown("<h3 style='text-align:center;'>Navigation</h3>", unsafe_allow_html=True)
    page = st.radio(
        "Navigate",
        ["Solar Performance", "Generator", "Factory", "Kehua", "Billing"],
        label_visibility="collapsed"
    )

# ------------------ DATA SOURCES ------------------
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

# ------------------ DATA LOADING ------------------
@st.cache_data(show_spinner=False)
def load_csvs(urls):
    dfs = []
    for url in urls:
        try:
            df = pd.read_csv(url)
            if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
                df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
                df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
                df['entity_id'] = df['entity_id'].str.lower().str.strip()
                piv = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
                dfs.append(piv)
        except: pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_weather(gti, pr):
    try:
        df = pd.read_csv(WEATHER_URL)
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
        df['expected_power_kw'] = df['gti'] * gti * 221.43 * pr / 1000
        return df
    except: return pd.DataFrame()

solar_df = load_csvs(SOLAR_URLS)
weather_df = load_weather(gti_factor, pr_ratio)
gen_df = load_csvs([GEN_URL])
factory_df = load_csvs([FACTORY_URL])
kehua_df = load_csvs([KEHUA_URL])

# Factory daily kWh
if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

# Merge
all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(col),
                               left_on='last_changed', right_on=col, direction='nearest')
else:
    merged = pd.DataFrame()

if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns:
        merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns:
        merged['sensor.goodwe_grid_power'] /= 1000
    merged['sum_grid_power'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

filtered = merged[(merged['last_changed'] >= pd.to_datetime(start_date)) & 
                  (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))]

# ------------------ CHART FUNCTION ------------------
def chart(df, x, y, title, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color)))
    fig.update_layout(title=title, xaxis_rangeslider_visible=True, hovermode='x unified',
                      template="simple_white", height=500)
    return fig

# ------------------ PAGES ------------------
if page == "Solar Performance":
    st.header("Solar Performance")
    fig = chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "#00C853")
    if 'expected_power_kw' in filtered.columns:
        fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'],
                                 name="Expected Power", line=dict(color="#007aff", dash="dot")))
    st.plotly_chart(fig, use_container_width=True)

elif page == "Generator":
    st.header("Generator")
    if 'sensor.generator_fuel_consumed' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel Consumed (L)", "red"), use_container_width=True)
    if 'sensor.generator_runtime_duration' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (hours)", "purple"), use_container_width=True)

elif page == "Factory":
    st.header("Factory Daily Consumption")
    if 'daily_factory_kwh' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'daily_factory_kwh', "Daily Factory kWh", "#1E88E5"), use_container_width=True)

elif page == "Kehua":
    st.header("Kehua Internal Power")
    if 'sensor.kehua_internal_power' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Kehua Power (kW)", "#00ACC1"), use_container_width=True)

elif page == "Billing":
    st.header("Billing Editor – September 2025")
    
    response = requests.get(BILLING_URL)
    wb = openpyxl.load_workbook(io.BytesIO(response.content), data_only=False)
    ws = wb.active

    col1, col2 = st.columns(2)
    with col1:
        b2 = ws['B2'].value or "30/09/25"
        from_date = st.date_input("Date From", value=datetime.strptime(b2, "%d/%m/%y").date())
        to_date = st.date_input("Date To", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
        days = (to_date - from_date).days

    with col2:
        c7 = st.number_input("Freedom Village Units (C7)", value=float(ws['C7'].value or 0))
        c9 = st.number_input("Boerdery Units (C9)", value=float(ws['C9'].value or 0))
        e9 = st.number_input("Boerdery Cost (E9)", value=float(ws['E9'].value or 0))
        g21 = st.number_input("Drakenstein Account (G21)", value=float(ws['G21'].value or 0))

    st.subheader("Boerdery Subunits")
    c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
    c11 = st.number_input("Pomp, Willie, Gaste, Comp (C11)", value=float(ws['C11'].value or 0))
    c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

    if st.button("Apply & Preview"):
        ws['A1'].value = from_date.strftime("%b'%y")
        ws['B2'].value = from_date.strftime("%d/%m/%y")
        ws['B3'].value = to_date.strftime("%d/%m/%y")
        ws['B4'].value = days
        ws['C7'].value = c7
        ws['C9'].value = c9
        ws['C10'].value = c10
        ws['C11'].value = c11
        ws['C12'].value = c12
        ws['E7'] = '=C7*D7'          # Real formula
        ws['E9'].value = e9
        ws['G21'].value = g21

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        st.session_state.edited = buf.getvalue()
        st.dataframe(pd.read_excel(buf, header=None), use_container_width=True)

    if 'edited' in st.session_state:
        st.download_button(
            "Download Edited September 2025.xlsx",
            st.session_state.edited,
            file_name=f"September 2025 - {from_date.strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#888; font-size:0.9rem;'>"
    "Built  by Hussein Akim - December 2025 Update"
    "</p>",
    unsafe_allow_html=True
)
