# app.py — Unified Solar + Generator + Factory + Billing Dashboard
# Built by Hussein Akim — December 2025

import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import openpyxl
import io
import requests

# ------------------ CONFIGURATION ------------------
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
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
BILLING_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
]
DEFAULT_COST_PER_UNIT = 2.98

# ------------------ FRIENDLY NAMES ------------------
FRIENDLY_NAMES = {
    "sensor.fronius_grid_power": "Fronius Grid Power (kW)",
    "sensor.goodwe_grid_power": "GoodWe Grid Power (kW)",
    "sum_grid_power": "Total Solar Power (kW)",
    "expected_power_kw": "Expected Power (kW)",
    "sensor.generator_fuel_consumed": "Generator Fuel (L)",
    "sensor.generator_runtime_duration": "Generator Runtime (h)",
    "daily_factory_kwh": "Daily Factory kWh",
    "sensor.kehua_internal_power": "Kehua Internal Power (kW)"
}

# ------------------ STREAMLIT SETUP ------------------
st.set_page_config(page_title="Unified Energy Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("Unified Solar, Generator, Factory & Billing Dashboard")

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.image("https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/logo.png", width=200)  # optional logo
    st.header("Configuration")
    gti_factor = st.slider("GTI Factor", 0.5, 1.5, 1.0, 0.05)
    pr_ratio = st.slider("Performance Ratio", 0.5, 1.0, PERFORMANCE_RATIO, 0.05)
    cost_per_unit = st.number_input("Cost per kWh (ZAR)", 0.0, 10.0, DEFAULT_COST_PER_UNIT, 0.01)

    st.markdown("---")
    st.subheader("Date Range")
    today = datetime.today().date()
    start_date = st.date_input("From", today.replace(day=1))
    end_date = st.date_input("To", today)

    st.markdown("---")
    st.subheader("Navigation")
    page = st.radio("Go to", [
        "Solar Performance",
        "Generator",
        "Factory Consumption",
        "Kehua Internal",
        "Billing Editor"
    ], label_visibility="collapsed")

# ------------------ DATA LOADING (cached) ------------------
progress = st.progress(0)
st.info("Loading data from GitHub...")

@st.cache_data(show_spinner=False)
def load_solar():
    dfs = []
    for url in SOLAR_URLS:
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

@st.cache_data(show_spinner=False)
def load_generator(): return _load_csv(GEN_URL)
@st.cache_data(show_spinner=False)
def load_factory(): 
    df = _load_csv(FACTORY_URL)
    if not df.empty:
        df = df.sort_values('last_changed')
        df['daily_factory_kwh'] = df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)
    return df
@st.cache_data(show_spinner=False)
def load_kehua(): return _load_csv(KEHUA_URL)

def _load_csv(url):
    try:
        df = pd.read_csv(url)
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            return df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
    except: pass
    return pd.DataFrame()

# Load everything
solar_df = load_solar(); progress.progress(20)
weather_df = load_weather(gti_factor, pr_ratio); progress.progress(40)
gen_df = load_generator(); progress.progress(60)
factory_df = load_factory(); progress.progress(80)
kehua_df = load_kehua(); progress.progress(100)
st.success("All data loaded!")

# Merge
all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        time_col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(time_col),
                               left_on='last_changed', right_on=time_col, direction='nearest')
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

# ------------------ CHART HELPER ------------------
def make_chart(df, x, y, title, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name=FRIENDLY_NAMES.get(y, y), line=dict(color=color)))
    fig.update_layout(title=title, xaxis_rangeslider_visible=True, hovermode='x unified')
    return fig

