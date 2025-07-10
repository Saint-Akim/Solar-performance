# ✅ FULL VERSION — Unified Solar Dashboard by Hussein Akim (Pro Edition)

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
INVERTER_KW = FRONIUS_KW + GOODWE_KW
TZ = "Africa/Johannesburg"

# ---- GitHub URLs ----
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"

# ---- Friendly Names ----
FRIENDLY = {
    "sensor.fronius_grid_power": "Fronius Grid Power (kW)",
    "sensor.goodwe_grid_power": "GoodWe Grid Power (kW)",
    "actual_power_kw": "Actual Power (kW)",
    "expected_total_kw": "Expected Power (221.43 kW)",
    "expected_inverter_kw": "Expected Inverter Power (170 kW)",
    "expected_goodwe_kw": "Expected GoodWe Power (110 kW)",
    "expected_fronius_kw": "Expected Fronius Power (60 kW)",
    "gti": "GTI (W/m²)",
    "ghi": "GHI (W/m²)",
    "air_temp": "Air Temperature (°C)",
    "cloud_opacity": "Cloud Opacity (%)",
    "humidity": "Humidity (%)",
    "wind_speed": "Wind Speed (m/s)",
    "co2_saved": "CO₂ Saved (kg)",
    "pr": "Performance Ratio",
}

EXPLAINERS = {
    "gti": "📈 GTI: Sunlight on tilted panels. Higher GTI = more solar energy.",
    "ghi": "📉 GHI: Total sunlight on flat surface.",
    "air_temp": "🌡️ Higher temperature can reduce panel efficiency.",
    "cloud_opacity": "☁️ More cloud = less irradiance = lower output.",
    "humidity": "💧 High humidity = potential cloudiness and reduced solar performance.",
    "wind_speed": "💨 Wind cools the panels = slightly higher efficiency.",
    "expected_total_kw": "🔋 Based on full 221.43 kW panel capacity.",
    "expected_inverter_kw": "⚡ Based on inverter limit: 170 kW.",
    "expected_goodwe_kw": "🔌 GoodWe (110 kW) expected output.",
    "expected_fronius_kw": "🔌 Fronius (60 kW) expected output."
}

# ---- Load GitHub CSVs ----
def load_csvs(urls):
    dfs = []
    for url in urls:
        r = requests.get(url)
        if r.status_code == 200:
            dfs.append(pd.read_csv(StringIO(r.text)))
    return pd.concat(dfs, ignore_index=True)

solar_raw = load_csvs(SOLAR_URLS)
weather_raw = load_csvs([WEATHER_URL])

