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
st.sidebar.header("\ud83d\udca5 System Monitor")
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
with st.sidebar.expander("\ud83d\udd10 Admin Mode"):
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
                    if st.button("\ud83d\uddd1\ufe0f", key=f"del_{filetype}_{f}"):
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

st.sidebar.header("\ud83d\udcc1 File Management")
with st.sidebar.expander("Solar Data", expanded=True):
    upload_section("Solar CSV(s)", SOLAR_DIR, "solar")
with st.sidebar.expander("Weather Data", expanded=True):
    upload_section("Weather CSV(s)", WEATHER_DIR, "weather")

# ---- Placeholder for analysis section ----
st.markdown("---")
st.markdown("## \ud83d\udd2c Analysis and Visuals Will Be Loaded Here Once Data Is Uploaded")

# You can append your previous solar+weather charting logic below this line
# using `solar_files = file_disk_action(SOLAR_DIR, "load")` etc.
# That logic is already integrated — just trimmed here for clarity.

st.markdown("<center><small>Built by Hussein Akim — Solar Insights</small></center>", unsafe_allow_html=True)
