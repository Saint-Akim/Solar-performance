# app.py — FINAL VERSION (Streamlit + Netlify/Home Assistant Custom Card UI)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ NETLIFY / HOME ASSISTANT CUSTOM CARD UI ------------------
st.set_page_config(page_title="Southern Paarl Energy", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Netlify + Mushroom Cards + Home Assistant Custom Card Design */
    .stApp {background: #0f0f0f !important;}
    [data-testid="stAppViewContainer"] > .main {background: transparent !important;}
    [data-testid="stSidebar"] {background: rgba(15,15,15,0.95) !important; backdrop-filter: blur(20px);}
    
    /* Cards - Mushroom Card style */
    .energy-card {
        background: rgba(30,30,30,0.85) !important;
        border-radius: 24px !important;
        padding: 28px !important;
        margin: 20px 0 !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(20px);
        transition: all 0.3s ease !important;
    }
    .energy-card:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 12px 40px rgba(0,0,0,0.7) !important;
    }
    
    /* Header */
    .header-title {
        font-size: 52px !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #00D4FF, #00FF88) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-align: center !important;
        margin: 40px 0 10px 0 !important;
        text-shadow: 0 4px 20px rgba(0,212,255,0.3) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #00D4FF, #00FF88) !important;
        color: black !important;
        border-radius: 16px !important;
        height: 56px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        border: none !important;
        box-shadow: 0 4px 20px rgba(0,212,255,0.4) !important;
        transition: all 0.3s !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 30px rgba(0,255,136,0.5) !important;
    }
    
    /* Text */
    h1, h2, h3, p, div, span, label {color: white !important;}
    .stMarkdown {color: #e0e0e0 !important;}
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown("<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#aaa; font-size:20px; margin-bottom:40px;'>Solar • Generator • Factory • Billing Dashboard</p>", unsafe_allow_html=True)

# ------------------ SIDEBAR (MATCHING NETLIFY UI) ------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:30px 0;">
        <div style="width:80px; height:80px; background:linear-gradient(135deg,#00D4FF,#00FF88); border-radius:50%; margin:0 auto 20px; display:flex; align-items:center; justify-content:center; color:black; font-weight:bold; font-size:32px; box-shadow:0 8px 30px rgba(0,212,255,0.4);">
            HA
        </div>
        <div style="font-weight:700; font-size:24px; color:white;">Hussein Akim</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Configuration")
    st.markdown("**GTI Factor**"); gti_factor = st.slider("", 0.50, 1.50, 1.00, 0.01)
    st.markdown("**Performance Ratio**"); pr_ratio = st.slider("", 0.50, 1.00, 0.80, 0.01)
    st.markdown("**Cost per kWh (ZAR)**"); cost_per_unit = st.number_input("", 0.0, 10.0, 2.98, 0.01)
    
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1: st.markdown("**From**"); start_date = st.date_input("", datetime(2025, 5, 1))
    with col2: st.markdown("**To**"); end_date = st.date_input("", datetime(2025, 5, 31))
    
    st.markdown("---")
    page = st.radio("Navigate", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")
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
if page == "Solar":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Solar Output")
    # your chart code
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ... repeat for all pages ...

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#888; font-size:16px; margin:40px 0;'>Built with love by Hussein Akim • Durr Bottling • December 2025</p>", unsafe_allow_html=True)
