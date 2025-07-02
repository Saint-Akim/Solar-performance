import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from huggingface_hub import InferenceClient
import cohere, replicate

st.set_page_config(page_title="Solar AI Dashboard", layout="wide")
st.title("☀️ AI-Powered Solar Performance & Weather Analyzer")

# --- Helpers for API keys (persisted) ---
def persist_text_input(key, label, type=None):
    val = st.sidebar.text_input(label, type=type, key=key)
    if val:
        st.session_state[key] = val
    return st.session_state.get(key, "")

# --- API key inputs ---
st.sidebar.header("🔐 API Keys (Optional)")
cohere_key = persist_text_input("cohere_key", "Cohere API Key", type="password")
hug_key = persist_text_input("hug_key", "Hugging Face API Key", type="password")
replicate_key = persist_text_input("replicate_key", "Replicate API Key", type="password")
if cohere_key: co = cohere.Client(cohere_key)
if hug_key: hf = InferenceClient(token=hug_key)
if replicate_key: rep = replicate.Client(api_token=replicate_key)

# --- Main file management function ---
def upload_and_manage_files(label, session_key):
    st.write(f"### {label}")

    files = st.session_state.get(session_key, [])

    # Show current files
    if files:
        st.success(f"{len(files)} file(s) stored:")
        for i, file in enumerate(files):
            st.write(f"{i+1}. {file.name}")

    # Temporary uploader for new files
    uploaded = st.file_uploader(f"Add/Update {label}", type="csv", accept_multiple_files=True, key=f"temp_{session_key}")

    # For overwrite logic
    if uploaded:
        files_dict = {f.name: (i, f) for i, f in enumerate(files)}
        overwrite_needed = False
        overwrite_names = []
        for f in uploaded:
            if f.name in files_dict:
                overwrite_needed = True
                overwrite_names.append(f.name)
        if overwrite_needed:
            st.warning(f"File(s) with the same name already exist: {', '.join(overwrite_names)}")
            overwrite = st.checkbox(f"Overwrite existing file(s): {', '.join(overwrite_names)}", key=f"chk_{session_key}")
            if overwrite and st.button(f"Confirm Add/Overwrite {label}", key=f"btn_overwrite_{session_key}"):
                # Overwrite existing by filename
                # Remove files with those names
                files = [f for f in files if f.name not in overwrite_names]
                files.extend(uploaded)
                st.session_state[session_key] = files
                st.success("Files added/overwritten. Please reload or continue.")
                st.experimental_rerun()
        else:
            if st.button(f"Add {label}", key=f"btn_add_{session_key}"):
                files.extend(uploaded)
                st.session_state[session_key] = files
                st.success("Files added. Please reload or continue.")
                st.experimental_rerun()

    # Clear all files
    if files and st.button(f"Clear {label}", key=f"clear_{session_key}"):
        st.session_state[session_key] = []
        st.experimental_rerun()

    return st.session_state.get(session_key, [])

# --- Sidebar: Data Upload ---
st.sidebar.header("📁 Upload Data")
with st.sidebar.expander("Solar Data", expanded=True):
    solar_files = upload_and_manage_files("Solar CSV(s)", "solar_files")
with st.sidebar.expander("Weather Data", expanded=True):
    weather_files = upload_and_manage_files("Weather CSV(s)", "weather_files")

if not solar_files or not weather_files:
    st.warning("Upload both solar and weather data to begin analysis.")
    st.stop()

# --- Data Loading and Caching ---
@st.cache_data(show_spinner=False)
def load_and_prep_solar(files):
    solar_dfs = []
    for f in files:
        df = pd.read_csv(f)
        if 'last_changed' not in df.columns:
            raise ValueError("Missing 'last_changed' in solar data")
        df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
        df = df.dropna(subset=['last_changed'])
        df['last_changed'] = df['last_changed'].dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
        df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
        df['entity_id'] = df['entity_id'].str.lower().str.strip()
        solar_dfs.append(df)
    solar_data = pd.concat(solar_dfs, ignore_index=True)
    solar_pivot = solar_data.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last').reset_index()
    return solar_pivot

