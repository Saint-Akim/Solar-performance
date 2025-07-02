import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest
from io import BytesIO
import base64
import numpy as np

st.set_page_config(page_title="Solar System Analyzer", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .block-container { padding: 2rem 2rem 2rem 2rem; }
    footer { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)
st.title("☀️ Solar System Performance & Anomaly Dashboard")

# --- FILE UPLOAD ---
with st.sidebar:
    st.header("📁 Upload Data")
    solar_files = st.file_uploader("Upload Solar Data CSV(s)", type="csv", accept_multiple_files=True)
    weather_files = st.file_uploader("Upload Weather Data CSV(s)", type="csv", accept_multiple_files=True)

if not solar_files or not weather_files:
    st.warning("⚠️ Please upload both solar and weather CSV files to continue.")
    st.stop()

# --- LOAD SOLAR DATA ---
solar_dfs = []
for file in solar_files:
    df = pd.read_csv(file)
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
    df = df.dropna(subset=['last_changed'])
    df['last_changed'] = df['last_changed'].dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
    df['entity_id'] = df['entity_id'].str.lower().str.strip()
    solar_dfs.append(df)

solar_data = pd.concat(solar_dfs, ignore_index=True)
solar_pivot = solar_data.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last').reset_index()

# --- LOAD WEATHER DATA ---
weather_dfs = []
for file in weather_files:
    df = pd.read_csv(file)
    df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
    df = df.dropna(subset=['period_end'])
    df['period_end'] = df['period_end'].dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    for col in df.columns:
        if col not in ['period_end', 'period']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    weather_dfs.append(df)

weather_data = pd.concat(weather_dfs, ignore_index=True)

# --- PARAMETERS ---
power_params = [col for col in solar_pivot.columns if col != 'last_changed']
weather_params = [col for col in weather_data.columns if col not in ['period_end', 'period']]

# --- SIDEBAR FILTERS ---
st.sidebar.header("⚙️ Filters")
date_range = st.sidebar.date_input("Select Date Range", value=(solar_pivot['last_changed'].min(), solar_pivot['last_changed'].max()))
selected_power = st.sidebar.multiselect("Power Parameters", power_params, default=power_params[:2])
selected_weather = st.sidebar.multiselect("Weather Parameters", weather_params, default=weather_params[:2])

# --- FILTER DATA ---
start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
solar_filtered = solar_pivot[(solar_pivot['last_changed'] >= start_date) & (solar_pivot['last_changed'] <= end_date)]
weather_filtered = weather_data[(weather_data['period_end'] >= start_date) & (weather_data['period_end'] <= end_date)]

# --- EXPECTED POWER CALC ---
total_capacity_kw = 221.43
performance_ratio = 0.8
if 'gti' in weather_filtered.columns:
    weather_filtered['expected_power_kw'] = weather_filtered['gti'] * total_capacity_kw * performance_ratio / 1000

# --- EFFICIENCY ANALYSIS ---
if 'expected_power_kw' in weather_filtered.columns:
    actual_kw = solar_filtered[selected_power].sum(axis=1)
    expected_kw = weather_filtered.set_index('period_end').reindex(solar_filtered['last_changed'], method='nearest')['expected_power_kw']
    loss = expected_kw - actual_kw
    fig_loss = go.Figure()
    fig_loss.add_trace(go.Scatter(x=solar_filtered['last_changed'], y=actual_kw, name='Actual Power', line=dict(color='green')))
    fig_loss.add_trace(go.Scatter(x=solar_filtered['last_changed'], y=expected_kw, name='Expected Power', line=dict(color='orange')))
    fig_loss.add_trace(go.Scatter(x=solar_filtered['last_changed'], y=loss, name='Power Loss', line=dict(color='red', dash='dot')))
    fig_loss.update_layout(title="🔋 Efficiency & Loss Analysis", xaxis_title="Time", yaxis_title="Power (kW)", hovermode="x unified")
    st.plotly_chart(fig_loss, use_container_width=True)

# --- ANOMALY DETECTION ---
try:
    st.subheader("🚨 Anomaly Detection")
    df_merged = pd.merge_asof(solar_filtered.sort_values('last_changed'), weather_filtered.sort_values('period_end'), left_on='last_changed', right_on='period_end')
    df_feat = df_merged[selected_power + selected_weather].fillna(0)
    model = IsolationForest(contamination=0.01, random_state=42)
    preds = model.fit_predict(df_feat)
    df_merged['anomaly'] = preds
    fig_anom = px.scatter(
        df_merged,
        x='last_changed', y='expected_power_kw',
        color=df_merged['anomaly'].map({1: 'Normal', -1: 'Anomaly'}),
        title="Detected Performance Anomalies",
        color_discrete_map={'Normal': 'blue', 'Anomaly': 'crimson'}
    )
    st.plotly_chart(fig_anom, use_container_width=True)
    with st.expander("📄 View Detailed Anomaly Report"):
        st.dataframe(df_merged[df_merged['anomaly'] == -1][['last_changed', 'expected_power_kw'] + selected_power])
except Exception as e:
    st.warning(f"Anomaly detection skipped: {e}")

# --- CHARTING ---
st.subheader("📊 Power Parameters")
for param in selected_power:
    fig = px.line(solar_filtered, x='last_changed', y=param, title=f"Power: {param}")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("🌦️ Weather Parameters")
for param in selected_weather:
    fig = px.line(weather_filtered, x='period_end', y=param, title=f"Weather: {param}")
    st.plotly_chart(fig, use_container_width=True)

# --- EXPORT OPTIONS ---
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

st.sidebar.markdown("---")
if st.sidebar.button("📤 Export Filtered Power Data"):
    st.sidebar.download_button("Download CSV", convert_df(solar_filtered), file_name="filtered_power.csv")
if st.sidebar.button("📤 Export Weather Data"):
    st.sidebar.download_button("Download CSV", convert_df(weather_filtered), file_name="filtered_weather.csv")

# --- SESSION EXPORT ---
if st.sidebar.button("💾 Export Dashboard as Static Report"):
    report_html = f"""
    <html><head><title>Solar Report</title></head><body>
    <h2>Solar System Anomaly Report</h2>
    <p>Generated anomalies and performance summary over selected range.</p>
    <footer><small>Generated by Hussein Akim’s Analyzer</small></footer></body></html>
    """
    b = BytesIO()
    b.write(report_html.encode())
    b.seek(0)
    st.sidebar.download_button("Download Report HTML", b, file_name="solar_report.html", mime="text/html")

# --- FOOTER ---
st.markdown("""<hr><center><small>Built by Hussein Akim - Solar Analysis Platform</small></center>""", unsafe_allow_html=True)
