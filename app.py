# solar_streamlit_app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from sklearn.ensemble import IsolationForest
import base64

st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("☀️ Solar System Dashboard: Insights & Diagnostics")

# --- FILE UPLOAD ---
st.sidebar.header("Upload Data")
solar_files = st.sidebar.file_uploader("Upload Solar Data CSV(s)", type="csv", accept_multiple_files=True)
weather_files = st.sidebar.file_uploader("Upload Weather Data CSV(s)", type="csv", accept_multiple_files=True)

if not solar_files or not weather_files:
    st.warning("Please upload both solar and weather CSV files to proceed.")
    st.stop()

# --- LOAD SOLAR DATA ---
all_solar_dfs = []
for file in solar_files:
    df = pd.read_csv(file)
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
    df = df.dropna(subset=['last_changed'])
    df['last_changed'] = df['last_changed'].dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    df['entity_id'] = df['entity_id'].str.strip().str.lower()
    df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
    df = df.dropna(subset=['state'])
    df = df.drop_duplicates(subset=['entity_id', 'last_changed'], keep='last')
    all_solar_dfs.append(df)

solar_df_raw = pd.concat(all_solar_dfs, ignore_index=True)
solar_df = solar_df_raw.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last').reset_index()

# --- CATEGORIZE SOLAR PARAMETERS ---
categories = {
    'Voltage': [c for c in solar_df.columns if 'voltage' in c],
    'Current': [c for c in solar_df.columns if 'current' in c and 'power' not in c],
    'Reactive Power': [c for c in solar_df.columns if 'reactive_power' in c],
    'Apparent Power': [c for c in solar_df.columns if 'apparent_power' in c],
    'Power': [c for c in solar_df.columns if 'power' in c and 'apparent' not in c and 'reactive' not in c],
    'Frequency': [c for c in solar_df.columns if 'frequency' in c],
    'Status': [c for c in solar_df.columns if 'status' in c or 'init' in c]
}

for col in categories['Power']:
    solar_df[col] = pd.to_numeric(solar_df[col], errors='coerce').fillna(0).abs() / 1000

fronius_cols = [col for col in solar_df.columns if 'fronius_power_l' in col]
goodwe_cols = [col for col in solar_df.columns if 'goodwe_power_l' in col]
solar_df['fronius_total_power_kw'] = solar_df[fronius_cols].sum(axis=1)
solar_df['goodwe_total_power_kw'] = solar_df[goodwe_cols].sum(axis=1)
solar_df['combined_total_power_kw'] = solar_df['fronius_total_power_kw'] + solar_df['goodwe_total_power_kw']

# --- LOAD WEATHER DATA ---
all_weather_dfs = []
for file in weather_files:
    df = pd.read_csv(file)
    df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
    df = df.dropna(subset=['period_end'])
    df['period_end'] = df['period_end'].dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    for col in df.columns:
        if col not in ['period_end', 'period']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    all_weather_dfs.append(df)

weather_df = pd.concat(all_weather_dfs, ignore_index=True)
total_capacity_kw = 221.43
performance_ratio = 0.8
if 'gti' in weather_df.columns:
    weather_df['expected_power_kw'] = weather_df['gti'] * total_capacity_kw * performance_ratio / 1000

# --- FILTERS ---
st.sidebar.header("Filters")
date_range = st.sidebar.date_input("Date Range", [solar_df['last_changed'].min(), solar_df['last_changed'].max()])
selected_category = st.sidebar.selectbox("Select Category", list(categories.keys()))

start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
solar_df = solar_df[(solar_df['last_changed'] >= start) & (solar_df['last_changed'] <= end)]
weather_df = weather_df[(weather_df['period_end'] >= start) & (weather_df['period_end'] <= end)]

# --- PLOTTING FUNCTION ---
def plot_chart(df, x_col, y_col, label, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], name=label, line=dict(color=color)))
    fig.update_layout(title=label, xaxis_title="Time", yaxis_title=label, hovermode="x unified")
    return fig

# --- DISPLAY CHARTS ---
st.subheader(f"📊 Category: {selected_category}")
for col in categories[selected_category]:
    fig = plot_chart(solar_df, 'last_changed', col, col, '#1f77b4')
    st.plotly_chart(fig, use_container_width=True)

# --- WEATHER PLOTS ---
st.subheader("🌤️ Weather Parameters")
weather_plot_cols = ['ghi', 'cloud_opacity', 'precipitation_rate', 'expected_power_kw']
for col in [c for c in weather_plot_cols if c in weather_df.columns]:
    fig = plot_chart(weather_df, 'period_end', col, col, '#ff7f0e')
    st.plotly_chart(fig, use_container_width=True)

# --- DEBUG SUMMARY ---
st.sidebar.markdown("---")
st.sidebar.markdown("### Debug Summary")
st.sidebar.text(f"Solar rows: {len(solar_df)}")
st.sidebar.text(f"Weather rows: {len(weather_df)}")
st.sidebar.text(f"Total power cols: {len(categories['Power'])}")

# --- EXPORT SECTION ---
def to_csv_download(df, filename):
    csv = df.to_csv(index=False).encode()
    st.sidebar.download_button(f"⬇️ Download {filename}", csv, filename=filename, mime='text/csv')

to_csv_download(solar_df, "filtered_solar.csv")
to_csv_download(weather_df, "filtered_weather.csv")

# --- FOOTER ---
st.markdown("""
<hr style="margin-top: 50px;">
<center><small>Generated by Hussein Akim's Analyzer · Built with Streamlit</small></center>
""", unsafe_allow_html=True)