@st.cache_data(show_spinner=False)
def load_and_prep_weather(files):
    weather_dfs = []
    for f in files:
        df = pd.read_csv(f)
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
        df = df.dropna(subset=['period_end'])
        df['period_end'] = df['period_end'].dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
        for col in df.columns:
            if col not in ['period_end', 'period']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        weather_dfs.append(df)
    weather_data = pd.concat(weather_dfs, ignore_index=True)
    # Add expected_power_kw if GTI present
    total_capacity_kw = 221.43
    performance_ratio = 0.8
    if 'gti' in weather_data.columns:
        weather_data['expected_power_kw'] = weather_data['gti'] * total_capacity_kw * performance_ratio / 1000
    return weather_data

try:
    solar_pivot = load_and_prep_solar(solar_files)
    weather_data = load_and_prep_weather(weather_files)
except Exception as e:
    st.error(f"Error loading files: {e}")
    st.stop()

# --- Date Filter ---
st.sidebar.header("📅 Filter")
solar_min = solar_pivot['last_changed'].min() if not solar_pivot.empty else pd.Timestamp.today()
solar_max = solar_pivot['last_changed'].max() if not solar_pivot.empty else pd.Timestamp.today()
start, end = st.sidebar.date_input("Select Date Range", [solar_min, solar_max])
sdate, edate = pd.to_datetime(start), pd.to_datetime(end)
solar_filtered = solar_pivot[(solar_pivot['last_changed'] >= sdate) & (solar_pivot['last_changed'] <= edate)]
weather_filtered = weather_data[(weather_data['period_end'] >= sdate) & (weather_data['period_end'] <= edate)]

# --- Chart Plot Function ---
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

# --- Sidebar Controls for Solar & Weather ---
with st.sidebar.expander("🔆 Solar Chart Controls", expanded=True):
    solar_params = [col for col in solar_filtered.columns if col != 'last_changed']
    solar_num_charts = st.number_input("Number of Solar Charts", min_value=1, max_value=min(3, len(solar_params)), value=1, key="solar_num")
    solar_chart_types = []
    solar_selected_params = []
    for i in range(solar_num_charts):
        param = st.selectbox(f"Solar Parameter {i+1}", solar_params, key=f'solar_param_{i}')
        ctype = st.selectbox(f"Chart Type {i+1}", ["Line", "Bar", "Scatter", "Area"], key=f'solar_ctype_{i}')
        solar_selected_params.append(param)
        solar_chart_types.append(ctype)

with st.sidebar.expander("🌦️ Weather Chart Controls", expanded=True):
    weather_params = [col for col in weather_filtered.columns if col not in ['period_end', 'period']]
    weather_num_charts = st.number_input("Number of Weather Charts", min_value=1, max_value=min(3, len(weather_params)), value=1, key="weather_num")
    weather_chart_types = []
    weather_selected_params = []
    for i in range(weather_num_charts):
        param = st.selectbox(f"Weather Parameter {i+1}", weather_params, key=f'weather_param_{i}')
        ctype = st.selectbox(f"Chart Type {i+1}", ["Line", "Bar", "Scatter", "Area"], key=f'weather_ctype_{i}')
        weather_selected_params.append(param)
        weather_chart_types.append(ctype)

# --- Layout: Solar & Weather Charts Side by Side ---
st.markdown("## Compare Solar & Weather Data")
cols = st.columns(2)
with cols[0]:
    st.subheader("🔆 Solar Charts")
    for i in range(solar_num_charts):
        fig = plot_with_slider(solar_filtered, 'last_changed', solar_selected_params[i], solar_chart_types[i], f"{solar_selected_params[i]} ({solar_chart_types[i]})")
        st.plotly_chart(fig, use_container_width=True, key=f"solar_chart_{i}")

with cols[1]:
    st.subheader("🌦️ Weather Charts")
    for i in range(weather_num_charts):
        fig = plot_with_slider(weather_filtered, 'period_end', weather_selected_params[i], weather_chart_types[i], f"{weather_selected_params[i]} ({weather_chart_types[i]})")
        st.plotly_chart(fig, use_container_width=True, key=f"weather_chart_{i}")

# --- AI Assistant (no OpenAI) ---
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

# --- Sharing Instructions ---
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
