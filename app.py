import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import platform
import psutil

# ---- Configuration Constants ----
UPLOAD_ROOT = "Uploads"
SOLAR_DIR = os.path.join(UPLOAD_ROOT, "solar")
WEATHER_DIR = os.path.join(UPLOAD_ROOT, "weather")
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'
MAX_FILE_SIZE_MB = 10
ADMIN_PASSWORD = "admin123"

# ---- Ensure Upload Directories ----
os.makedirs(SOLAR_DIR, exist_ok=True)
os.makedirs(WEATHER_DIR, exist_ok=True)

# ---- Sidebar System Monitor ----
st.sidebar.header("🖥️ System Monitor")
cpu = psutil.cpu_percent(interval=1)
ram = psutil.virtual_memory()
disk = psutil.disk_usage('/')
st.sidebar.markdown(f"**CPU Usage:** {cpu}%")
st.sidebar.markdown(f"**RAM Usage:** {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)")
st.sidebar.markdown(f"**Disk Usage:** {disk.percent}%")
st.sidebar.markdown(f"**OS:** {platform.system()} {platform.release()}")

# ---- Admin Mode Toggle ----
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

with st.sidebar.expander("🔐 Admin Mode"):
    pwd = st.text_input("Enter password to toggle Admin Mode", type="password")
    if st.button("Toggle Admin Mode"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_mode = not st.session_state.admin_mode
            st.success(f"Admin mode {'enabled' if st.session_state.admin_mode else 'disabled'}.")
        else:
            st.error("Incorrect password")

# ---- Upload and File Viewer Section ----
def file_disk_action(folder, action, filename=None):
    if action == "load":
        return [os.path.join(folder, fname) for fname in sorted(os.listdir(folder)) if fname.endswith(".csv")]
    elif action == "delete_all":
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))
    elif action == "delete_one" and filename:
        os.remove(os.path.join(folder, filename))

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
                    st.download_button("⬇️", data=d, file_name=os.path.basename(f), key=f"dl_{f}")
            if st.session_state.admin_mode:
                with col3:
                    if st.button("🗑️", key=f"del_{filetype}_{f}"):
                        file_disk_action(folder, "delete_one", os.path.basename(f))
                        st.rerun()
        if st.session_state.admin_mode and st.button(f"Clear All {label}", key=f"clear_{filetype}"):
            file_disk_action(folder, "delete_all")
            st.rerun()

    if st.session_state.admin_mode:
        uploaded_files = st.file_uploader(f"Add/Replace {label}", type="csv", accept_multiple_files=True, key=f"uploader_{filetype}")
        if uploaded_files:
            save_files_to_disk(uploaded_files, folder)
            st.success("Files uploaded successfully.")
            st.rerun()

# ---- Main Layout ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("☀️ Solar Performance & Weather Analyzer")

st.sidebar.header("📁 File Management")
with st.sidebar.expander("Solar Data", expanded=True):
    upload_section("Solar CSV(s)", SOLAR_DIR, "solar")
with st.sidebar.expander("Weather Data", expanded=True):
    upload_section("Weather CSV(s)", WEATHER_DIR, "weather")

st.markdown("<center><small>Built by Hussein Akim — Solar Insights</small></center>", unsafe_allow_html=True)
