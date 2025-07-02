import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from huggingface_hub import InferenceClient
import cohere, replicate

# --- CONFIG ---
st.set_page_config(page_title="Solar AI Dashboard", layout="wide")
st.title("☀️ AI-Powered Solar Performance & Weather Analyzer")

# --- API KEY ENTRY ---
st.sidebar.header("🔐 API Keys (Optional)")
cohere_key = st.sidebar.text_input("Cohere API Key", type="password")
hug_key = st.sidebar.text_input("Hugging Face API Key", type="password")
replicate_key = st.sidebar.text_input("Replicate API Key", type="password")

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

# --- PLOTLY CHART FUNCTION ---
def plot_with_slider(df, x_col, y_col, chart_type, title):
    if chart_type == "Line":
        mode, fill = "lines", None
    elif chart_type == "Bar":
        mode, fill = None, None
    elif chart_type == "Scatter":
        mode, fill = "markers", None
    elif chart_type == "Area":
        mode, fill = "lines", "tozeroy"
    else:
        mode, fill = "lines", None

    fig = go.Figure()
    if chart_type == "Bar":
        fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], name=y_col))
    else:
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[y_col], 
            mode=mode, 
            fill=fill,
            name=y_col
        ))
    fig.update_layout(
        title=title,
        xaxis=dict(
            title=x_col,
            rangeslider=dict(visible=True),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1d", step="day", stepmode="backward"),
                    dict(count=7, label="1w", step="day", stepmode="backward"),
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            type="date"
        ),
        yaxis=dict(title=y_col),
        hovermode='x unified'
    )
    return fig

# --- PARAMETER SELECTION & MULTI-TAB CHARTS ---
st.sidebar.header("📊 Chart Controls")
chart_types = ['Solar', 'Weather']
selected_chart_type = st.sidebar.selectbox("Chart type", chart_types)

if selected_chart_type == 'Solar':
    available_params = [col for col in solar_filtered.columns if col != 'last_changed']
    x_axis = 'last_changed'
    data = solar_filtered
else:
    available_params = [col for col in weather_filtered.columns if col not in ['period_end', 'period']]
    x_axis = 'period_end'
    data = weather_filtered

num_charts = st.sidebar.number_input("How many charts?", min_value=1, max_value=min(5, len(available_params)), value=1)

tab_labels = [f"Chart {i+1}" for i in range(num_charts)]
selected_parameters = []
selected_chart_types = []

for i in range(num_charts):
    param = st.sidebar.selectbox(f"Parameter for Chart {i+1}", available_params, key=f'param_{i}')
    chart_type = st.sidebar.selectbox(f"Chart Type for Chart {i+1}", ["Line", "Bar", "Scatter", "Area"], key=f"ctype_{i}")
    selected_parameters.append(param)
    selected_chart_types.append(chart_type)

tabs = st.tabs(tab_labels)
for i, tab in enumerate(tabs):
    with tab:
        fig = plot_with_slider(data, x_axis, selected_parameters[i], selected_chart_types[i], f"{selected_parameters[i]} ({selected_chart_types[i]})")
        st.plotly_chart(fig, use_container_width=True)

# --- AI ASSISTANT (NO OPENAI) ---
st.subheader("🤖 AI Data Analysis")
question = st.text_input("Ask a question about your solar or weather data")
if question:
    if cohere_key:
        with st.spinner("Thinking..."):
            response = co.chat(message=question)
            st.success(response.text)
    elif hug_key:
        st.info("HuggingFace model integration goes here.")
    elif replicate_key:
        st.info("Replicate model integration goes here.")
    else:
        st.info("Enter a model API key (Cohere, Hugging Face, or Replicate) for smart responses.")

# --- SHARING INSTRUCTIONS ---
st.markdown("---")
st.markdown(
    """
    #### 👥 **Share this dashboard**
    - Deploy your app using [Streamlit Community Cloud](https://share.streamlit.io/) or another hosting service.
    - Once deployed, copy the app URL and share it with others—they'll be able to view and interact with your charts!
    - _If running locally, others on your network can access it via your computer's IP address and the port shown in your terminal (e.g., `http://192.168.X.X:8501`)._
    """
)
st.markdown("<center><small>Built by Hussein Akim — AI-enhanced Solar Insights</small></center>", unsafe_allow_html=True)