# ------------------ PAGE ROUTING ------------------
if page == "Solar Performance":
    st.header("Solar Performance")
    fig = make_chart(filtered, 'last_changed', 'sum_grid_power', "Actual vs Expected Power", "green")
    if 'expected_power_kw' in filtered.columns:
        fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'],
                                 name="Expected Power (kW)", line=dict(color="orange", dash="dot")))
    st.plotly_chart(fig, use_container_width=True, width='stretch')

    st.subheader("Parameter Explorer")
    cols = st.columns(2)
    params = [c for c in filtered.columns if c not in ['last_changed', 'period_end', 'period'] and filtered[c].dtype != 'O']
    with cols[0]:
        sel = st.multiselect("Solar/Inverter", [p for p in params if any(k in p.lower() for k in ['fronius','goodwe','kehua','power'])],
                             default=[p for p in params if 'sum_grid_power' in p])
        for p in sel:
            st.plotly_chart(make_chart(filtered, 'last_changed', p, FRIENDLY_NAMES.get(p,p), '#00C853'), use_container_width=True, width='stretch')
    with cols[1]:
        sel = st.multiselect("Weather", [p for p in params if p not in ['sum_grid_power','expected_power_kw'] and 'generator' not in p and 'factory' not in p],
                             default=['gti','air_temp'])
        for p in sel:
            xcol = 'period_end' if p in weather_df.columns else 'last_changed'
            st.plotly_chart(make_chart(filtered, xcol, p, FRIENDLY_NAMES.get(p,p), '#1E88E5'), use_container_width=True, width='stretch')

elif page == "Generator":
    st.header("Generator Performance")
    if not gen_df.empty:
        st.plotly_chart(make_chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel Consumed", "red"), use_container_width=True, width='stretch')
        st.plotly_chart(make_chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime", "purple"), use_container_width=True, width='stretch')
    else:
        st.info("No generator data")

elif page == "Factory Consumption":
    st.header("Factory Daily Consumption")
    if 'daily_factory_kwh' in filtered.columns:
        st.plotly_chart(make_chart(filtered, 'last_changed', 'daily_factory_kwh', "Daily Factory kWh", "blue"), use_container_width=True, width='stretch')
    else:
        st.info("No factory data")

elif page == "Kehua Internal":
    st.header("Kehua Internal Power")
    if 'sensor.kehua_internal_power' in filtered.columns:
        st.plotly_chart(make_chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Kehua Power (kW)", "cyan"), use_container_width=True, width='stretch')
    else:
        st.info("No Kehua data")

elif page == "Billing Editor":
    st.header("Billing Editor – September 2025")

    if BILLING_URLS:
        url = BILLING_URLS[0]
        resp = requests.get(url)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active

        col1, col2 = st.columns(2)
        with col1:
            b2 = ws['B2'].value or "30/09/25"
            from_date = st.date_input("Date From (B2)", value=datetime.strptime(b2, "%d/%m/%y").date())
            b3 = ws['B3'].value or "05/11/25"
            to_date = st.date_input("Date To (B3)", value=datetime.strptime(b3, "%d/%m/%y").date())
            days = (to_date - from_date).days
            st.metric("Days (B4)", days)

        with col2:
            c7 = st.number_input("Freedom Village Units (C7)", value=float(ws['C7'].value or 0))
            c9 = st.number_input("Boerdery Total Units (C9)", value=float(ws['C9'].value or 0))
            e9 = st.number_input("Boerdery Cost (E9) – Override", value=float(ws['E9'].value or 0))
            g21 = st.number_input("Drakenstein Account (G21)", value=float(ws['G21'].value or 0))

        st.subheader("Boerdery Subunits")
        c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
        c11 = st.number_input("Pomp, Willie, Gaste, Comp (C11)", value=float(ws['C11'].value or 0))
        c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

        if st.button("Apply Changes & Preview"):
            ws['A1'].value = from_date.strftime("%b'%y")
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['B4'].value = days
            ws['C7'].value = c7
            ws['C9'].value = c9
            ws['C10'].value = c10
            ws['C11'].value = c11
            ws['C12'].value = c12
            ws['E7'] = '=C7*D7'          # ← Forces real formula
            ws['E9'].value = e9
            ws['G21'].value = g21

            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.session_state.edited_xlsx = buf.getvalue()

            preview = pd.read_excel(buf, header=None)
            st.dataframe(preview, use_container_width=True)

        if 'edited_xlsx' in st.session_state:
            st.download_button(
                "Download Edited September 2025.xlsx",
                st.session_state.edited_xlsx,
                file_name=f"September 2025 - Edited ({from_date.strftime('%Y-%m-%d')}).xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ------------------ FOOTER ------------------
st.markdown("---")
st.caption("Built by Hussein Akim • December 2025 • Southern Paarl Solar Farm")
