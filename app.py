# Merged Streamlit App: Unified + Upgraded Solar Dashboard by Hussein Akim (Debugged)

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import zipfile
from datetime import datetime, timedelta

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

# ---- File Handlers ----
def save_files_to_disk(uploaded_files, folder):
    for file in uploaded_files:
        file_path = os.path.join(folder, file.name)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

def load_files_from_disk(folder):
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith(".csv")]

def delete_files_from_disk(folder):
    for f in os.listdir(folder):
        os.remove(os.path.join(folder, f))

# ---- Upload UI ----
def upload_section(label, folder):
    st.write(f"### {label}")
    existing_files = load_files_from_disk(folder)
    if existing_files:
        st.success(f"{len(existing_files)} file(s) stored")
        for f in existing_files:
            col1, col2 = st.columns([4, 1])
            col1.write(os.path.basename(f))
            if col2.button("Delete", key=f"del_{f}"):
                os.remove(f)
                st.experimental_rerun()
        if st.button(f"Clear all {label}"):
            delete_files_from_disk(folder)
            st.experimental_rerun()

    uploaded_files = st.file_uploader(f"Add {label}", type="csv", accept_multiple_files=True, key=f"uploader_{label}")
    if uploaded_files:
        st.write("Uploaded files:", [f.name for f in uploaded_files])
        if st.button(f"Upload {label}"):
            save_files_to_disk(uploaded_files, folder)
            st.success("Files uploaded.")
            st.experimental_rerun()
    return load_files_from_disk(folder)

# ---- App Layout ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("☀️ Unified Solar Dashboard")

st.sidebar.header("📁 Upload Data")
with st.sidebar.expander("Solar Data", expanded=True):
    solar_files = upload_section("Solar", SOLAR_DIR)
with st.sidebar.expander("Weather Data", expanded=True):
    weather_files = upload_section("Weather", WEATHER_DIR)

st.write("Solar Files:", solar_files)
st.write("Weather Files:", weather_files)

if not solar_files or not weather_files:
    st.warning("Upload both solar and weather data to begin analysis.")
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
        df['state'] = pd.to_numeric(df['state'], errors='coerce')
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

try:
    solar_df = load_solar(solar_files)
    weather_df = load_weather(weather_files)
    if solar_df.empty or weather_df.empty:
        st.warning("One of the datasets is empty after loading. Check your CSVs.")
        st.stop()
    merged_df = pd.merge_asof(solar_df.sort_values("last_changed"), weather_df.sort_values("period_end"), left_on="last_changed", right_on="period_end")
except Exception as e:
    st.error(f"Error during file loading: {e}")
    st.stop()

# ---- Date Filter ----
st.sidebar.header("📅 Date Filter")
min_date = merged_df['last_changed'].min()
max_date = merged_df['last_changed'].max()
start, end = st.sidebar.date_input("Select Date Range", [min_date, max_date])
filtered = merged_df[(merged_df['last_changed'] >= pd.to_datetime(start)) & (merged_df['last_changed'] <= pd.to_datetime(end))]

if filtered.empty:
    st.warning("No data available in the selected date range.")
    st.stop()

# ---- Plot Charts ----
st.subheader("🌞 Actual vs Expected Power")
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['state'], name="Actual", line=dict(color="green")))
if 'expected_power_kw' in filtered.columns:
    fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'], name="Expected", line=dict(color="orange")))
st.plotly_chart(fig, use_container_width=True)

if 'sensor.fronius_grid_power' in filtered.columns and 'sensor.goodwe_grid_power' in filtered.columns:
    st.subheader("⚡ Sum of Fronius and GoodWe Grid Power")
    filtered['sum_grid_power'] = filtered['sensor.fronius_grid_power'].fillna(0) + filtered['sensor.goodwe_grid_power'].fillna(0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['sum_grid_power'], name="Sum Grid Power", line=dict(color="#A020F0")))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("🌦️ Weather Parameters")
for col in [c for c in weather_df.columns if c not in ['period_end', 'period']]:
    if col not in filtered.columns or filtered[col].dtype not in [float, int]:
        continue
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered['period_end'], y=filtered[col], name=col))
    st.plotly_chart(fig, use_container_width=True)
    if col in WEATHER_PARAM_EXPLAINERS:
        st.markdown(WEATHER_PARAM_EXPLAINERS[col])

if 'weather_type' in filtered.columns:
    st.subheader("🌤️ Weather Type Overview")
    counts = filtered['weather_type'].value_counts().head(5).reset_index()
    counts.columns = ['Weather', 'Count']
    counts['Weather'] = counts['Weather'].map(WEATHER_TYPE_DISPLAY).fillna(counts['Weather'])
    st.dataframe(counts)

st.download_button("📄 Download Merged CSV", filtered.to_csv(index=False), file_name="merged_data.csv")
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Unified Solar Insights</small></center>", unsafe_allow_html=True)
