import os
import zipfile
import tempfile
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# ---- Configuration Constants ----
UPLOAD_ROOT = "Uploads"
SOLAR_DIR = os.path.join(UPLOAD_ROOT, "solar")
WEATHER_DIR = os.path.join(UPLOAD_ROOT, "weather")
TOTAL_CAPACITY_KW = 225.78   # you may adjust if needed
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'
MAX_FILE_SIZE_MB = 10
SUPPORTED_EXTENSIONS = ['.csv', '.xlsx']

# ---- Solar Parameter Labels ----
SOLAR_LABELS = {
    'sensor.fronius_grid_power': 'Fronius Grid Power',
    'sensor.goodwe_grid_power': 'GoodWe Grid Power',
    'sensor.fronius_power_l1': 'Fronius Power L1',
    'sensor.fronius_power_l2': 'Fronius Power L2',
    'sensor.fronius_power_l3': 'Fronius Power L3',
    'sensor.goodwe_power_l1': 'GoodWe Power L1',
    'sensor.goodwe_power_l2': 'GoodWe Power L2',
    'sensor.goodwe_power_l3': 'GoodWe Power L3',
    'sensor.fronius_voltage_l1': 'Fronius Voltage L1',
    'sensor.fronius_voltage_l2': 'Fronius Voltage L2',
    'sensor.fronius_voltage_l3': 'Fronius Voltage L3',
    'sensor.goodwe_voltage_l1': 'GoodWe Voltage L1',
    'sensor.goodwe_voltage_l2': 'GoodWe Voltage L2',
    'sensor.goodwe_voltage_l3': 'GoodWe Voltage L3',
    'sensor.fronius_current_l1': 'Fronius Current L1',
    'sensor.fronius_current_l2': 'Fronius Current L2',
    'sensor.fronius_current_l3': 'Fronius Current L3',
    'sensor.goodwe_current_l1': 'GoodWe Current L1',
    'sensor.goodwe_current_l2': 'GoodWe Current L2',
    'sensor.goodwe_current_l3': 'GoodWe Current L3'
}

# ---- Weather Parameter Explainers ----
WEATHER_PARAM_EXPLAINERS = {
    "air_temp": "🌡️ **Air Temperature:** Affects panel efficiency; too high reduces output.",
    "albedo": "🪞 **Albedo:** Reflectivity of ground—higher values mean more reflected sunlight to panels.",
    "azimuth": "🧭 **Azimuth:** Direction of the sun, affecting angle of incidence on panels.",
    "clearsky_dhi": "🌤️ **Clear-sky Diffuse Horizontal Irradiance:** Sky-scattered light under ideal conditions.",
    "clearsky_dni": "🌞 **Clear-sky Direct Normal Irradiance:** Direct beam sunlight in ideal sky.",
    "clearsky_ghi": "🔆 **Clear-sky Global Horizontal Irradiance:** Total sunlight on flat surface in clear sky.",
    "clearsky_gti": "📈 **Clear-sky Global Tilted Irradiance:** Irradiance on tilted plane under clear sky.",
    "cloud_opacity": "☁️ **Cloud Opacity:** Scale from 0–10. Higher = more light blocked by clouds.",
    "dhi": "☀️ **Diffuse Horizontal Irradiance:** Scattered light from sky, not direct sun.",
    "dni": "🌅 **Direct Normal Irradiance:** Sunlight coming straight from the sun.",
    "ghi": "📉 **Global Horizontal Irradiance:** Sum of direct and diffuse light on flat plane.",
    "gti": "📊 **Global Tilted Irradiance:** Real solar input on actual panel tilt.",
    "precipitation_rate": "🌧️ **Precipitation Rate:** Heavy rain reduces sunlight, may indicate inverter faults.",
    "zenith": "🧮 **Zenith Angle:** Higher angle = sun lower in sky = less efficient light capture.",
    "weather_type": "🌦️ **Weather Type:** Descriptive condition: SUNNY, CLEAR, MOSTLY CLOUDY etc.",
    "period_end": "🕓 **Time Period End:** Timestamp of observation hour.",
    "period": "⏱️ **Period Duration:** Observation duration (e.g., PT60M for 1 hour)."
}

WEATHER_TYPE_DISPLAY = {
    "CLEAR": "☀️ Clear",
    "MOSTLY CLEAR": "🌤️ Mostly Clear",
    "MOSTLY SUNNY": "⛅ Mostly Sunny",
    "SUNNY": "🌞 Sunny"
}

# ---- Solcast Config ----
SOLCAST_LAT = -33.781051
SOLCAST_LON = 19.001587
SOLCAST_API_KEY = "XktBENtnodA78TdNRp7Myp0RkZ4AvvAn"
SOLCAST_URL = f"https://api.solcast.com.au/world_radiation/estimated_actuals?longitude={SOLCAST_LON}&latitude={SOLCAST_LAT}&format=csv&api_key={SOLCAST_API_KEY}"

# ---- UI Setup ----
st.set_page_config(page_title="⚡ Solar Performance Dashboard", layout="wide")
st.title("🌞 Solar & Weather Performance Analyzer")

# ---- Create Upload Folders ----
os.makedirs(SOLAR_DIR, exist_ok=True)
os.makedirs(WEATHER_DIR, exist_ok=True)

# ---- File Handling ----
def allowed_file(filename):
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)

def extract_zip(uploaded_zip, folder):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(uploaded_zip, 'r') as z:
            z.extractall(tmpdir)
            for name in os.listdir(tmpdir):
                fpath = os.path.join(tmpdir, name)
                if os.path.isfile(fpath) and allowed_file(name):
                    with open(fpath, 'rb') as src, open(os.path.join(folder, name), 'wb') as dst:
                        dst.write(src.read())

