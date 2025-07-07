# app.py — Unified Solar Dashboard by Hussein Akim

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

# ---- Configuration ----
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

# ---- Archive Files Automatically ----
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

# ---- Session State ----
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "memory_data" not in st.session_state:
    st.session_state.memory_data = pd.DataFrame(columns=["time", "ram_percent"])

# ---- Page Setup ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("☀️ Solar Performance & Weather Analyzer")

# ---- Sidebar: System Monitor ----
st.sidebar.header("
