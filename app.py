# ✅ FINAL VERSION — Unified Solar Dashboard by Hussein Akim (history.CSV support)
# Features: GitHub data loading, local history.CSV support, full sidebar control panel, GTI & PR tuning, dual-chart explorer, kW units, max power recording

import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

# ---- Configuration ----
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
HISTORY_FILE = "history.CSV"

# ---- Friendly Names ----
FRIENDLY_NAMES = {
    "sensor.fronius_grid_power": "Fronius Grid Power (kW)",
    "sensor.goodwe_grid_power": "GoodWe Grid Power (kW)",
    "sum_grid_power": "Actual Power (kW)",
    "expected_power_kw": "Expected Power (kW)",
    "air_temp": "Air Temperature (°C)",
    "gti": "GTI (W/m²)",
    "ghi": "GHI (W/m²)",
    "cloud_opacity": "Cloud Opacity (%)",
    "humidity": "Humidity (%)",
    "wind_speed": "Wind Speed (m/s)",
    "weather_type": "Weather Type"
}

WEATHER_PARAM_EXPLAINERS = {
    "air_temp": "🌡️ Air Temperature affects panel efficiency.",
    "gti": "📈 GTI: Tilted surface irradiance.",
    "ghi": "📉 GHI: Horizontal irradiance.",
    "cloud_opacity": "☁️ Cloudiness effect.",
    "humidity": "💧 Humidity level.",
    "wind_speed": "💨 Cooling effect on panels.",
    "expected_power_kw": "🔋 Expected power based on irradiance.",
}

# ---- UI Setup ----
st.set_page_config(page_title="Unified Solar Dashboard", layout="wide")
st.title("☀️ GoodWe and Fronius Performance vs Weather Data")

# Sidebar Controls
st.sidebar.header("🗓️ Controls")
site = st.sidebar.selectbox("Site", ["Southern Paarl"])
gti_factor = st.sidebar.slider("GTI Factor (W/m²)", 0.5, 1.5, 1.0)
pr_ratio = st.sidebar.slider("Performance Ratio", 0.5, 1.0, PERFORMANCE_RATIO)

