# ✅ FULL ENHANCED VERSION — Unified Solar Dashboard by Hussein Akim (Sidebar Features Added)

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import zipfile
from datetime import datetime

# ---- Configuration ----
UPLOAD_ROOT = "uploads"
SOLAR_DIR = os.path.join(UPLOAD_ROOT, "solar")
WEATHER_DIR = os.path.join(UPLOAD_ROOT, "weather")
ARCHIVE_DIR = os.path.join(UPLOAD_ROOT, "archive")
DEFAULT_TOTAL_CAPACITY_KW = 221.43
DEFAULT_PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'

# ---- Setup ----
os.makedirs(SOLAR_DIR, exist_ok=True)
os.makedirs(WEATHER_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# ---- Friendly Names ----
FRIENDLY_NAMES = {
    "sensor.fronius_grid_power": "Fronius Grid Power (kW)",
    "sensor.goodwe_grid_power": "GoodWe Grid Power (kW)",
    "sum_grid_power": "Actual Power (kW)",
    "expected_power_kw": "Expected Power (kW)",
    "air_temp": "Air Temperature (\u00b0C)",
    "gti": "GTI (W/m\u00b2)",
    "ghi": "GHI (W/m\u00b2)",
    "cloud_opacity": "Cloud Opacity (%)",
    "humidity": "Humidity (%)",
    "wind_speed": "Wind Speed (m/s)",
    "weather_type": "Weather Type"
}

WEATHER_PARAM_EXPLAINERS = {
    "air_temp": "\ud83c\udf21\ufe0f Air Temperature affects panel efficiency.",
    "gti": "\ud83d\udcc8 GTI: Tilted surface irradiance.",
    "ghi": "\ud83d\udcc9 GHI: Horizontal irradiance.",
    "cloud_opacity": "\u2601\ufe0f Cloudiness effect.",
    "humidity": "\ud83d\udca7 Humidity level.",
    "wind_speed": "\ud83c\udf2c\ufe0f Cooling effect on panels.",
    "weather_type": "\ud83c\udf26\ufe0f General sky condition.",
    "expected_power_kw": "\ud83d\udd0b Expected power based on irradiance."
}

WEATHER_TYPE_DISPLAY = {
    "CLEAR": "\u2600\ufe0f Clear",
    "MOSTLY CLEAR": "\ud83c\udf24\ufe0f Mostly Clear",
    "MOSTLY SUNNY": "\u26c5 Mostly Sunny",
    "SUNNY": "\ud83c\udf1e Sunny"
}

# ---- Archive Old Files ----
def archive_old_files(folder):
    for fname in os.listdir(folder):
        fpath = os.path.join(folder, fname)
        if os.path.isfile(fpath):
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if (datetime.now() - mtime).days > 30:
                zipname = os.path.join(ARCHIVE_DIR, f"{fname}.zip")
                with zipfile.ZipFile(zipname, 'w') as z:
                    z.write(fpath, arcname=fname)
                os.remove(fpath)

archive_old_files(SOLAR_DIR)
archive_old_files(WEATHER_DIR)

# ---- App UI ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("\u2600\ufe0f GoodWe and Fronius Performance vs Weather Data — Southern Paarl")

# ---- Sidebar Enhancements ----
st.sidebar.header("\ud83d\udcc5 Controls")

with st.sidebar.expander("\ud83c\udfe2 Site Selection", expanded=True):
    site = st.selectbox("Choose Site", ["Southern Paarl", "Cape Town Test Site", "Worcester Station"])

with st.sidebar.expander("\u2699\ufe0f Advanced Settings", expanded=False):
    custom_ratio = st.slider("Performance Ratio (\u03b7)", 0.5, 1.0, value=DEFAULT_PERFORMANCE_RATIO, step=0.01)
    custom_capacity = st.number_input("System Capacity (kW)", value=DEFAULT_TOTAL_CAPACITY_KW, step=1.0)

with st.sidebar.expander("\ud83c\udfa8 Theme", expanded=False):
    theme_mode = st.radio("Select Theme", ["Light", "Dark"], index=0, key="theme_mode")

if st.session_state.get("theme_mode") == "Dark":
    st.markdown("<style>body { background-color: #111; color: white; }</style>", unsafe_allow_html=True)

# ---- Load Files from GitHub (assumes files are cloned locally)
solar_files = [f for f in os.listdir(".") if f.endswith(".csv") and "Fronius" in f]
weather_files = [f for f in os.listdir(".") if f.endswith(".csv") and "horizontal" in f]

@st.cache_data(show_spinner=False)
def load_solar(files):
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
            df = df.dropna(subset=['last_changed'])
            df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            pivoted = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            dfs.append(pivoted)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_weather(files):
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        if 'period_end' not in df.columns:
            continue
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
        df = df.dropna(subset=['period_end'])
        df['period_end'] = df['period_end'].dt.tz_convert(TZ).dt.tz_localize(None)
        for col in df.columns:
            if col not in ['period_end', 'period']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        dfs.append(df)
    weather = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    if 'gti' in weather.columns:
        weather['expected_power_kw'] = weather['gti'] * custom_capacity * custom_ratio / 1000
    return weather

solar_df = load_solar(solar_files)
weather_df = load_weather(weather_files)

if solar_df.empty or weather_df.empty:
    st.warning("One of the datasets is empty after loading.")
    st.stop()

merged_df = pd.merge_asof(
    solar_df.sort_values("last_changed"),
    weather_df.sort_values("period_end"),
    left_on="last_changed", right_on="period_end")

st.sidebar.header("\ud83d\uddd3\ufe0f Date Filter")
min_date = merged_df['last_changed'].min()
max_date = merged_df['last_changed'].max()
start, end = st.sidebar.date_input("Select Date Range", [min_date, max_date])
filtered = merged_df[(merged_df['last_changed'] >= pd.to_datetime(start)) & (merged_df['last_changed'] <= pd.to_datetime(end))]

if 'sensor.fronius_grid_power' in filtered.columns and 'sensor.goodwe_grid_power' in filtered.columns:
    filtered['sensor.fronius_grid_power'] = filtered['sensor.fronius_grid_power'] / 1000
    filtered['sensor.goodwe_grid_power'] = filtered['sensor.goodwe_grid_power'] / 1000
    filtered['sum_grid_power'] = filtered['sensor.fronius_grid_power'].fillna(0) + filtered['sensor.goodwe_grid_power'].fillna(0)

# ---- Plot Utility ----
def slider_chart(df, x_col, y_col, title, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], name=FRIENDLY_NAMES.get(y_col, y_col), line=dict(color=color)))
    fig.update_layout(
        title=title,
        xaxis=dict(title=x_col, rangeslider=dict(visible=True), type="date"),
        yaxis=dict(title=FRIENDLY_NAMES.get(y_col, y_col)),
        hovermode='x unified'
    )
    return fig