# ---- Clean Data ----
solar_raw['last_changed'] = pd.to_datetime(solar_raw['last_changed'], utc=True, errors='coerce')
solar_raw.dropna(subset=['last_changed'], inplace=True)
solar_raw['last_changed'] = solar_raw['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
solar_raw['state'] = pd.to_numeric(solar_raw['state'], errors='coerce').abs()
solar_raw['entity_id'] = solar_raw['entity_id'].str.lower().str.strip()
pivoted = solar_raw.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()

weather_raw['period_end'] = pd.to_datetime(weather_raw['period_end'], utc=True, errors='coerce')
weather_raw.dropna(subset=['period_end'], inplace=True)
weather_raw['period_end'] = weather_raw['period_end'].dt.tz_convert(TZ).dt.tz_localize(None)
for col in weather_raw.columns:
    if col not in ['period_end', 'period']:
        weather_raw[col] = pd.to_numeric(weather_raw[col], errors='coerce').fillna(0)

merged = pd.merge_asof(pivoted.sort_values("last_changed"), weather_raw.sort_values("period_end"), left_on="last_changed", right_on="period_end")
merged['sensor.fronius_grid_power'] /= 1000
merged['sensor.goodwe_grid_power'] /= 1000
merged['actual_power_kw'] = merged['sensor.fronius_grid_power'].fillna(0) + merged['sensor.goodwe_grid_power'].fillna(0)

# ---- UI ----
st.set_page_config(layout="wide")
st.title("☀️ Unified Solar Dashboard")

# ---- Sidebar ----
st.sidebar.header("🔧 Controls")
with st.sidebar.form("factors"):
    gti = st.slider("GTI Multiplier", 0.5, 1.5, 1.0, 0.01)
    pr_goodwe = st.slider("GoodWe PR", 0.5, 1.0, DEFAULT_PR, 0.01)
    pr_fronius = st.slider("Fronius PR", 0.5, 1.0, DEFAULT_PR, 0.01)
    apply = st.form_submit_button("Apply")

# ---- Expected Power ----
if apply:
    merged['expected_total_kw'] = merged['gti'] * gti * TOTAL_CAPACITY_KW * DEFAULT_PR / 1000
    merged['expected_inverter_kw'] = merged['gti'] * gti * INVERTER_KW * DEFAULT_PR / 1000
    merged['expected_goodwe_kw'] = merged['gti'] * gti * GOODWE_KW * pr_goodwe / 1000
    merged['expected_fronius_kw'] = merged['gti'] * gti * FRONIUS_KW * pr_fronius / 1000
else:
    merged['expected_total_kw'] = merged['gti'] * TOTAL_CAPACITY_KW * DEFAULT_PR / 1000
    merged['expected_inverter_kw'] = merged['gti'] * INVERTER_KW * DEFAULT_PR / 1000
    merged['expected_goodwe_kw'] = merged['gti'] * GOODWE_KW * DEFAULT_PR / 1000
    merged['expected_fronius_kw'] = merged['gti'] * FRONIUS_KW * DEFAULT_PR / 1000

# ---- Filter Date ----
d1, d2 = st.sidebar.date_input("📅 Date Range", [merged['last_changed'].min(), merged['last_changed'].max()])
filtered = merged[(merged['last_changed'] >= pd.to_datetime(d1)) & (merged['last_changed'] <= pd.to_datetime(d2))]

# ---- Chart Utility ----
def chart(df, x, y, title, color):
    label = FRIENDLY.get(y, y)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name=label, line=dict(color=color)))
    fig.update_layout(title=title, xaxis=dict(rangeslider=dict(visible=True), type='date'), yaxis_title=label, hovermode='x unified')
    return fig

# ---- Actual vs Expected ----
st.subheader("🌞 Actual vs Expected Power")
fig = chart(filtered, 'last_changed', 'actual_power_kw', "Actual Power (kW)", "green")
fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_total_kw'], name=FRIENDLY['expected_total_kw'], line=dict(color="orange")))
fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_inverter_kw'], name=FRIENDLY['expected_inverter_kw'], line=dict(color="blue")))
st.plotly_chart(fig, use_container_width=True)

# ---- Metrics ----
st.subheader("📈 Performance Summary")
st.metric("Max Actual (kW)", f"{filtered['actual_power_kw'].max():.2f}")
st.metric("Shortfall vs 221.43 kW", f"{TOTAL_CAPACITY_KW - filtered['actual_power_kw'].max():.2f} kW")
st.metric("GoodWe Max", f"{filtered['sensor.goodwe_grid_power'].max():.2f} / {GOODWE_KW} kW")
st.metric("Fronius Max", f"{filtered['sensor.fronius_grid_power'].max():.2f} / {FRONIUS_KW} kW")

# ---- Dual Column Explorer ----
st.subheader("📊 Weather and Solar Parameter Explorer")
s_cols = ['sensor.fronius_grid_power', 'sensor.goodwe_grid_power', 'expected_total_kw', 'expected_goodwe_kw', 'expected_fronius_kw']
w_cols = [c for c in weather_raw.columns if c not in ['period_end', 'period'] and pd.api.types.is_numeric_dtype(weather_raw[c])]

l, r = st.columns(2)
with l:
    ssel = st.multiselect("Select Solar Parameters", s_cols, default=['sensor.fronius_grid_power'])
    for s in ssel:
        st.plotly_chart(chart(filtered, 'last_changed', s, FRIENDLY.get(s, s), '#00cc99'), use_container_width=True)
with r:
    wsel = st.multiselect("Select Weather Parameters", w_cols, default=['gti', 'ghi'])
    for w in wsel:
        st.plotly_chart(chart(filtered, 'last_changed', w, FRIENDLY.get(w, w), '#1e90ff'), use_container_width=True)
        if w in EXPLAINERS:
            st.markdown(EXPLAINERS[w])

st.download_button("📥 Download CSV", filtered.to_csv(index=False), file_name="solar_dashboard_data.csv")
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Unified Solar Insights</small></center>", unsafe_allow_html=True)
