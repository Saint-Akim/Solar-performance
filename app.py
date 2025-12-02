# app.py — Unified Solar + Generator + Factory + Billing Dashboard
# Built by Hussein Akim — December 2025 (Sequoia Light UI integrated)
# Requirements: streamlit, pandas, plotly, openpyxl, requests

import os
import io
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import openpyxl
import requests
from typing import List

# ------------------ CONFIGURATION ------------------
TOTAL_CAPACITY_KW = 221.43
GOODWE_KW = 110.0
FRONIUS_KW = 60.0
INVERTER_TOTAL_KW = GOODWE_KW + FRONIUS_KW
DEFAULT_PR = 0.80
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
    "expected_total_kw": "Expected (Total panels, kW)",
    "expected_inverter_kw": "Expected (Inverter capacity, kW)",
    "expected_goodwe_kw": "Expected GoodWe (kW)",
    "expected_fronius_kw": "Expected Fronius (kW)",
    "sensor.generator_fuel_consumed": "Generator Fuel (L)",
    "sensor.generator_runtime_duration": "Generator Runtime (h)",
    "daily_factory_kwh": "Daily Factory kWh",
    "sensor.kehua_internal_power": "Kehua Internal Power (kW)",
    "gti": "GTI"
}

# ------------------ SEQUOIA LIGHT CSS ------------------
SEQUOIA_CSS = """
<style>
html, body, [class*="css"]  { font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif; }
[data-testid="stAppViewContainer"] > .main { background: radial-gradient(800px 400px at 10% 10%, rgba(0,122,255,0.02), transparent), radial-gradient(700px 300px at 90% 90%, rgba(0,200,83,0.01), transparent), #f7f7f9; padding: 18px 20px 40px 20px; }
.sequoia-card { background: rgba(255,255,255,0.68); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); border-radius: 20px; padding: 18px; margin-bottom: 16px; box-shadow: 0 10px 28px rgba(9,30,66,0.06); border: 1px solid rgba(255,255,255,0.45); }
section[data-testid="stSidebar"] > div { background: rgba(255,255,255,0.60) !important; backdrop-filter: blur(18px) !important; -webkit-backdrop-filter: blur(18px) !important; border-right: 1px solid rgba(255,255,255,0.45) !important; padding-top: 18px !important; }
button[kind="primary"] { background: linear-gradient(180deg,#ffffff,#f0f0f3) !important; color:#222 !important; border-radius:12px !important; border:1px solid rgba(0,0,0,0.06) !important; box-shadow: 0 6px 18px rgba(9,30,66,0.06) !important; height:44px !important; font-weight:700 !important; }
.dataframe td, .dataframe th { background: transparent !important; }
.js-plotly-plot .plotly { background: white !important; border-radius: 12px !important; }
.metric-big { font-size: 24px; font-weight: 800; }
.metric-sub { color: #6b7280; font-size: 12px; }
.kpi-row { display:flex; gap:12px; }
.kpi { flex:1; }
</style>
"""
st.markdown(SEQUOIA_CSS, unsafe_allow_html=True)

