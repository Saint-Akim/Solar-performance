# streamlit_ai_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest
from huggingface_hub import InferenceClient
import openai, cohere, replicate

# --- CONFIG ---
st.set_page_config(page_title="Solar AI Dashboard", layout="wide")
st.title("☀️ AI-Powered Solar Performance & Weather Analyzer")

# --- API KEY ENTRY ---
st.sidebar.header("🔐 API Keys (Optional)")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
cohere_key = st.sidebar.text_input("Cohere API Key", type="password")
hug_key = st.sidebar.text_input("Hugging Face API Key", type="password")
replicate_key = st.sidebar.text_input("Replicate API Key", type="password")

if openai_key: openai.api_key = openai_key
if cohere_key: co = cohere.Client(cohere_key)
if hug_key: hf = InferenceClient(token=hug_key)
if replicate_key: rep = replicate.Client(api_token=replicate_key)

# --- DATA UPLOAD ---
st.sidebar.header("📁 Upload Data")
solar_files = st.sidebar.file_uploader("Upload Solar CSV(s)", type="csv", accept_multiple_files=True)
weather_files = st.sidebar.file_uploader("Upload Weather CSV(s)", type="csv", accept_multiple_files=True)
if not solar_files or not weather_files:
    st.warning("Upload solar and weather data to begin analysis.")
    st.stop()

# --- LOAD SOLAR ---
solar_dfs = []
for f in solar_files:
    df = pd.read_csv(f)
    if 'last_changed' not in df.columns:
        st.error("Missing 'last_changed' in solar data")
        st.stop()
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
    df = df.dropna(subset=['last_changed'])
    df['last_changed'] = df['last_changed'].dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
    df['entity_id'] = df['entity_id'].str.lower().str.strip()
    solar_dfs.append(df)
solar_data = pd.concat(solar_dfs, ignore_index=True)
solar_pivot = solar_data.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last').reset_index()

# --- LOAD WEATHER ---
weather_dfs = []
for f in weather_files:
    df = pd.read_csv(f)
    df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
    df = df.dropna(subset=['period_end'])
    df['period_end'] = df['period_end'].dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    for col in df.columns:
        if col not in ['period_end', 'period']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    weather_dfs.append(df)
weather_data = pd.concat(weather_dfs, ignore_index=True)

# --- EXPECTED POWER ---
total_capacity_kw = 221.43
performance_ratio = 0.8
if 'gti' in weather_data.columns:
    weather_data['expected_power_kw'] = weather_data['gti'] * total_capacity_kw * performance_ratio / 1000

# --- FILTER ---
st.sidebar.header("📅 Filter")
start, end = st.sidebar.date_input("Select Date Range", [solar_pivot['last_changed'].min(), solar_pivot['last_changed'].max()])
sdate, edate = pd.to_datetime(start), pd.to_datetime(end)
solar_filtered = solar_pivot[(solar_pivot['last_changed'] >= sdate) & (solar_pivot['last_changed'] <= edate)]
weather_filtered = weather_data[(weather_data['period_end'] >= sdate) & (weather_data['period_end'] <= edate)]

# --- PARAMETER SELECTION ---
power_params = [c for c in solar_pivot.columns if c != 'last_changed']
weather_params = [c for c in weather_data.columns if c not in ['period_end', 'period']]
selected_power = st.sidebar.multiselect("⚡ Power Parameters", power_params, default=power_params[:3])
selected_weather = st.sidebar.multiselect("🌦️ Weather Parameters", weather_params, default=weather_params[:3])

# --- CHARTING ---
st.subheader("📊 Power Charts")
for param in selected_power:
    st.plotly_chart(px.line(solar_filtered, x='last_changed', y=param, title=param), use_container_width=True)
st.subheader("🌤️ Weather Charts")
for param in selected_weather:
    st.plotly_chart(px.line(weather_filtered, x='period_end', y=param, title=param), use_container_width=True)

# --- AI ASSISTANT ---
st.subheader("🤖 AI Data Analysis")
question = st.text_input("Ask a question about your solar or weather data")
if question:
    if openai_key:
        with st.spinner("Thinking..."):
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Using the uploaded solar power and weather data, answer: {question}"}]
            )
            st.success(response['choices'][0]['message']['content'])
    else:
        st.info("Enter OpenAI key for smart responses")

# --- FOOTER ---
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — AI-enhanced Solar Insights</small></center>", unsafe_allow_html=True)
