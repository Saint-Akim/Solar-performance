# solar_dashboard.py — Final Unified Version by Hussein Akim

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import platform
import psutil
import shutil
import zipfile
from datetime import datetime, timedelta
import pytz

# ---- Configuration Constants ----
UPLOAD_ROOT = "Uploads"
SOLAR_DIR = os.path.join(UPLOAD_ROOT, "solar")
WEATHER_DIR = os.path.join(UPLOAD_ROOT, "weather")
ARCHIVE_DIR = os.path.join(UPLOAD_ROOT, "Archive")
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'
MAX_FILE_SIZE_MB = 10
ADMIN_PASSWORD = "admin123"
ARCHIVE_DAYS = 30

os.makedirs(SOLAR_DIR, exist_ok=True)
os.makedirs(WEATHER_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# ---- Archive Old Files Automatically ----
def archive_old_files(folder):
    now = datetime.now()
    for fname in os.listdir(folder):
        fpath = os.path.join(folder, fname)
        if os.path.isfile(fpath):
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if (now - mtime).days > ARCHIVE_DAYS:
                zipname = os.path.join(ARCHIVE_DIR, f"{fname}.zip")
                with zipfile.ZipFile(zipname, 'w') as zipf:
                    zipf.write(fpath, arcname=fname)
                os.remove(fpath)
archive_old_files(SOLAR_DIR)
archive_old_files(WEATHER_DIR)

# ---- Session State Init ----
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "memory_data" not in st.session_state:
    st.session_state.memory_data = pd.DataFrame(columns=["time", "ram_percent"])

# ---- Page Config ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("\u2600\ufe0f Solar Performance & Weather Analyzer")

# ---- Sidebar: System Monitor ----
st.sidebar.header("\U0001F4A5 System Monitor")
cpu = psutil.cpu_percent(interval=1)
ram = psutil.virtual_memory()
disk = psutil.disk_usage('/')
st.sidebar.markdown(f"**CPU Usage:** {cpu}%")
st.sidebar.markdown(f"**RAM Usage:** {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)")
st.sidebar.markdown(f"**Disk Usage:** {disk.percent}%")
st.sidebar.markdown(f"**OS:** {platform.system()} {platform.release()}")

# ---- RAM Usage Chart ----
st.session_state.memory_data = pd.concat([
    st.session_state.memory_data,
    pd.DataFrame({"time": [datetime.now()], "ram_percent": [ram.percent]})
]).tail(60)
st.sidebar.line_chart(st.session_state.memory_data.set_index("time"))

# ---- Admin Toggle ----
with st.sidebar.expander("Admin Mode"):
    pwd = st.text_input("Enter password to toggle Admin Mode", type="password")
    if st.button("Toggle Admin Mode"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_mode = not st.session_state.admin_mode
            st.success(f"Admin mode {'enabled' if st.session_state.admin_mode else 'disabled'}.")
        else:
            st.error("Incorrect password")

# ---- File Management ----
def file_disk_action(folder, action, filename=None):
    if action == "load":
        return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith(".csv")]
    elif action == "delete_one" and filename:
        os.remove(os.path.join(folder, filename))
    elif action == "delete_all":
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))

def save_files_to_disk(uploaded_files, folder):
    for file in uploaded_files:
        with open(os.path.join(folder, file.name), "wb") as f:
            f.write(file.getbuffer())

def upload_section(label, folder, filetype):
    st.write(f"### {label}")
    existing_files = file_disk_action(folder, "load")
    if existing_files:
        st.success(f"{len(existing_files)} file(s) stored:")
        for f in existing_files:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.write(f"- {os.path.basename(f)}")
            with col2:
                with open(f, "rb") as d:
                    st.download_button("\u2b07\ufe0f", data=d, file_name=os.path.basename(f), key=f"dl_{f}")
            if st.session_state.admin_mode:
                with col3:
                    if st.button("\U0001F5D1\ufe0f", key=f"del_{filetype}_{f}"):
                        file_disk_action(folder, "delete_one", os.path.basename(f))
                        st.rerun()
        if st.session_state.admin_mode and st.button(f"Clear All {label}", key=f"clear_{filetype}"):
            file_disk_action(folder, "delete_all")
            st.rerun()
    if st.session_state.admin_mode:
        uploaded = st.file_uploader(f"Upload {label}", type="csv", accept_multiple_files=True, key=f"uploader_{filetype}")
        if uploaded:
            save_files_to_disk(uploaded, folder)
            st.success("Files uploaded.")
            st.rerun()

st.sidebar.header("File Management")
with st.sidebar.expander("Solar Data", expanded=True):
    upload_section("Solar CSV(s)", SOLAR_DIR, "solar")
with st.sidebar.expander("Weather Data", expanded=True):
    upload_section("Weather CSV(s)", WEATHER_DIR, "weather")

# ---- Analysis and Visuals ----
st.markdown("---")
st.markdown("## Solar & Weather Performance Analysis")

def parse_datetime(df, col):
    try:
        return pd.to_datetime(df[col]).dt.tz_localize(None).dt.tz_localize("UTC").dt.tz_convert(TZ)
    except Exception:
        return pd.to_datetime(df[col])

solar_files = file_disk_action(SOLAR_DIR, "load")
weather_files = file_disk_action(WEATHER_DIR, "load")

if solar_files and weather_files:
    df_solar = pd.concat([pd.read_csv(f) for f in solar_files])
    df_weather = pd.concat([pd.read_csv(f) for f in weather_files])

    for col in ["time", "timestamp", "datetime"]:
        if col in df_solar.columns:
            df_solar["time"] = parse_datetime(df_solar, col)
            break
    for col in ["time", "timestamp", "datetime"]:
        if col in df_weather.columns:
            df_weather["time"] = parse_datetime(df_weather, col)
            break

    df_solar = df_solar.sort_values("time")
    df_weather = df_weather.sort_values("time")

    df = pd.merge_asof(df_solar, df_weather, on="time")
    df = df.dropna(subset=["energy_kwh", "ghi", "cloud_opacity"], how="any")

    df["expected_kwh"] = (df["ghi"] * TOTAL_CAPACITY_KW * PERFORMANCE_RATIO) / 1000
    df["efficiency"] = df["energy_kwh"] / df["expected_kwh"]

    st.subheader("Energy Output vs Expected")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df["time"], y=df["energy_kwh"], name="Actual Energy (kWh)", line=dict(color="green")))
    fig1.add_trace(go.Scatter(x=df["time"], y=df["expected_kwh"], name="Expected Energy (kWh)", line=dict(color="orange")))
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Efficiency Over Time")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["time"], y=df["efficiency"], name="Efficiency", line=dict(color="blue")))
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Cloud Opacity vs Energy")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df["time"], y=df["cloud_opacity"], name="Cloud Opacity", yaxis="y2", line=dict(color="gray")))
    fig3.add_trace(go.Scatter(x=df["time"], y=df["energy_kwh"], name="Energy (kWh)", line=dict(color="purple")))
    fig3.update_layout(yaxis2=dict(overlaying="y", side="right", title="Cloud Opacity"), yaxis=dict(title="Energy (kWh)"))
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.warning("Please upload both solar and weather data files to begin analysis.")

st.markdown("<center><small>Built by Hussein Akim — Solar Insights</small></center>", unsafe_allow_html=True)