# ---- Load Data ----
@st.cache_data(show_spinner=False)
def load_solar():
    """Load solar CSVs from remote URLs and an optional local history.CSV if present.
    All source CSVs are expected to contain columns: last_changed, state, entity_id (Home Assistant history export format).
    The function pivots each source into time-indexed columns keyed by entity_id.
    """
    dfs = []
    # Remote CSVs
    for url in SOLAR_URLS:
        try:
            df = pd.read_csv(url)
        except Exception:
            continue
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
            df = df.dropna(subset=['last_changed'])
            df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            pivoted = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            dfs.append(pivoted)
    # Local history.CSV (if present in the repo working directory)
    if os.path.exists(HISTORY_FILE):
        try:
            hdf = pd.read_csv(HISTORY_FILE)
            if {'last_changed', 'state', 'entity_id'}.issubset(hdf.columns):
                hdf['last_changed'] = pd.to_datetime(hdf['last_changed'], utc=True, errors='coerce')
                hdf = hdf.dropna(subset=['last_changed'])
                hdf['last_changed'] = hdf['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
                hdf['state'] = pd.to_numeric(hdf['state'], errors='coerce').abs()
                hdf['entity_id'] = hdf['entity_id'].str.lower().str.strip()
                pivoted_h = hdf.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
                dfs.append(pivoted_h)
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

@st.cache_data(show_spinner=False)
def load_weather(gti_factor_local, pr_ratio_local):
    df = pd.read_csv(WEATHER_URL)
    df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
    df = df.dropna(subset=['period_end'])
    df['period_end'] = df['period_end'].dt.tz_convert(TZ).dt.tz_localize(None)
    for col in df.columns:
        if col not in ['period_end', 'period']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'gti' in df.columns:
        df['expected_power_kw'] = df['gti'] * gti_factor_local * TOTAL_CAPACITY_KW * pr_ratio_local / 1000
    return df

solar_df = load_solar()
weather_df = load_weather(gti_factor, pr_ratio)

# Inform user if history.CSV was detected and included
if os.path.exists(HISTORY_FILE):
    st.sidebar.success(f"Detected and loaded local {HISTORY_FILE} — included in solar data.")

# ---- Merge & Clean ----
if solar_df.empty:
    st.warning("No solar time-series data found from configured sources.")
    st.stop()

# Ensure sort for merge_asof
merged_df = pd.merge_asof(solar_df.sort_values("last_changed"), weather_df.sort_values("period_end"), left_on="last_changed", right_on="period_end")

# Add calculated columns
if 'sensor.fronius_grid_power' in merged_df.columns:
    merged_df['sensor.fronius_grid_power'] = pd.to_numeric(merged_df['sensor.fronius_grid_power'], errors='coerce') / 1000
if 'sensor.goodwe_grid_power' in merged_df.columns:
    merged_df['sensor.goodwe_grid_power'] = pd.to_numeric(merged_df['sensor.goodwe_grid_power'], errors='coerce') / 1000

merged_df['sum_grid_power'] = merged_df.get('sensor.fronius_grid_power', 0).fillna(0) + merged_df.get('sensor.goodwe_grid_power', 0).fillna(0)

# Record Max Values safely
max_fronius = float(merged_df['sensor.fronius_grid_power'].max()) if 'sensor.fronius_grid_power' in merged_df.columns else 0.0
max_goodwe = float(merged_df['sensor.goodwe_grid_power'].max()) if 'sensor.goodwe_grid_power' in merged_df.columns else 0.0

# ---- Date Filter ----
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Date Range")
min_date = pd.to_datetime(merged_df['last_changed'].min())
max_date = pd.to_datetime(merged_df['last_changed'].max())
start_date, end_date = st.sidebar.date_input("Select range", [min_date.date(), max_date.date()])
filtered = merged_df[(merged_df['last_changed'] >= pd.to_datetime(start_date)) & (merged_df['last_changed'] <= pd.to_datetime(end_date))]

if filtered.empty:
    st.warning("No data available in the selected date range.")
    st.stop()

# ---- Chart Function ----
def slider_chart(df, x_col, y_col, title, color):
    label = FRIENDLY_NAMES.get(y_col, y_col)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], name=label, line=dict(color=color)))
    fig.update_layout(
        title=title,
        xaxis=dict(title=x_col, rangeslider=dict(visible=True), type="date"),
        yaxis=dict(title=label),
        hovermode='x unified'
    )
    return fig

# ---- Actual vs Expected ----
st.subheader("🌞 Actual vs Expected Power")
fig = slider_chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "green")
if 'expected_power_kw' in filtered.columns:
    fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'], name=FRIENDLY_NAMES['expected_power_kw'], line=dict(color="orange")))
st.plotly_chart(fig, use_container_width=True)

# ---- Dual Parameter Explorer ----
st.subheader("📊 Parameter Explorer")
params = [c for c in filtered.columns if c not in ['last_changed', 'period_end', 'period'] and filtered[c].dtype != 'O']
solar_params = [p for p in params if 'grid' in p or 'power' in p]
weather_params = [p for p in params if p not in solar_params]

col1, col2 = st.columns(2)
with col1:
    selected_solar = st.multiselect("🔌 Solar Parameters", solar_params, default=solar_params[:2])
    for p in selected_solar:
        st.plotly_chart(slider_chart(filtered, 'last_changed', p, FRIENDLY_NAMES.get(p, p), '#33CFA5'), use_container_width=True)

with col2:
    selected_weather = st.multiselect("☁️ Weather Parameters", weather_params, default=weather_params[:2])
    for p in selected_weather:
        # Some weather params are tied to period_end
        xcol = 'period_end' if p in weather_df.columns else 'last_changed'
        st.plotly_chart(slider_chart(filtered, xcol, p, FRIENDLY_NAMES.get(p, p), '#1f77b4'), use_container_width=True)
        if p in WEATHER_PARAM_EXPLAINERS:
            st.markdown(WEATHER_PARAM_EXPLAINERS[p])

# ---- Max Power Display ----
st.markdown(f"**🔋 Max Fronius Grid Power:** {max_fronius:.2f} kW")
st.markdown(f"**🔋 Max GoodWe Grid Power:** {max_goodwe:.2f} kW")

# ---- Export ----
st.download_button("📄 Download Merged CSV", filtered.to_csv(index=False), file_name="merged_data.csv")
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Unified Solar Insights</small></center>", unsafe_allow_html=True)