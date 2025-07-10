# ✅ FULL WORKING VERSION — Unified Solar Dashboard by Hussein Akim (kW units + Cleaned)
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

ADMIN_PASSWORD = "your_admin_password"  # <<<--- CHANGE THIS TO YOUR ACTUAL PASSWORD

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

def delete_files_from_disk(folder):
    for f in os.listdir(folder):
        os.remove(os.path.join(folder, f))

# ---- Admin Auth ----
def is_admin():
    return st.session_state.get('is_admin', False)

if 'auth_checked' not in st.session_state:
    st.session_state['auth_checked'] = False

if not st.session_state['auth_checked']:
    with st.sidebar:
        st.markdown("### 🔒 Admin Login (for uploading files)")
        admin_pw = st.text_input("Enter admin password to unlock upload features", type="password")
        if st.button("Login as Admin"):
            if admin_pw == ADMIN_PASSWORD:
                st.session_state['is_admin'] = True
                st.success("Admin mode enabled.")
            else:
                st.session_state['is_admin'] = False
                st.error("Incorrect password.")
            st.session_state['auth_checked'] = True
    st.stop()

# ---- App UI ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("☀️ Goowe and Fronius Performance vs Weather data of Southern Paarl \n\n")

# ---- Show currently uploaded files ----
def list_uploaded_files():
    solar_files = load_files_from_disk(SOLAR_DIR)
    weather_files = load_files_from_disk(WEATHER_DIR)
    return solar_files, weather_files

solar_files, weather_files = list_uploaded_files()

st.sidebar.markdown("### 📄 Previously Uploaded Files")
st.sidebar.write("**Solar files:**")
if solar_files:
    for f in solar_files:
        st.sidebar.write(os.path.basename(f))
else:
    st.sidebar.write("_No solar files uploaded yet_")
st.sidebar.write("**Weather files:**")
if weather_files:
    for f in weather_files:
        st.sidebar.write(os.path.basename(f))
else:
    st.sidebar.write("_No weather files uploaded yet_")

# ---- Upload Section (Admin Only) ----
if is_admin():
    st.sidebar.header("📁 Upload Data")
    with st.sidebar.expander("Solar Data", expanded=True):
        solar_uploaded = st.file_uploader("Upload Solar CSV(s)", type="csv", accept_multiple_files=True, key="solar")
        if solar_uploaded:
            st.session_state['solar_ready'] = True
            st.success(f"{len(solar_uploaded)} file(s) ready")
    with st.sidebar.expander("Weather Data", expanded=True):
        weather_uploaded = st.file_uploader("Upload Weather CSV(s)", type="csv", accept_multiple_files=True, key="weather")
        if weather_uploaded:
            st.session_state['weather_ready'] = True
            st.success(f"{len(weather_uploaded)} file(s) ready")
    upload_btn = st.sidebar.button("🚀 Upload and Analyze")
    if upload_btn:
        if not solar_uploaded or not weather_uploaded:
            st.error("Please upload both solar and weather CSV files.")
            st.stop()
        save_files_to_disk(solar_uploaded, SOLAR_DIR)
        save_files_to_disk(weather_uploaded, WEATHER_DIR)
        st.success("✅ Files saved. Reloading...")
        st.rerun()
else:
    st.sidebar.info("You are in viewer mode. Only previously uploaded files are available for analysis.")

# ---- Analyze Button for All Users ----
analyze_btn = st.sidebar.button("🔍 Analyze Data")

if not solar_files or not weather_files:
    st.warning("No solar or weather files uploaded yet. (Admin must upload them first.)")
    st.stop()

if not analyze_btn and not is_admin():
    st.info("Click 'Analyze Data' to load and analyze the latest uploaded files.")
    st.stop()

# ---- Data Loading ----
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

st.sidebar.header("📅 Date Filter")
min_date = merged_df['last_changed'].min()
max_date = merged_df['last_changed'].max()
start, end = st.sidebar.date_input("Select Date Range", [min_date, max_date])
filtered = merged_df[(merged_df['last_changed'] >= pd.to_datetime(start)) & (merged_df['last_changed'] <= pd.to_datetime(end))]

if filtered.empty:
    st.warning("No data available in the selected date range.")
    st.stop()

# ---- Actual Power Calculation ----
if 'sensor.fronius_grid_power' in filtered.columns and 'sensor.goodwe_grid_power' in filtered.columns:
    filtered['sensor.fronius_grid_power'] = filtered['sensor.fronius_grid_power'] / 1000
    filtered['sensor.goodwe_grid_power'] = filtered['sensor.goodwe_grid_power'] / 1000
    filtered['sum_grid_power'] = filtered['sensor.fronius_grid_power'].fillna(0) + filtered['sensor.goodwe_grid_power'].fillna(0)

# ---- Chart Utility ----
def slider_chart(df, x_col, y_col, title, color):
    fig = go.Figure()
    y_label = FRIENDLY_NAMES.get(y_col, y_col)
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], name=y_label, line=dict(color=color)))
    fig.update_layout(
        title=title,
        xaxis=dict(title=x_col, rangeslider=dict(visible=True), type="date"),
        yaxis=dict(title=y_label),
        hovermode='x unified'
    )
    return fig

# ---- Main Charts ----
st.subheader("🌞 Actual vs Expected Power")
fig = slider_chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "green")
if 'expected_power_kw' in filtered.columns:
    fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'], name=FRIENDLY_NAMES['expected_power_kw'], line=dict(color="orange")))
st.plotly_chart(fig, use_container_width=True)

st.subheader("📊 Parameter Explorer")
available_params = [c for c in filtered.columns if c not in ['last_changed', 'period_end', 'period'] and filtered[c].dtype != 'O']
param_selection = st.multiselect("Select parameters to visualize:", available_params, default=['sensor.fronius_grid_power', 'sensor.goodwe_grid_power'])
for col in param_selection:
    fig = slider_chart(filtered, 'last_changed', col, FRIENDLY_NAMES.get(col, col), '#1e90ff')
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
