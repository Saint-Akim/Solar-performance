# app.py — Southern Paarl Energy Dashboard (Fixed & Enhanced)
# Fixed: Labels, data filtering, UI consistency, responsiveness • December 2025

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Southern Paarl Energy", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ------------------ ENHANCED UI CSS ------------------
st.markdown("""
<style>
    .stApp {background: #f8f9fb;}
    [data-testid="stAppViewContainer"] > .main {background: #f8f9fb;}
    [data-testid="stSidebar"] {background: white; border-right: 1px solid #e5e5e7;}
    
    h1, h2, h3, p, div, span, label, .stMarkdown {color: #1d1d1f !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;}
    
    .energy-card {
        background: white !important;
        border-radius: 16px !important;
        padding: 24px !important;
        margin: 20px 0 !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
        border: 1px solid #e5e5e7 !important;
    }
    
    .header-title {
        font-size: 48px !important;
        font-weight: 700 !important;
        background: linear-gradient(90deg, #007AFF, #00C853) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-align: center !important;
        margin: 40px 0 10px 0 !important;
    }
    
    .stButton > button {
        background: #007AFF !important;
        color: white !important;
        border-radius: 12px !important;
        height: 48px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    
    .stButton > button:hover {background: #0066CC !important;}
    
    /* Responsive columns */
    @media (max-width: 768px) {
        .stColumns .stColumn {width: 100% !important;}
    }
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown("<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#555; font-size:18px; margin-bottom:40px;'>Solar • Generator • Factory • Billing Dashboard</p>", unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:30px 0;">
        <div style="width:80px; height:80px; background:linear-gradient(135deg,#007AFF,#00C853); border-radius:50%; margin:0 auto 20px; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:32px;">
            HA
        </div>
        <div style="font-weight:700; font-size:24px;">Hussein Akim</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Configuration")
    st.markdown("**GTI Factor**")
    gti_factor = st.slider("GTI Factor", 0.50, 1.50, 1.00, 0.01)
    
    st.markdown("**Performance Ratio**")
    pr_ratio = st.slider("Performance Ratio", 0.50, 1.00, 0.80, 0.01)
    
    st.markdown("**Cost per kWh (ZAR)**")
    cost_per_unit = st.number_input("Cost per kWh", min_value=0.0, value=2.98, step=0.01)
    
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**From**")
        start_date = st.date_input("From Date", datetime(2025, 5, 1))
    with col2:
        st.markdown("**To**")
        end_date = st.date_input("To Date", datetime(2025, 5, 31))
    
    st.markdown("---")
    st.markdown("### Navigation")
    page = st.radio("Navigate", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")

# ------------------ DATA LOADING ------------------
@st.cache_data
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
        except Exception as e:
            st.warning(f"Could not load {url}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

@st.cache_data
def load_weather(gti, pr):
    try:
        df = pd.read_csv(WEATHER_URL)
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        df['expected_power_kw'] = df['gti'] * gti * TOTAL_CAPACITY_KW * pr / 1000
        return df
    except Exception as e:
        st.warning(f"Could not load weather data: {e}")
        return pd.DataFrame()

solar_df = load_csvs(SOLAR_URLS)
weather_df = load_weather(gti_factor, pr_ratio)
gen_df = load_csvs([GEN_URL])
factory_df = load_csvs([FACTORY_URL])
kehua_df = load_csvs([KEHUA_URL])

if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
merged = pd.DataFrame()
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(col),
                               left_on='last_changed', right_on=col, direction='nearest')

if not merged.empty:
    for col in ['sensor.fronius_grid_power', 'sensor.goodwe_grid_power']:
        if col in merged.columns: merged[col] /= 1000
    merged['sum_grid_power'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

filtered = pd.DataFrame()
if not merged.empty:
    mask = (merged['last_changed'] >= pd.to_datetime(start_date)) & (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged.loc[mask].copy()

# ------------------ CHART FUNCTION ------------------
def plot(df, x, y, title, color):
    if df.empty or y not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False, font=dict(color="#666"))
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color, width=3)))
        if 'expected_power_kw' in df.columns and "Actual Power" in title:
            fig.add_trace(go.Scatter(x=df[x], y=df['expected_power_kw'], name="Expected", line=dict(color="#94a3b8", dash="dot")))
    fig.update_layout(
        title=title, template="plotly_white",
        height=500, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color="#1d1d1f"), xaxis=dict(gridcolor="#e5e5e5"), yaxis=dict(gridcolor="#e5e5e5")
    )
    return fig

# ------------------ PAGES ------------------
if page == "Solar":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Solar Output")
    st.plotly_chart(plot(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "#10b981"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Fuel Consumption")
        st.plotly_chart(plot(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel (L)", "#ef4444"), use_container_width=True)
    with col2:
        st.subheader("Runtime")
        st.plotly_chart(plot(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (h)", "#8b5cf6"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Daily Factory Consumption")
    st.plotly_chart(plot(filtered, 'last_changed', 'daily_factory_kwh', "Daily kWh", "#0ea5e9"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Kehua Internal Power")
    st.plotly_chart(plot(filtered, 'last_changed', 'sensor.kehua_internal_power', "Power (kW)", "#14b8a6"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Billing Editor – September 2025")
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
    except Exception as e:
        st.error(f"Could not load billing file: {e}")
        ws = None

    if ws:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Dates**")
            b2 = ws['B2'].value or "30/09/25"
            from_date = st.date_input("From Date", value=datetime.strptime(b2, "%d/%m/%y").date())
            b3 = ws['B3'].value or "05/11/25"
            to_date = st.date_input("To Date", value=datetime.strptime(b3, "%d/%m/%y").date())
        with col2:
            st.markdown("**Main Units**")
            c7 = st.number_input("Freedom Village (C7)", value=float(ws['C7'].value or 0))
            c9 = st.number_input("Boerdery (C9)", value=float(ws['C9'].value or 0))
            e9 = st.number_input("Boerdery Cost (E9)", value=float(ws['E9'].value or 0))
        with col3:
            st.markdown("**Account**")
            g21 = st.number_input("Drakenstein (G21)", value=float(ws['G21'].value or 0))

        st.markdown("### Boerdery Subunits")
        col_sub1, col_sub2, col_sub3 = st.columns(3)
        with col_sub1: c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
        with col_sub2: c11 = st.number_input("Pomp, Willie (C11)", value=float(ws['C11'].value or 0))
        with col_sub3: c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

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
                "Download Updated Excel",
                st.session_state.edited,
                file_name=f"September 2025 - {from_date.strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#555; font-size:16px; margin:40px 0;'>Built with love by Hussein Akim • Durr Bottling • December 2025</p>", unsafe_allow_html=True)
