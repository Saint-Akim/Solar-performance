# app.py — Unified Solar Dashboard by Hussein Akim with Upgrades

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import platform
import psutil
import zipfile
from datetime import datetime, timedelta

# ---- Configuration ----
UPLOAD_ROOT = "Uploads"
SOLAR_DIR = os.path.join(UPLOAD_ROOT, "solar")
WEATHER_DIR = os.path.join(UPLOAD_ROOT, "weather")
ARCHIVE_DIR = os.path.join(UPLOAD_ROOT, "Archive")
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'
ADMIN_PASSWORD = "admin123"

# ---- Setup ----
os.makedirs(SOLAR_DIR, exist_ok=True)
os.makedirs(WEATHER_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# ---- Friendly Labels ----
SOLAR_LABELS = {
    'sensor.fronius_grid_power': 'Fronius Grid Power',
    'sensor.goodwe_grid_power': 'GoodWe Grid Power',
    'sensor.fronius_power_l1': 'Fronius Power L1',
    'sensor.fronius_power_l2': 'Fronius Power L2',
    'sensor.fronius_power_l3': 'Fronius Power L3',
    'sensor.goodwe_power_l1': 'GoodWe Power L1',
    'sensor.goodwe_power_l2': 'GoodWe Power L2',
    'sensor.goodwe_power_l3': 'GoodWe Power L3'
    # Add more as needed
}

# ---- Weather Parameter Explainers (expanded & improved) ----
WEATHER_PARAM_EXPLAINERS = {
    "air_temp": "🌡️ **Air Temperature:** High temperatures can reduce the efficiency of solar panels—typically by about 0.4% per °C above 25°C—resulting in lower energy output on hot days.",
    "gti": "📈 **Global Tilted Irradiance (GTI):** The amount of solar energy received on a tilted surface, directly impacting solar production.",
    "ghi": "📉 **Global Horizontal Irradiance (GHI):** Measures sunlight on a flat surface; an indicator of available solar resource.",
    "cloud_opacity": "☁️ **Cloud Opacity:** Higher values mean more sunlight is being blocked by clouds.",
    "humidity": "💧 **Humidity:** High humidity can reduce sunlight through increased cloudiness, lowering panel output.",
    "wind_speed": "💨 **Wind Speed:** Wind can cool panels, making them more efficient, but excessive wind may signal storms or dust.",
    "weather_type": "🌦️ **Weather Type:** General sky condition (e.g., SUNNY, CLEAR, etc.), descriptive only.",
    "expected_power_kw": "🔋 **Expected Power:** Calculated based on irradiance, system size, and performance ratio; shows what your system should ideally produce.",
    "period_end": "🕒 **Period End:** The time this weather data was recorded."
}

WEATHER_TYPE_DISPLAY = {
    "CLEAR": "☀️ Clear",
    "MOSTLY CLEAR": "🌤️ Mostly Clear",
    "MOSTLY SUNNY": "⛅ Mostly Sunny",
    "SUNNY": "🌞 Sunny"
}

# ---- Utility ----
def file_disk_action(folder, action, filename=None):
    if action == "load":
        return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith(".csv")]
    elif action == "delete_all":
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))
    elif action == "delete_one" and filename:
        os.remove(os.path.join(folder, filename))

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

# ---- UI ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("☀️ Solar Performance & Weather Analyzer")

st.sidebar.header("📁 Upload Files")

with st.sidebar.expander("Solar Data", expanded=True):
    solar_files = file_disk_action(SOLAR_DIR, "load")
    if st.button("Download All Solar as Zip"):
        zip_path = os.path.join(UPLOAD_ROOT, "solar_all.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for f in solar_files:
                zipf.write(f, arcname=os.path.basename(f))
        with open(zip_path, "rb") as z:
            st.download_button("Download Solar Zip", z, file_name="solar_all.zip")

with st.sidebar.expander("Weather Data", expanded=True):
    weather_files = file_disk_action(WEATHER_DIR, "load")
    if st.button("Download All Weather as Zip"):
        zip_path = os.path.join(UPLOAD_ROOT, "weather_all.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for f in weather_files:
                zipf.write(f, arcname=os.path.basename(f))
        with open(zip_path, "rb") as z:
            st.download_button("Download Weather Zip", z, file_name="weather_all.zip")

# ---- Load Data ----
def load_data(files, time_col):
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce').dt.tz_localize(None)
    return df.sort_values(time_col)

if solar_files and weather_files:
    df_solar = load_data(solar_files, "last_changed")
    df_weather = load_data(weather_files, "period_end")
    df = pd.merge_asof(df_solar, df_weather, left_on="last_changed", right_on="period_end")
    df["expected_power_kw"] = (df["gti"] * TOTAL_CAPACITY_KW * PERFORMANCE_RATIO) / 1000

    st.subheader("🌞 Energy vs Expected")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["last_changed"], y=df["state"], name="Actual", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=df["last_changed"], y=df["expected_power_kw"], name="Expected", line=dict(color="orange")))
    st.plotly_chart(fig, use_container_width=True)

    # --- Sum of Fronius and GoodWe Grid Power Chart ---
    if "sensor.fronius_grid_power" in df.columns and "sensor.goodwe_grid_power" in df.columns:
        df["sum_grid_power"] = df["sensor.fronius_grid_power"].fillna(0) + df["sensor.goodwe_grid_power"].fillna(0)
        fig_sum = go.Figure()
        fig_sum.add_trace(go.Scatter(
            x=df["last_changed"], y=df["sum_grid_power"],
            name="Sum Grid Power", line=dict(color="#A020F0")))
        st.markdown("#### Sum of Fronius and GoodWe Grid Power")
        st.plotly_chart(fig_sum, use_container_width=True)
        st.markdown("⚡ **This chart shows the combined grid power measured by both the Fronius and GoodWe sensors, providing a holistic view of your system's total grid contribution.**")

    # ---- Weather Parameter Charts ----
    weather_chart_cols = [c for c in df_weather.columns if c not in ["period_end", "period"]]
    for param in weather_chart_cols:
        if param not in df.columns or df[param].dtype not in [float, int]:
            continue
        st.subheader(f"🌦️ {param.replace('_', ' ').title()}")
        fig_weather = go.Figure()
        fig_weather.add_trace(go.Scatter(
            x=df["period_end"], y=df[param],
            name=param, line=dict(color="#1e90ff")))
        st.plotly_chart(fig_weather, use_container_width=True)
        # Add explainer below each chart if available
        key = param.lower()
        explainer = WEATHER_PARAM_EXPLAINERS.get(key)
        if explainer:
            st.markdown(f"<div style='margin-bottom:2em'>{explainer}</div>", unsafe_allow_html=True)

    if "weather_type" in df.columns:
        st.subheader("🌤️ Weather Type Overview")
        types = df["weather_type"].value_counts().head(5).reset_index()
        types.columns = ["Weather", "Count"]
        types["Weather"] = types["Weather"].map(WEATHER_TYPE_DISPLAY).fillna(types["Weather"])
        st.dataframe(types)

    st.download_button("📄 Download Merged CSV", df.to_csv(index=False), file_name="merged_data.csv")
else:
    st.warning("Please upload both solar and weather files to begin analysis.")

st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Solar Insights</small></center>", unsafe_allow_html=True)
