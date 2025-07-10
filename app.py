import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
from io import StringIO

# ---- Config ----
TOTAL_CAPACITY_KW = 221.43
FRONIUS_KW = 60
GOODWE_KW = 110
TZ = "Africa/Johannesburg"
DEFAULT_GTI_FACTOR = 1.0
DEFAULT_PR = 0.8

# ---- GitHub URLs ----
GITHUB_SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]

GITHUB_WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"

# ---- UI Setup ----
st.set_page_config(page_title="Unified Solar Dashboard", layout="wide")
st.title("\U0001F31E GoodWe and Fronius Performance vs Weather Data")

# ---- Sidebar: Controls ----
st.sidebar.header("\U0001F4C5 Controls")
site = st.sidebar.selectbox("Site", ["Southern Paarl"])

with st.sidebar.form("adjust_factors"):
    gti_factor = st.slider("GTI Multiplier", 0.5, 1.5, DEFAULT_GTI_FACTOR, 0.01)
    pr = st.slider("Performance Ratio (PR)", 0.5, 1.0, DEFAULT_PR, 0.01)
    show_weather_explain = st.checkbox("Show Weather Impact Explanations", value=True)
    submitted = st.form_submit_button("Apply")

# ---- Helper: Load CSVs from GitHub ----
def load_csv_from_github(urls):
    dfs = []
    for url in urls:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))
                dfs.append(df)
        except Exception as e:
            st.error(f"Failed to load {url}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# ---- Load and clean solar data ----
solar_df_raw = load_csv_from_github(GITHUB_SOLAR_URLS)
weather_df_raw = load_csv_from_github([GITHUB_WEATHER_URL])

if solar_df_raw.empty or weather_df_raw.empty:
    st.error("Solar or weather data could not be loaded.")
    st.stop()

solar_df_raw['last_changed'] = pd.to_datetime(solar_df_raw['last_changed'], utc=True, errors='coerce')
solar_df_raw = solar_df_raw.dropna(subset=['last_changed'])
solar_df_raw['last_changed'] = solar_df_raw['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
solar_df_raw['state'] = pd.to_numeric(solar_df_raw['state'], errors='coerce').abs()
solar_df_raw['entity_id'] = solar_df_raw['entity_id'].str.strip().str.lower()

pivoted = solar_df_raw.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()

weather_df_raw['period_end'] = pd.to_datetime(weather_df_raw['period_end'], utc=True, errors='coerce')
weather_df_raw = weather_df_raw.dropna(subset=['period_end'])
weather_df_raw['period_end'] = weather_df_raw['period_end'].dt.tz_convert(TZ).dt.tz_localize(None)
for col in weather_df_raw.columns:
    if col not in ['period_end', 'period']:
        weather_df_raw[col] = pd.to_numeric(weather_df_raw[col], errors='coerce').fillna(0)

merged_df = pd.merge_asof(
    pivoted.sort_values("last_changed"),
    weather_df_raw.sort_values("period_end"),
    left_on="last_changed", right_on="period_end"
)

merged_df['sensor.fronius_grid_power'] = merged_df.get('sensor.fronius_grid_power', 0) / 1000
merged_df['sensor.goodwe_grid_power'] = merged_df.get('sensor.goodwe_grid_power', 0) / 1000
merged_df['actual_power_kw'] = merged_df['sensor.fronius_grid_power'].fillna(0) + merged_df['sensor.goodwe_grid_power'].fillna(0)

if submitted:
    merged_df['expected_power_kw'] = merged_df.get('gti', 0) * TOTAL_CAPACITY_KW * pr * gti_factor / 1000
else:
    merged_df['expected_power_kw'] = merged_df.get('gti', 0) * TOTAL_CAPACITY_KW * DEFAULT_PR * DEFAULT_GTI_FACTOR / 1000

st.sidebar.header("\U0001F4C6 Date Filter")
min_date = merged_df['last_changed'].min()
max_date = merged_df['last_changed'].max()
start, end = st.sidebar.date_input("Date Range", [min_date, max_date])
merged_df = merged_df[(merged_df['last_changed'] >= pd.to_datetime(start)) & (merged_df['last_changed'] <= pd.to_datetime(end))]

# ---- Analysis ----
st.subheader("\U0001F4CA Actual vs Expected Power")
fig = go.Figure()
fig.add_trace(go.Scatter(x=merged_df['last_changed'], y=merged_df['actual_power_kw'], name="Actual Power (kW)", line=dict(color="green")))
fig.add_trace(go.Scatter(x=merged_df['last_changed'], y=merged_df['expected_power_kw'], name="Expected Power (kW)", line=dict(color="orange")))
fig.update_layout(xaxis_title="Time", yaxis_title="Power (kW)", hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# ---- Shortfall ----
max_actual = merged_df['actual_power_kw'].max()
st.metric("\U0001F4A1 Max Actual Power (kW)", f"{max_actual:.2f} kW")
shortfall = TOTAL_CAPACITY_KW - max_actual
st.metric("\u274C Shortfall from Capacity", f"{shortfall:.2f} kW")

# ---- Per-inverter comparison ----
st.subheader("\u26A1 Inverter Performance")
fronius_max = merged_df['sensor.fronius_grid_power'].max()
goodwe_max = merged_df['sensor.goodwe_grid_power'].max()
st.metric("Fronius Max Output", f"{fronius_max:.2f} kW / {FRONIUS_KW} kW")
st.metric("GoodWe Max Output", f"{goodwe_max:.2f} kW / {GOODWE_KW} kW")

# ---- Weather Parameter Explorer ----
st.subheader("\U0001F325\uFE0F Weather Parameters vs Power")
weather_cols = [c for c in weather_df_raw.columns if c not in ['period', 'period_end'] and pd.api.types.is_numeric_dtype(weather_df_raw[c])]
selected_weather = st.multiselect("Select Weather Parameters", weather_cols, default=['gti', 'ghi', 'cloud_opacity'])

col1, col2 = st.columns(2)
for i, param in enumerate(selected_weather):
    with col1 if i % 2 == 0 else col2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=merged_df['last_changed'], y=merged_df[param], name=param, line=dict(color="#1e90ff")))
        fig.update_layout(title=param, xaxis_title="Time", yaxis_title=param, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

if show_weather_explain:
    st.subheader("\U0001F4D6 Weather Parameter Impact Explanation")
    st.markdown("""
    - **GTI (Global Tilted Irradiance):** Measures sunlight on tilted panel surface — higher GTI = more energy.
    - **GHI (Global Horizontal Irradiance):** Sunlight on flat surface, used for expected yield models.
    - **Cloud Opacity:** High values reduce light intensity and panel output.
    - **Humidity:** Excessive moisture can reduce panel efficiency.
    - **Air Temperature:** High temps can reduce voltage and overall efficiency.
    - **Wind Speed:** Moderate wind cools panels, improving efficiency slightly.
    """)

st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Unified Solar Insights</small></center>", unsafe_allow_html=True)
