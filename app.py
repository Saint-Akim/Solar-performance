# app.py — Southern Paarl Energy Dashboard (Ultimate HA-Inspired Design)
# Final • December 2025 — Perfect UI, No Errors, Fully Visible

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Southern Paarl Energy", layout="wide", initial_sidebar_state="expanded")

# ------------------ HOME ASSISTANT + PREMIUM UI (LIGHT ONLY) ------------------
st.markdown("""
<style>
    /* Global light theme */
    .stApp {background: #f5f5f7 !important;}
    [data-testid="stAppViewContainer"] > .main {background: #f5f5f7 !important;}
    [data-testid="stSidebar"] {background: white !important; border-right: 1px solid #e0e0e0 !important;}
    
    /* Typography - HA style */
    h1, h2, h3, h4, p, div, span, label, .stMarkdown {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        color: #1d1d1f !important;
    }
    
    /* HA Card Style - from HA frontend */
    .ha-card {
        background: white !important;
        border-radius: 16px !important;
        padding: 24px !important;
        margin: 20px 0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        border: 1px solid #e8e8e8 !important;
    }
    
    /* Header - HA style */
    .ha-header {
        text-align: center;
        padding: 40px 0;
        margin-bottom: 20px;
    }
    .ha-title {
        font-size: 44px !important;
        font-weight: 700 !important;
        background: linear-gradient(90deg, #007AFF, #00C853) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        margin: 0 !important;
    }
    .ha-subtitle {
        color: #555 !important;
        font-size: 18px !important;
        margin: 12px 0 0 0 !important;
    }
    
    /* Sidebar - HA style */
    .sidebar-profile {
        text-align: center;
        padding: 24px 0;
    }
    .profile-avatar {
        width: 80px; height: 80px; border-radius: 50%;
        background: linear-gradient(135deg, #007AFF, #00C853);
        display: inline-flex; align-items: center; justify-content: center;
        color: white; font-weight: bold; font-size: 32px;
        margin-bottom: 16px;
        box-shadow: 0 6px 20px rgba(0,122,255,0.3);
    }
    
    /* Buttons - HA style */
    .stButton > button {
        background: #007AFF !important;
        color: white !important;
        border-radius: 14px !important;
        height: 52px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,122,255,0.3) !important;
    }
    .stButton > button:hover {
        background: #0066CC !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(0,102,204,0.4) !important;
    }
    
    /* Plotly fix */
    .js-plotly-plot .plotly {background: white !important;}
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown("""
<div class="ha-header">
    <div class="ha-title">Southern Paarl Energy</div>
    <div class="ha-subtitle">Solar • Generator • Factory • Billing Dashboard</div>
</div>
""", unsafe_allow_html=True)

# ------------------ SIDEBAR — FULLY VISIBLE ------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-profile">
        <div class="profile-avatar">HA</div>
        <div style="font-weight:700; font-size:22px; color:#1d1d1f;">Hussein Akim</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Configuration")
    st.markdown("**GTI Factor**")
    gti_factor = st.slider("", 0.50, 1.50, 1.00, 0.01, key="gti")
    
    st.markdown("**Performance Ratio**")
    pr_ratio = st.slider("", 0.50, 1.00, 0.80, 0.01, key="pr")
    
    st.markdown("**Cost per kWh (ZAR)**")
    cost_per_unit = st.number_input("", min_value=0.0, value=2.98, step=0.01, format="%.2f", key="cost")
    
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**From**")
        start_date = st.date_input("", datetime(2025, 5, 1), key="from")
    with col2:
        st.markdown("**To**")
        end_date = st.date_input("", datetime(2025, 5, 31), key="to")
    
    st.markdown("---")
    st.markdown("### Navigation")
    page = st.radio("Go to", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")

# ------------------ DATA LOADING ------------------
TOTAL_CAPACITY_KW = 221.43
TZ = 'Africa/Johannesburg'

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

@st.cache_data(show_spinner=False)
def load_csvs(urls):
    dfs = []
    for url in urls:
        try:
            df = pd.read_csv(url)
            if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
                df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
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
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        df['expected_power_kw'] = df['gti'] * gti * TOTAL_CAPACITY_KW * pr / 1000
        return df
    except: return pd.DataFrame()

solar_df = load_csvs(SOLAR_URLS)
weather_df = load_weather(gti_factor, pr_ratio)
gen_df = load_csvs([GEN_URL])
factory_df = load_csvs([FACTORY_URL])
kehua_df = load_csvs([KEHUA_URL])

if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

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
    if 'sensor.fronius_grid_power' in merged.columns: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns: merged['sensor.goodwe_grid_power'] /= 1000
    merged['sum_grid_power'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

filtered = merged[
    (merged['last_changed'] >= pd.to_datetime(start_date)) &
    (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
]

def plot(df, x, y, title, color):
    if df.empty or y not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data in selected range", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        return fig
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color, width=3)))
    fig.update_layout(title=title, xaxis_rangeslider_visible=True, hovermode='x unified',
                      template="simple_white", height=520)
    return fig

# ------------------ PAGES ------------------
if page == "Solar":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Solar Output")
    fig = plot(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "#00C853")
    if 'expected_power_kw' in filtered.columns:
        fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'],
                                 name="Expected", line=dict(color="#007AFF", width=3, dash="dot")))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Generator Performance")
    if 'sensor.generator_fuel_consumed' in filtered.columns:
        st.plotly_chart(plot(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel Consumed (L)", "#DC2626"), use_container_width=True)
    if 'sensor.generator_runtime_duration' in filtered.columns:
        st.plotly_chart(plot(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (hours)", "#7C3AED"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Daily Factory Consumption")
    if 'daily_factory_kwh' in filtered.columns:
        st.plotly_chart(plot(filtered, 'last_changed', 'daily_factory_kwh', "Daily kWh", "#0EA5E9"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Kehua Internal Power")
    if 'sensor.kehua_internal_power' in filtered.columns:
        st.plotly_chart(plot(filtered, 'last_changed', 'sensor.kehua_internal_power', "Power (kW)", "#06B6D4"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Billing Editor – September 2025")
    
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
    except:
        st.error("Could not load billing file")
        ws = None

    if ws:
        col1, col2 = st.columns(2)
        with col1:
            b2 = ws['B2'].value or "30/09/25"
            from_date = st.date_input("From", value=datetime.strptime(b2, "%d/%m/%y").date())
            to_date = st.date_input("To", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
        with col2:
            c7 = st.number_input("Freedom Village (C7)", value=float(ws['C7'].value or 0))
            c9 = st.number_input("Boerdery (C9)", value=float(ws['C9'].value or 0))
            e9 = st.number_input("Boerdery Cost (E9)", value=float(ws['E9'].value or 0))
            g21 = st.number_input("Drakenstein (G21)", value=float(ws['G21'].value or 0))

        st.markdown("### Boerdery Subunits")
        c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
        c11 = st.number_input("Pomp, Willie (C11)", value=float(ws['C11'].value or 0))
        c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

        if st.button("Apply Changes & Preview", type="primary"):
            ws['A1'].value = from_date.strftime("%b'%y")
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['B4'].value = (to_date - from_date).days
            ws['C7'].value = c7; ws['C9'].value = c9
            ws['C10'].value = c10; ws['C11'].value = c11; ws['C12'].value = c12
            ws['E7'] = '=C7*D7'
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
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#666; font-size:16px; margin:40px 0;'>Built with love by Hussein Akim • Durr Bottling • December 2025</p>", unsafe_allow_html=True)