# ---- Charts ----
st.subheader("\ud83c\udf1e Actual vs Expected Power")
fig = slider_chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "green")
if 'expected_power_kw' in filtered.columns:
    fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'], name="Expected", line=dict(color="orange")))
st.plotly_chart(fig, use_container_width=True)

st.subheader("\ud83d\udcca Parameter Explorer")
available_params = [c for c in filtered.columns if c not in ['last_changed', 'period_end', 'period'] and filtered[c].dtype != 'O']
param_selection = st.multiselect("Select parameters to visualize:", available_params, default=['sensor.fronius_grid_power', 'sensor.goodwe_grid_power'])
for col in param_selection:
    fig = slider_chart(filtered, 'last_changed', col, FRIENDLY_NAMES.get(col, col), '#1e90ff')
    st.plotly_chart(fig, use_container_width=True)
    if col in WEATHER_PARAM_EXPLAINERS:
        st.markdown(WEATHER_PARAM_EXPLAINERS[col])

if 'weather_type' in filtered.columns:
    st.subheader("\ud83c\udf24\ufe0f Weather Type Overview")
    counts = filtered['weather_type'].value_counts().head(5).reset_index()
    counts.columns = ['Weather', 'Count']
    counts['Weather'] = counts['Weather'].map(WEATHER_TYPE_DISPLAY).fillna(counts['Weather'])
    st.dataframe(counts)

st.download_button("\ud83d\udcc4 Download Merged CSV", filtered.to_csv(index=False), file_name="merged_data.csv")
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim \u2014 Unified Solar Insights</small></center>", unsafe_allow_html=True)
