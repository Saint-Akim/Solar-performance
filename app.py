# ✅ FINAL VERSION — GitHub Data Integration by Hussein Akim

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# ---- Config ----
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'

# ---- GitHub Raw URLs ----
SOLAR_CSV_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]

WEATHER_CSV_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"

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

# ---- Streamlit Config ----
st.set_page_config(page_title="GitHub Solar Dashboard", layout="wide")
st.title("☀️ GoodWe & Fronius Performance vs Weather (Southern Paarl)")

# ---- Load Solar Data ----
@st.cache_data(show_spinner=False)
def load_solar():
    dfs = []
    for url in SOLAR_CSV_URLS:
        df = pd.read_csv(url)
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
            df = df.dropna(subset=['last_changed'])
            df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            pivoted = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            dfs.append(pivoted)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# ---- Load Weather Data ----
@st.cache_data(show_spinner=False)
def load_weather():
    df = pd.read_csv(WEATHER_CSV_URL)
    if 'period_end' not in df.columns:
        return pd.DataFrame()
    df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
    df = df.dropna(subset=['period_end'])
    df['period_end'] = df['period_end'].dt.tz_convert(TZ).dt.tz_localize(None)
    for col in df.columns:
        if col not in ['period_end', 'period']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'gti' in df.columns:
        df['expected_power_kw'] = df['gti'] * TOTAL_CAPACITY_KW * PERFORMANCE_RATIO / 1000
    return df

# ---- Load Data ----
solar_df = load_solar()
weather_df = load_weather()

if solar_df.empty or weather_df.empty:
    st.error("❌ Data loading failed. Please check your GitHub URLs or CSV format.")
    st.stop()

merged_df = pd.merge_asof(
    solar_df.sort_values("last_changed"),
    weather_df.sort_values("period_end"),
    left_on="last_changed",
    right_on="period_end"
)

# ---- Date Filter ----
st.sidebar.header("📅 Date Filter")
min_date = merged_df['last_changed'].min()
max_date = merged_df['last_changed'].max()
start, end = st.sidebar.date_input("Select Date Range", [min_date, max_date])
filtered = merged_df[(merged_df['last_changed'] >= pd.to_datetime(start)) & (merged_df['last_changed'] <= pd.to_datetime(end))]

if filtered.empty:
    st.warning("No data available in the selected range.")
    st.stop()

# ---- Actual Power Calculation (in kW) ----
if 'sensor.fronius_grid_power' in filtered.columns and 'sensor.goodwe_grid_power' in filtered.columns:
    filtered['sensor.fronius_grid_power'] /= 1000
    filtered['sensor.goodwe_grid_power'] /= 1000
    filtered['sum_grid_power'] = filtered['sensor.fronius_grid_power'].fillna(0) + filtered['sensor.goodwe_grid_power'].fillna(0)

# ---- Plot Chart ----
def slider_chart(df, x_col, y_col, title, color):
    fig = go.Figure()
    label = FRIENDLY_NAMES.get(y_col, y_col)
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], name=label, line=dict(color=color)))
    fig.update_layout(
        title=title,
        xaxis=dict(title=x_col, rangeslider=dict(visible=True), type="date"),
        yaxis=dict(title=label),
        hovermode='x unified'
    )
    return fig

# ---- Main Chart ----
st.subheader("🌞 Actual vs Expected Power")
fig = slider_chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "green")
if 'expected_power_kw' in filtered.columns:
    fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'], name=FRIENDLY_NAMES['expected_power_kw'], line=dict(color="orange")))
st.plotly_chart(fig, use_container_width=True)

# ---- Parameter Explorer ----
st.subheader("📊 Parameter Explorer")
numeric_cols = [c for c in filtered.columns if filtered[c].dtype in [float, int] and c not in ['period', 'sum_grid_power']]
selection = st.multiselect("Select Parameters to Plot:", numeric_cols, default=['sensor.fronius_grid_power', 'sensor.goodwe_grid_power'])
for col in selection:
    fig = slider_chart(filtered, 'last_changed', col, FRIENDLY_NAMES.get(col, col), "#1e90ff")
    st.plotly_chart(fig, use_container_width=True)
    if col in WEATHER_PARAM_EXPLAINERS:
        st.markdown(WEATHER_PARAM_EXPLAINERS[col])

# ---- Weather Type Overview ----
if 'weather_type' in filtered.columns:
    st.subheader("🌤️ Weather Summary")
    counts = filtered['weather_type'].value_counts().head(5).reset_index()
    counts.columns = ['Weather', 'Count']
    st.dataframe(counts)

# ---- Export ----
st.download_button("📄 Download Merged CSV", filtered.to_csv(index=False), file_name="merged_data.csv")
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Unified Solar Insights</small></center>", unsafe_allow_html=True)