def save_uploaded_files(uploaded_files, folder):
    for file in uploaded_files:
        if file.name.lower().endswith(".zip"):
            extract_zip(file, folder)
        elif allowed_file(file.name):
            path = os.path.join(folder, file.name)
            with open(path, 'wb') as f:
                f.write(file.getbuffer())

def load_files_from(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f)) and allowed_file(f)]

def clear_folder(folder):
    for f in os.listdir(folder):
        try:
            os.remove(os.path.join(folder, f))
        except Exception as e:
            st.error(f"Error deleting {f}: {e}")

# ---- Upload Widget ----
def upload_widget(label, folder):
    st.subheader(label)
    session_key = f"{label}_uploaded"
    if session_key not in st.session_state:
        st.session_state[session_key] = False

    uploaded = st.file_uploader(f"Upload {label} (CSV, XLSX, or ZIP)",
                                accept_multiple_files=True,
                                type=["csv", "xlsx", "zip"],
                                key=label)

    if uploaded and not st.session_state[session_key]:
        save_uploaded_files(uploaded, folder)
        st.session_state[session_key] = True
        st.success(f"{len(uploaded)} file(s) saved!")
        st.rerun()

    if st.button(f"Clear {label}"):
        clear_folder(folder)
        st.session_state[session_key] = False
        st.success(f"All {label} files deleted.")
        st.rerun()

    files = load_files_from(folder)
    if files:
        st.caption(f"{len(files)} file(s) available")
    return files

# ---- Solcast Fetch ----
def fetch_solcast_csv():
    try:
        response = requests.get(SOLCAST_URL)
        if response.status_code == 200:
            with open(os.path.join(WEATHER_DIR, "solcast_latest.csv"), 'wb') as f:
                f.write(response.content)
            st.success("✅ Solcast data downloaded successfully!")
            st.rerun()
        else:
            st.error(f"Failed to fetch Solcast data. Status code: {response.status_code}")
    except Exception as e:
        st.error(f"Error fetching Solcast data: {e}")

# ---- Sidebar Uploads ----
st.sidebar.header("📁 Upload Your Data")
with st.sidebar.expander("Solar Data", expanded=True):
    solar_files = upload_widget("Solar Files", SOLAR_DIR)
with st.sidebar.expander("Weather Data", expanded=True):
    weather_files = upload_widget("Weather Files", WEATHER_DIR)
    if st.button("☀️ Sync from Solcast (7 days)"):
        fetch_solcast_csv()

if not solar_files or not weather_files:
    st.warning("Please upload both solar and weather data to continue.")
    st.stop()

# ---- Data Loaders ----
def load_data(files, date_column):
    dfs = []
    for file in files:
        try:
            ext = os.path.splitext(file)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(file)
            elif ext == ".xlsx":
                df = pd.read_excel(file)
            else:
                continue
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce', utc=True)
            df = df.dropna(subset=[date_column])
            df[date_column] = df[date_column].dt.tz_convert(TZ).dt.tz_localize(None)
            dfs.append(df)
        except Exception as e:
            st.error(f"Error loading {file}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# ---- Load Data ----
st.subheader("📊 Data Overview")
with st.spinner("Loading and preparing data..."):
    solar_df = load_data(solar_files, "last_changed")
    weather_df = load_data(weather_files, "period_end")

if solar_df.empty or weather_df.empty:
    st.error("Failed to load or parse data. Please check file format and column names.")
    st.stop()

# ---- Visual Controls ----
st.sidebar.header("🎛️ Chart Controls")
date_range = st.sidebar.date_input("Select Date Range", [solar_df['last_changed'].min(), solar_df['last_changed'].max()])
solar_df = solar_df[(solar_df['last_changed'] >= pd.to_datetime(date_range[0])) & (solar_df['last_changed'] <= pd.to_datetime(date_range[1]))]
weather_df = weather_df[(weather_df['period_end'] >= pd.to_datetime(date_range[0])) & (weather_df['period_end'] <= pd.to_datetime(date_range[1]))]

# ---- Plotting ----
def plot_comparison(df1, df2, time_col, y1, y2, label1, label2, color1, color2):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df1[time_col], y=df1[y1], mode='lines', name=label1, line=dict(color=color1)))
    fig.add_trace(go.Scatter(x=df2[time_col], y=df2[y2], mode='lines', name=label2, line=dict(color=color2)))
    fig.update_layout(title=f"{label1} vs {label2}", xaxis_title="Time", yaxis_title="Value", hovermode="x unified")
    return fig

st.subheader("📈 GTI vs GHI (Solcast)")
if 'gti' in weather_df.columns and 'ghi' in weather_df.columns:
    fig = plot_comparison(weather_df, weather_df, 'period_end', 'gti', 'ghi', 'Measured GTI', 'Solcast GHI', '#1f77b4', '#ff7f0e')
    st.plotly_chart(fig, use_container_width=True)

st.subheader("☁️ Cloud Opacity vs Grid Power Drop")
if 'cloud_opacity' in weather_df.columns and 'sensor.fronius_grid_power' in solar_df.columns:
    fig = plot_comparison(weather_df, solar_df, 'period_end', 'cloud_opacity', 'sensor.fronius_grid_power', 'Cloud Opacity', 'Grid Power', '#2ca02c', '#d62728')
    st.plotly_chart(fig, use_container_width=True)

# ---- Export Tools ----
st.subheader("📤 Export")
if st.button("📥 Download Combined Weather Data as CSV"):
    combined = weather_df.copy()
    st.download_button("Download", data=combined.to_csv(index=False), file_name="combined_weather.csv", mime="text/csv")

# ---- Footer ----
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Solar Analytics Dashboard</small></center>", unsafe_allow_html=True)