# ------------------ STREAMLIT SETUP ------------------
st.set_page_config(page_title="Unified Energy Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("Unified Solar, Generator, Factory & Billing Dashboard")

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.image("https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/logo.png", width=160)
    st.header("Configuration")
    gti_factor = st.slider("GTI Factor", 0.5, 1.5, 1.0, 0.01)
    pr_ratio = st.slider("Performance Ratio (global)", 0.5, 1.0, DEFAULT_PR, 0.01)
    # per-inverter PR sliders
    pr_goodwe = st.slider("PR — GoodWe (110 kW)", 0.5, 1.0, 0.90, 0.01)
    pr_fronius = st.slider("PR — Fronius (60 kW)", 0.5, 1.0, 0.86, 0.01)
    cost_per_unit = st.number_input("Cost per kWh (ZAR)", 0.0, 20.0, DEFAULT_COST_PER_UNIT, 0.01)

    st.markdown("---")
    st.subheader("Date Range")
    today = datetime.today().date()
    start_date = st.date_input("From", today - timedelta(days=30))
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
    st.markdown("---")
    st.caption("Sequoia Light theme • Built by Hussein Akim")

# ------------------ DATA LOADING (cached) ------------------
progress = st.progress(0)
st.info("Loading data from GitHub (cached)...")

@st.cache_data(show_spinner=False)
def safe_read_csv(url: str) -> pd.DataFrame:
    try:
        return pd.read_csv(url)
    except Exception:
        return pd.DataFrame()

def normalize_ha_history(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = set(map(str.lower, df.columns))
    if {'last_changed', 'state', 'entity_id'}.issubset(cols):
        df = df.rename(columns={c: c.lower() for c in df.columns})
        df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
        df['entity_id'] = df['entity_id'].str.lower().str.strip()
        pivot = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        return pivot
    # attempt to find a datetime column and rename to last_changed
    for c in df.columns:
        if 'time' in c.lower() or 'date' in c.lower() or 'period' in c.lower():
            try:
                df[c] = pd.to_datetime(df[c], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
                df = df.rename(columns={c: 'last_changed'}).reset_index(drop=True)
                return df
            except Exception:
                pass
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_and_normalize(urls: List[str]) -> pd.DataFrame:
    parts = []
    for u in urls:
        df = safe_read_csv(u)
        pivot = normalize_ha_history(df)
        if not pivot.empty:
            parts.append(pivot)
    if parts:
        big = pd.concat(parts, ignore_index=True, sort=False)
        big = big.sort_values('last_changed').reset_index(drop=True)
        return big
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_weather_df(gti_factor_local: float, pr_local: float) -> pd.DataFrame:
    df = safe_read_csv(WEATHER_URL)
    if df.empty:
        return pd.DataFrame()
    # detect time & gti columns
    time_col = None
    for c in df.columns:
        if 'period_end' in c.lower() or 'time' in c.lower() or 'date' in c.lower():
            time_col = c
            break
    if time_col is None:
        time_col = df.columns[0]
    try:
        df[time_col] = pd.to_datetime(df[time_col], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
    except Exception:
        pass
    # gti detection
    gti_col = None
    for c in df.columns:
        if 'gti' in c.lower() or 'irradi' in c.lower() or 'ghi' in c.lower():
            gti_col = c
            break
    if gti_col is None and 'value' in df.columns:
        gti_col = 'value'
    if gti_col:
        df = df.rename(columns={time_col: 'period_end', gti_col: 'gti'})
    else:
        df = df.rename(columns={time_col: 'period_end'})
        df['gti'] = 0.9 + 0.05 * (pd.Series(range(len(df))) % 24) / 24.0

    df['gti'] = pd.to_numeric(df['gti'], errors='coerce').fillna(0)
    # expected calculations (kW)
    # NOTE: If your GTI is in W/m² and you want /1000 conversion, adjust here. We'll assume current feed is normalized.
    df['expected_total_kw'] = df['gti'] * gti_factor_local * TOTAL_CAPACITY_KW * pr_local
    df['expected_inverter_kw'] = df['gti'] * gti_factor_local * INVERTER_TOTAL_KW * pr_local
    df['expected_goodwe_kw'] = df['gti'] * gti_factor_local * GOODWE_KW * pr_goodwe
    df['expected_fronius_kw'] = df['gti'] * gti_factor_local * FRONIUS_KW * pr_fronius
    return df[['period_end', 'gti', 'expected_total_kw', 'expected_inverter_kw', 'expected_goodwe_kw', 'expected_fronius_kw']]

# Load datasets
progress.progress(5)
solar_df = load_and_normalize(SOLAR_URLS); progress.progress(25)
weather_df = load_weather_df(gti_factor, pr_ratio); progress.progress(45)
gen_df = load_and_normalize([GEN_URL]); progress.progress(60)
factory_df = load_and_normalize([FACTORY_URL]); progress.progress(75)
kehua_df = load_and_normalize([KEHUA_URL]); progress.progress(90)
progress.progress(100)
st.success("All data loaded (cached)")

# Factory daily calculation
if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

# Build merged dataset (nearest)
all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        time_col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(time_col),
                               left_on='last_changed', right_on=time_col, direction='nearest', tolerance=pd.Timedelta('2H'))
else:
    merged = pd.DataFrame()

# Normalize kW if sensors are in W
if not merged.empty:
    for col in ['sensor.fronius_grid_power', 'sensor.goodwe_grid_power', 'sensor.kehua_internal_power']:
        if col in merged.columns:
            try:
                merged[col] = pd.to_numeric(merged[col], errors='coerce') / 1000.0
            except Exception:
                pass
    merged['sum_grid_power'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

# Filter by date range
if not merged.empty and 'last_changed' in merged.columns:
    merged['last_changed'] = pd.to_datetime(merged['last_changed'])
    mask = (merged['last_changed'] >= pd.to_datetime(start_date)) & (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged[mask].copy()
else:
    filtered = pd.DataFrame()

# Merge nearest weather expected columns into filtered if present
if not filtered.empty and not weather_df.empty:
    if 'period_end' in weather_df.columns:
        left = filtered.sort_values('last_changed').reset_index(drop=True)
        right = weather_df.sort_values('period_end').reset_index(drop=True)
        left = pd.merge_asof(left, right, left_on='last_changed', right_on='period_end', direction='nearest', tolerance=pd.Timedelta('3H'))
        filtered = left

# ------------------ CALCULATIONS: expected & shortfalls ------------------
if not filtered.empty:
    # expected from weather (if present)
    if 'expected_total_kw' in filtered.columns:
        filtered['expected_total_kw'] = pd.to_numeric(filtered['expected_total_kw'], errors='coerce').fillna(0)
    else:
        filtered['expected_total_kw'] = 0
    if 'expected_inverter_kw' in filtered.columns:
        filtered['expected_inverter_kw'] = pd.to_numeric(filtered['expected_inverter_kw'], errors='coerce').fillna(0)
    else:
        filtered['expected_inverter_kw'] = 0
    # fallback expected using GTI * gti_factor * TOTAL_CAPACITY * pr_ratio if GTI present
    if 'gti' in filtered.columns and (filtered['expected_total_kw'] == 0).all():
        filtered['expected_total_kw'] = filtered['gti'] * gti_factor * TOTAL_CAPACITY_KW * pr_ratio
        filtered['expected_inverter_kw'] = filtered['gti'] * gti_factor * INVERTER_TOTAL_KW * pr_ratio

    # inverter-specific expected (if not present)
    if 'expected_goodwe_kw' not in filtered.columns:
        if 'gti' in filtered.columns:
            filtered['expected_goodwe_kw'] = filtered['gti'] * gti_factor * GOODWE_KW * pr_goodwe
            filtered['expected_fronius_kw'] = filtered['gti'] * gti_factor * FRONIUS_KW * pr_fronius
        else:
            filtered['expected_goodwe_kw'] = 0
            filtered['expected_fronius_kw'] = 0

    # Shortfall (expected_total - actual_sum)
    filtered['actual_kw'] = filtered.get('sum_grid_power', 0).fillna(0)
    filtered['shortfall_kw'] = filtered['expected_total_kw'] - filtered['actual_kw']
    filtered['shortfall_kw'] = filtered['shortfall_kw'].fillna(0)

# ------------------ PLOTTING HELPERS ------------------
SEQUOIA_COLORS = {
    "actual": "#00C853",
    "expected_total": "#007AFF",
    "expected_inverter": "#8B5CF6",
    "goodwe": "#0EA5E9",
    "fronius": "#06B6D4",
    "shortfall": "#F97316"
}

def make_plotly_timeseries(df: pd.DataFrame, traces: List[dict], title: str, height=480):
    fig = go.Figure()
    for t in traces:
        fig.add_trace(go.Scatter(x=df[t["x"]], y=df[t["y"]], name=t.get("name", t["y"]), line=t.get("line", {}), mode=t.get("mode", "lines")))
    fig.update_layout(title=title, xaxis=dict(rangeslider=dict(visible=True)), hovermode="x unified", template="simple_white", height=height, margin=dict(l=20, r=20, t=60, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01))
    return fig

# ------------------ KPI HEADER ------------------
st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
st.markdown("<div style='display:flex;justify-content:space-between;align-items:center;gap:12px'>", unsafe_allow_html=True)

# Left: title + date range
st.markdown(f"<div><h3 style='margin:0'>Overview</h3><div style='color:#6b7280'>Date range: {start_date} → {end_date}</div></div>", unsafe_allow_html=True)

# Right: KPI cards
k1, k2, k3, k4 = st.columns([1,1,1,1])
with k1:
    if not filtered.empty and 'gti' in filtered.columns:
        avg_gti = filtered['gti'].mean()
        st.markdown("<div class='kpi'><div class='metric-big'>{:.2f}</div><div class='metric-sub'>Avg GTI</div></div>".format(avg_gti), unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi'><div class='metric-big'>—</div><div class='metric-sub'>Avg GTI</div></div>", unsafe_allow_html=True)

with k2:
    if not filtered.empty:
        avg_actual = filtered['actual_kw'].mean()
        st.markdown("<div class='kpi'><div class='metric-big'>{:.1f} kW</div><div class='metric-sub'>Avg Actual Output</div></div>".format(avg_actual), unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi'><div class='metric-big'>—</div><div class='metric-sub'>Avg Actual Output</div></div>", unsafe_allow_html=True)

with k3:
    if not filtered.empty:
        avg_expected = filtered['expected_total_kw'].mean()
        st.markdown("<div class='kpi'><div class='metric-big'>{:.1f} kW</div><div class='metric-sub'>Avg Expected (total)</div></div>".format(avg_expected), unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi'><div class='metric-big'>—</div><div class='metric-sub'>Avg Expected (total)</div></div>", unsafe_allow_html=True)

with k4:
    if not filtered.empty:
        avg_short = filtered['shortfall_kw'].mean()
        est_cost_short = avg_short * 24 * cost_per_unit  # daily cost estimate approx
        st.markdown("<div class='kpi'><div class='metric-big'>{:.1f} kW</div><div class='metric-sub'>Avg Shortfall</div><div style='font-size:12px;color:#6b7280'>Est daily cost ZAR {:.2f}</div></div>".format(avg_short, est_cost_short), unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi'><div class='metric-big'>—</div><div class='metric-sub'>Avg Shortfall</div></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ------------------ PAGE ROUTING ------------------
if page == "Solar Performance":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.header("Solar Performance")
    if filtered.empty:
        st.info("No merged data found for the selected date range. Extend the range or check data sources.")
    else:
        traces = []
        if 'actual_kw' in filtered.columns:
            traces.append({"x": "last_changed", "y": "actual_kw", "name": "Actual (kW)", "line": {"color": SEQUOIA_COLORS["actual"], "width": 3}})
        if 'expected_total_kw' in filtered.columns:
            traces.append({"x": "last_changed", "y": "expected_total_kw", "name": f"Expected (Total {TOTAL_CAPACITY_KW} kW)", "line": {"color": SEQUOIA_COLORS["expected_total"], "dash": "dot", "width": 2}})
        if 'expected_inverter_kw' in filtered.columns:
            traces.append({"x": "last_changed", "y": "expected_inverter_kw", "name": f"Expected (Inverters {INVERTER_TOTAL_KW} kW)", "line": {"color": SEQUOIA_COLORS["expected_inverter"], "dash": "dash", "width": 2}})
        if 'expected_goodwe_kw' in filtered.columns:
            traces.append({"x": "last_changed", "y": "expected_goodwe_kw", "name": "Expected GoodWe", "line": {"color": SEQUOIA_COLORS["goodwe"], "dash": "dot", "width": 1.5}})
        if 'expected_fronius_kw' in filtered.columns:
            traces.append({"x": "last_changed", "y": "expected_fronius_kw", "name": "Expected Fronius", "line": {"color": SEQUOIA_COLORS["fronius"], "dash": "dot", "width": 1.5}})
        if 'shortfall_kw' in filtered.columns:
            traces.append({"x": "last_changed", "y": "shortfall_kw", "name": "Shortfall (kW)", "line": {"color": SEQUOIA_COLORS["shortfall"], "dash": "dashdot", "width": 1}})

        fig = make_plotly_timeseries(filtered, traces, "Actual vs Expected Power (kW)", height=500)
        st.plotly_chart(fig, use_container_width=True)

        # quick inverter breakdown
        st.subheader("Inverter Expected Breakdown")
        inv_df = filtered[['last_changed', 'expected_goodwe_kw', 'expected_fronius_kw']].copy()
        inv_melt = inv_df.melt(id_vars='last_changed', value_vars=['expected_goodwe_kw', 'expected_fronius_kw'], var_name='inverter', value_name='kW')
        inv_melt['inverter'] = inv_melt['inverter'].map({'expected_goodwe_kw': 'GoodWe', 'expected_fronius_kw': 'Fronius'})
        inv_fig = px.area(inv_melt, x='last_changed', y='kW', color='inverter', labels={'kW': 'kW'}, height=320)
        st.plotly_chart(inv_fig, use_container_width=True)

        # Parameter explorer
        st.subheader("Parameter Explorer")
        cols = st.columns(2)
        params = [c for c in filtered.columns if c not in ['last_changed', 'period_end', 'period'] and filtered[c].dtype != 'O']
        with cols[0]:
            sel = st.multiselect("Solar/Inverter", [p for p in params if any(k in p.lower() for k in ['fronius','goodwe','kehua','power','sum_grid_power'])],
                                 default=[p for p in params if 'sum_grid_power' in p] or [])
            for p in sel:
                st.plotly_chart(make_plotly_timeseries(filtered.rename(columns={'last_changed':'last_changed'}), [{"x":"last_changed","y":p,"name":FRIENDLY_NAMES.get(p,p),"line":{"color":"#00C853"}}], FRIENDLY_NAMES.get(p,p), height=300), use_container_width=True)
        with cols[1]:
            sel = st.multiselect("Weather", [p for p in params if p not in ['sum_grid_power','expected_total_kw'] and 'generator' not in p and 'factory' not in p and 'expected' not in p],
                                 default=['gti'] if 'gti' in filtered.columns else [])
            for p in sel:
                xcol = 'period_end' if p in weather_df.columns else 'last_changed'
                st.plotly_chart(make_plotly_timeseries(filtered, [{"x":xcol,"y":p,"name":FRIENDLY_NAMES.get(p,p),"line":{"color":"#1E88E5"}}], FRIENDLY_NAMES.get(p,p), height=300), use_container_width=True)

        # Export CSV of filtered with expected columns
        csv_buffer = io.StringIO()
        filtered.to_csv(csv_buffer, index=False)
        st.download_button("Download Filtered CSV (with expected)", csv_buffer.getvalue(), file_name=f"filtered_sequoia_{start_date}_{end_date}.csv", mime="text/csv")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.header("Generator Performance")
    if filtered.empty:
        st.info("No generator data available for the selected date range.")
    else:
        traces = []
        if 'sensor.generator_fuel_consumed' in filtered.columns:
            traces.append({"x":"last_changed","y":"sensor.generator_fuel_consumed","name":"Fuel Consumed (L)","line":{"color":"#DC2626"}})
        if 'sensor.generator_runtime_duration' in filtered.columns:
            traces.append({"x":"last_changed","y":"sensor.generator_runtime_duration","name":"Runtime (h)","line":{"color":"#7C3AED"}})
        if traces:
            st.plotly_chart(make_plotly_timeseries(filtered, traces, "Generator metrics"), use_container_width=True)
        else:
            st.info("No generator sensors found in filtered data.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory Consumption":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.header("Factory Daily Consumption")
    if 'daily_factory_kwh' in filtered.columns:
        s = filtered[['last_changed','daily_factory_kwh']].sort_values('last_changed')
        st.plotly_chart(make_plotly_timeseries(s, [{"x":"last_changed","y":"daily_factory_kwh","name":"Daily kWh","line":{"color":"#0EA5E9"}}], "Daily Factory kWh"), use_container_width=True)
    else:
        st.info("No factory data available.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua Internal":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.header("Kehua Internal Power")
    if 'sensor.kehua_internal_power' in filtered.columns:
        st.plotly_chart(make_plotly_timeseries(filtered, [{"x":"last_changed","y":"sensor.kehua_internal_power","name":"Kehua Internal (kW)","line":{"color":"#06B6D4"}}], "Kehua Internal Power (kW)"), use_container_width=True)
    else:
        st.info("No Kehua internal sensor found.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing Editor":
    st.markdown("<div class='sequoia-card'>", unsafe_allow_html=True)
    st.header("Billing Editor – September 2025")

    if BILLING_URLS:
        url = BILLING_URLS[0]
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
            ws = wb.active
        except Exception as e:
            st.error(f"Could not load billing workbook: {e}")
            ws = None

        if ws:
            col1, col2 = st.columns(2)
            with col1:
                b2 = ws['B2'].value or "30/09/25"
                try:
                    from_date = st.date_input("Date From (B2)", value=datetime.strptime(b2, "%d/%m/%y").date())
                except Exception:
                    from_date = st.date_input("Date From (B2)", value=datetime.today() - timedelta(days=30))
                b3 = ws['B3'].value or "05/11/25"
                try:
                    to_date = st.date_input("Date To (B3)", value=datetime.strptime(b3, "%d/%m/%y").date())
                except Exception:
                    to_date = st.date_input("Date To (B3)", value=datetime.today())
                days = (to_date - from_date).days
                st.metric("Days (B4)", days)

            with col2:
                def safe_cell(cellref, default=0.0):
                    try:
                        return float(ws[cellref].value or default)
                    except Exception:
                        return default

                c7 = st.number_input("Freedom Village Units (C7)", value=safe_cell("C7"))
                c9 = st.number_input("Boerdery Total Units (C9)", value=safe_cell("C9"))
                e9 = st.number_input("Boerdery Cost (E9) – Override", value=safe_cell("E9"))
                g21 = st.number_input("Drakenstein Account (G21)", value=safe_cell("G21"))

            st.subheader("Boerdery Subunits")
            c10 = st.number_input("Johan & Stoor (C10)", value=safe_cell("C10"))
            c11 = st.number_input("Pomp, Willie, Gaste, Comp (C11)", value=safe_cell("C11"))
            c12 = st.number_input("Werkers (C12)", value=safe_cell("C12"))

            if st.button("Apply Changes & Preview"):
                try:
                    ws['A1'].value = from_date.strftime("%b'%y")
                    ws['B2'].value = from_date.strftime("%d/%m/%y")
                    ws['B3'].value = to_date.strftime("%d/%m/%y")
                    ws['B4'].value = days
                    ws['C7'].value = c7
                    ws['C9'].value = c9
                    ws['C10'].value = c10
                    ws['C11'].value = c11
                    ws['C12'].value = c12
                    ws['E7'] = '=C7*D7'
                    ws['E9'].value = e9
                    ws['G21'].value = g21

                    buf = io.BytesIO()
                    wb.save(buf)
                    buf.seek(0)
                    st.session_state.edited_xlsx = buf.getvalue()

                    preview = pd.read_excel(buf, header=None)
                    st.dataframe(preview, use_container_width=True)
                except Exception as ex:
                    st.error(f"Failed to apply changes: {ex}")

            if 'edited_xlsx' in st.session_state:
                st.download_button("Download Edited September 2025.xlsx", st.session_state['edited_xlsx'], file_name=f"September 2025 - Edited ({from_date.strftime('%Y-%m-%d')}).xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.caption("Durr Bottling • Built by Hussein Akim • December 2025")
