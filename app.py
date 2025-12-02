# app.py — Southern Paarl Energy Dashboard (Apple Sequoia Design)
# Full production version • December 2025

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ APPLE SEQUOIA UI ------------------
st.set_page_config(page_title="Durr Bottling Energy", layout="wide", initial_sidebar_state="expanded")
SEQUOIA_CSS = """
<style>
:root{
  --bg:#F6F7F8;
  --card:#FFFFFF;
  --muted:#6B7280;
  --accent-1: linear-gradient(135deg, rgba(14,63,45,0.06), rgba(183,145,96,0.03));
  --accent-2: linear-gradient(180deg, #F8FBF9 0%, #FFFFFF 100%);
  --glass: rgba(255,255,255,0.6);
  --radius: 18px;
}
[data-testid="stAppViewContainer"] > .main {
  background: radial-gradient(1200px 600px at 10% 10%, rgba(34,77,55,0.04), transparent 10%),
              radial-gradient(1000px 400px at 90% 90%, rgba(189,120,70,0.03), transparent 12%),
              var(--bg);
}
.sequoia-header{
  display:flex;align-items:center;gap:18px;padding:28px 24px;border-radius:20px;
  background: var(--accent-1);
  box-shadow: 0 6px 18px rgba(12,33,20,0.06);
  margin-bottom:24px;
}
.sequoia-title{font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif; font-weight:700; font-size:32px; background: linear-gradient(90deg, #007aff, #00c853); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
.sequoia-subtitle{color:#6B7280; font-size:15px; margin-top:6px}
.sequoia-card{
  background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.76));
  border-radius: var(--radius);
  padding:20px; border:1px solid rgba(12,33,20,0.04);
  box-shadow: 0 6px 20px rgba(12,33,20,0.04);
  margin-bottom:16px;
}
.metric-wrap{display:flex;gap:16px;align-items:center}
.metric-label{color:var(--muted);font-size:14px;font-weight:500}
.metric-value{font-weight:700;font-size:28px;color:#1d1d1f}
[data-testid="stSidebar"] {background: white; border-right: 1px solid #e0e0e0;}
.sidebar-profile{display:flex;align-items:center;gap:14px;margin-bottom:16px}
.profile-pill{background:linear-gradient(90deg,#0d3b66,#2a6f97);width:52px;height:52px;border-radius:14px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:18px}
.sequoia-btn{background:linear-gradient(90deg,#007aff,#0066cc);color:white;padding:12px 20px;border-radius:12px;border:none;font-weight:600}
.stButton>button:hover{background:#0051a8 !important}
</style>
"""
st.markdown(SEQUOIA_CSS, unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown(f"""
<div class='sequoia-header'>
  <div>
    <div class='sequoia-title'>Southern Paarl Energy</div>
    <div class='sequoia-subtitle'>Solar • Generator • Factory • Billing Dashboard</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ------------------ SIDEBAR — EXACTLY AS YOU WANTED ------------------
with st.sidebar:
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-profile'><div class='profile-pill'>HA</div><div><div style='font-weight:700'>Hussein Akim</div><div style='font-size:13px;color:#6B7280'>Electrical Engineer</div></div></div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:16px 0;border-color:rgba(0,0,0,0.08)'/>", unsafe_allow_html=True)
    
    st.markdown("### Configuration")
    st.markdown("**GTI Factor**")
    gti_factor = st.slider("", 0.50, 1.50, 1.00, 0.01, key="gti")
    
    st.markdown("**Performance Ratio**")
    pr_ratio = st.slider("", 0.50, 1.00, 0.80, 0.01, key="pr")
    
    st.markdown("**Cost per kWh (ZAR)**")
    cost_per_unit = st.number_input("", min_value=0.0, value=2.98, step=0.01, format="%.2f", key="cost")
    
    st.markdown("**Date Range**")
    col_from, col_to = st.columns(2)
    with col_from:
        st.markdown("**From**")
        start_date = st.date_input("", datetime.today() - timedelta(days=30), key="from")
    with col_to:
        st.markdown("**To**")
        end_date = st.date_input("", datetime.today(), key="to")
    
    st.markdown("---")
    st.markdown("### Navigation")
    page = st.radio("Navigate", [
        "Solar Performance", "Generator", "Factory", "Kehua", "Billing"
    ], label_visibility="collapsed")
    
    st.markdown("<div class='sequoia-note'>Theme: Apple Sequoia • v2.0</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ DATA SOURCES & LOADING ------------------
TOTAL_CAPACITY_KW = 221.43
TZ = 'Africa/Johannesburg'

SOLAR_URLS = ["https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
              "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
              "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
              "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
              "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"]
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"

progress = st.progress(0)
st.caption("Loading data from GitHub...")

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

solar_df = load_csvs(SOLAR_URLS); progress.progress(25)
weather_df = load_weather(gti_factor, pr_ratio); progress.progress(50)
gen_df = load_csvs([GEN_URL]); progress.progress(65)
factory_df = load_csvs([FACTORY_URL]); progress.progress(80)
kehua_df = load_csvs([KEHUA_URL]); progress.progress(100)

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

filtered = merged[(merged['last_changed'] >= pd.to_datetime(start_date)) & 
                  (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))]

def chart(df, x, y, title, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color), fill='tozeroy' if 'daily' in y else None))
    fig.update_layout(title=title, xaxis_rangeslider_visible=True, hovermode='x unified',
                      template="simple_white", margin=dict(l=20,r=20,t=60,b=20), height=500)
    return fig

# ------------------ PAGE CONTENT ------------------
if page == "Solar Performance":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.subheader("Actual vs Expected Power")
    fig = chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "#00C853")
    if 'expected_power_kw' in filtered.columns:
        fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'],
                                 name="Expected", line=dict(color="#007AFF", dash="dot")))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.subheader("Generator Performance")
    if 'sensor.generator_fuel_consumed' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel Consumed (L)", "#DC2626"), use_container_width=True)
    if 'sensor.generator_runtime_duration' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (hours)", "#7C3AED"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.subheader("Daily Factory Consumption")
    if 'daily_factory_kwh' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'daily_factory_kwh', "Daily kWh", "#0EA5E9"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.subheader("Kehua Internal Power")
    if 'sensor.kehua_internal_power' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Power (kW)", "#06B6D4"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.subheader("Billing Editor – September 2025")
    
    resp = requests.get(BILLING_URL)
    wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
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

    st.markdown("### Boerdery Subunits")
    c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
    c11 = st.number_input("Pomp, Willie, Gaste, Comp (C11)", value=float(ws['C11'].value or 0))
    c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

    if st.button("Apply Changes & Preview", type="primary"):
        ws['A1'].value = from_date.strftime("%b'%y")
        ws['B2'].value = from_date.strftime("%d/%m/%y")
        ws['B3'].value = to_date.strftime("%d/%m/%y")
        ws['B4'].value = days
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
st.markdown("<p style='text-align:center; color:#888; font-size:0.9rem;'>Built  by Hussein  • Durr Bottling • December 2025</p>", unsafe_allow_html=True)
