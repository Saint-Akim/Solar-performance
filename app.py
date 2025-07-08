# ✅ FINAL MERGED VERSION — Unified Solar Dashboard with Parameter Selection, Sliders, and Data Fixes

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
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'

# ---- Setup ----
os.makedirs(SOLAR_DIR, exist_ok=True)
os.makedirs(WEATHER_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# ---- Weather Explainable Info ----
WEATHER_PARAM_EXPLAINERS = {
    "air_temp": "🌡️ Air Temperature affects panel efficiency.",
    "gti": "📈 GTI: Tilted surface irradiance.",
    "ghi": "📉 GHI: Horizontal irradiance.",
    "cloud_opacity": "☁️ Cloudiness effect.",
    "humidity": "💧 Humidity level.",
    "wind_speed": "💨 Cooling effect on panels.",
    "weather_type": "🌦️ General sky condition.",
    "expected_power_kw": "🔋 Expected power based on irradiance.",
    "period_end": "🕒 Weather timestamp."
}

WEATHER_TYPE_DISPLAY = {
    "CLEAR": "☀️ Clear",
    "MOSTLY CLEAR": "🌤️ Mostly Clear",
    "MOSTLY SUNNY": "⛅ Mostly Sunny",
    "SUNNY": "🌞 Sunny"
}

# ---- Utilities ----
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

# ---- File Handling ----
def save_files_to_disk(uploaded_files, folder):
    for file in uploaded_files:
        file_path = os.path.join(folder, file.name)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

def load_files_from_disk(folder):
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith(".csv")]

# ---- App UI ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("☀️ Unified Solar Dashboard")

st.sidebar.header("📁 Upload Data")

with st.sidebar.expander("Solar Data", expanded=True):
    solar_uploaded = st.file_uploader("Upload Solar CSV(s)", type="csv", accept_multiple_files=True, key="solar")
    if solar_uploaded:
        st.session_state['solar_ready'] = True

with st.sidebar.expander("Weather Data", expanded=True):
    weather_uploaded = st.file_uploader("Upload Weather CSV(s)", type="csv", accept_multiple_files=True, key="weather")
    if weather_uploaded:
        st.session_state['weather_ready'] = True

run_btn = st.sidebar.button("🚀 Run Analysis")
if run_btn:
    if not solar_uploaded or not weather_uploaded:
        st.error("Please upload both solar and weather CSV files.")
        st.stop()
    save_files_to_disk(solar_uploaded, SOLAR_DIR)
    save_files_to_disk(weather_uploaded, WEATHER_DIR)
    st.success("✅ Files saved. Reloading...")
    st.rerun()

solar_files = load_files_from_disk(SOLAR_DIR)
weather_files = load_files_from_disk(WEATHER_DIR)

if not solar_files or not weather_files:
    st.warning("Upload both solar and weather data and click 'Run Analysis'.")
    st.stop()

@st.cache_data(show_spinner=False)
def load_solar(files):
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        required_cols = {'last_changed', 'state', 'entity_id'}
        if not required_cols.issubset(df.columns):
            st.error(f"Missing required columns in {f}: {required_cols - set(df.columns)}")
            continue
        df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
        df = df.dropna(subset=['last_changed'])
        df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
        df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
        df['entity_id'] = df['entity_id'].str.lower().str.strip()
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_weather(files):
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        if 'period_end' not in df.columns:
            st.error(f"Missing 'period_end' in weather file {f}")
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
        weather['expected_power_kw'] = weather['gti'] * TOTAL_CAPACITY_KW * PERFORMANCE_RATIO / 1000
    return weather

solar_df = load_solar(solar_files)
weather_df = load_weather(weather_files)
if solar_df.empty or weather_df.empty:
    st.warning("One of the datasets is empty after loading. Check your CSVs.")
    st.stop()

merged_df = pd.merge_asof(
    solar_df.sort_values("last_changed"),
    weather_df.sort_values("period_end"),
    left_on="last_changed",
    right_on="period_end"
)

st.sidebar.header("📅 Date Filter")
min_date = merged_df['last_changed'].min()
max_date = merged_df['last_changed'].max()
start, end = st.sidebar.date_input("Select Date Range", [min_date, max_date])
filtered = merged_df[(merged_df['last_changed'] >= pd.to_datetime(start)) & (merged_df['last_changed'] <= pd.to_datetime(end))]

if filtered.empty:
    st.warning("No data available in the selected date range.")
    st.stop()

# ---- Parameter Selection ----
st.sidebar.header("📊 Chart Controls")

solar_params = filtered['entity_id'].unique().tolist()
weather_params = [col for col in weather_df.columns if col not in ['period_end', 'period']]

solar_selected = st.sidebar.multiselect("Select Solar Parameters", options=solar_params)
weather_selected = st.sidebar.multiselect("Select Weather Parameters", options=weather_params)

# ---- Plot Function ----
def slider_chart(df, x_col, y_col, title, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], name=y_col, line=dict(color=color)))
    fig.update_layout(
        title=title,
        xaxis=dict(
            title=x_col,
            rangeslider=dict(visible=True),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1d", step="day", stepmode="backward"),
                    dict(count=7, label="1w", step="day", stepmode="backward"),
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            type="date"
        ),
        yaxis=dict(title=y_col),
        hovermode='x unified'
    )
    return fig

# ---- Solar Charts ----
st.subheader("🌞 Actual vs Expected Power")
fig = slider_chart(filtered, 'last_changed', 'state', "Actual Power", "green")
if 'expected_power_kw' in filtered.columns:
    fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'], name="Expected", line=dict(color="orange")))
st.plotly_chart(fig, use_container_width=True)

# ---- Entity Charts ----
for entity in solar_selected:
    df_entity = filtered[filtered['entity_id'] == entity]
    fig = slider_chart(df_entity, 'last_changed', 'state', f"{entity} Output", "#17BECF")
    st.plotly_chart(fig, use_container_width=True)

# ---- Grid Power ----
if 'sensor.fronius_grid_power' in filtered.columns and 'sensor.goodwe_grid_power' in filtered.columns:
    st.subheader("⚡ Sum of Fronius and GoodWe Grid Power")
    filtered['sum_grid_power'] = filtered['sensor.fronius_grid_power'].fillna(0) + filtered['sensor.goodwe_grid_power'].fillna(0)
    fig = slider_chart(filtered, 'last_changed', 'sum_grid_power', "Sum Grid Power", "#A020F0")
    st.plotly_chart(fig, use_container_width=True)

# ---- Weather Charts ----
st.subheader("🌦️ Weather Parameters")
for col in weather_selected:
    if col in filtered.columns:
        fig = slider_chart(filtered, 'period_end', col, col, "#1e90ff")
        st.plotly_chart(fig, use_container_width=True)
        if col in WEATHER_PARAM_EXPLAINERS:
            st.markdown(WEATHER_PARAM_EXPLAINERS[col])

# ---- Weather Type Overview ----
if 'weather_type' in filtered.columns:
    st.subheader("🌤️ Weather Type Overview")
    counts = filtered['weather_type'].value_counts().head(5).reset_index()
    counts.columns = ['Weather', 'Count']
    counts['Weather'] = counts['Weather'].map(WEATHER_TYPE_DISPLAY).fillna(counts['Weather'])
    st.dataframe(counts)

st.download_button("📄 Download Merged CSV", filtered.to_csv(index=False), file_name="merged_data.csv")
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Unified Solar Insights</small></center>", unsafe_allow_html=True)
