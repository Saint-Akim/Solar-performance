import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---- Folder Setup ----
UPLOAD_ROOT = "uploads"
SOLAR_DIR = os.path.join(UPLOAD_ROOT, "solar")
WEATHER_DIR = os.path.join(UPLOAD_ROOT, "weather")
os.makedirs(SOLAR_DIR, exist_ok=True)
os.makedirs(WEATHER_DIR, exist_ok=True)

# ---- File Handling Utilities ----
def save_files_to_disk(uploaded_files, folder):
    for file in uploaded_files:
        file_path = os.path.join(folder, file.name)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

def load_files_from_disk(folder):
    files = []
    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if os.path.isfile(fpath) and fname.lower().endswith(".csv"):
            files.append(fpath)
    return files

def delete_files_from_disk(folder):
    for fname in os.listdir(folder):
        fpath = os.path.join(folder, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)

def remove_single_file(folder, filename):
    fpath = os.path.join(folder, filename)
    if os.path.isfile(fpath):
        os.remove(fpath)

def display_file_list(files, folder, filetype):
    for fname in files:
        col1, col2 = st.columns([4,1])
        with col1:
            st.write(f"- {os.path.basename(fname)}")
        with col2:
            if st.button(f"Delete", key=f"del_{filetype}_{fname}"):
                remove_single_file(folder, os.path.basename(fname))
                st.rerun()

def upload_section(label, folder, filetype):
    st.write(f"### {label}")
    existing_files = load_files_from_disk(folder)
    if existing_files:
        st.success(f"{len(existing_files)} file(s) currently stored:")
        display_file_list(existing_files, folder, filetype)
        if st.button(f"Clear all {label}", key=f"clear_{filetype}"):
            delete_files_from_disk(folder)
            st.rerun()

    uploaded_files = st.file_uploader(f"Add/Replace {label}", type="csv", accept_multiple_files=True, key=f"uploader_{filetype}")
    if uploaded_files:
        existing_names = [os.path.basename(f) for f in existing_files]
        to_overwrite = [f.name for f in uploaded_files if f.name in existing_names]
        if to_overwrite:
            st.warning(f"File(s) already exist and will be overwritten: {', '.join(to_overwrite)}")
            if st.button(f"Confirm Overwrite {label}", key=f"overwrite_{filetype}"):
                save_files_to_disk(uploaded_files, folder)
                st.success("Files uploaded and overwritten as needed.")
                st.rerun()
        else:
            if st.button(f"Add {label}", key=f"add_{filetype}"):
                save_files_to_disk(uploaded_files, folder)
                st.success("Files uploaded.")
                st.rerun()

    # Return up-to-date file list
    return load_files_from_disk(folder)

# ---- Sidebar: API Keys ----
st.sidebar.header("🔐 API Keys (Optional)")
cohere_key = st.sidebar.text_input("Cohere API Key", type="password", key="cohere_key")
hug_key = st.sidebar.text_input("Hugging Face API Key", type="password", key="hug_key")
replicate_key = st.sidebar.text_input("Replicate API Key", type="password", key="replicate_key")

# ---- Sidebar: File Upload and Management ----
st.sidebar.header("📁 Upload Data")
with st.sidebar.expander("Solar Data", expanded=True):
    solar_files = upload_section("Solar CSV(s)", SOLAR_DIR, "solar")
with st.sidebar.expander("Weather Data", expanded=True):
    weather_files = upload_section("Weather CSV(s)", WEATHER_DIR, "weather")

if not solar_files or not weather_files:
    st.warning("Upload both solar and weather data to begin analysis.")
    st.stop()

# ---- Data Loading ----
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

# ---- Date Filter ----
st.sidebar.header("📅 Filter")
solar_min = solar_pivot['last_changed'].min() if not solar_pivot.empty else pd.Timestamp.today()
solar_max = solar_pivot['last_changed'].max() if not solar_pivot.empty else pd.Timestamp.today()
start, end = st.sidebar.date_input("Select Date Range", [solar_min, solar_max])
sdate, edate = pd.to_datetime(start), pd.to_datetime(end)
solar_filtered = solar_pivot[(solar_pivot['last_changed'] >= sdate) & (solar_pivot['last_changed'] <= edate)]
weather_filtered = weather_data[(weather_data['period_end'] >= sdate) & (weather_data['period_end'] <= edate)]

# ---- Chart Plot Function ----
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

# ---- Sidebar Controls for Solar & Weather ----
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

# ---- Layout: Solar & Weather Charts Side by Side ----
st.markdown("## Compare Solar & Weather Data")
cols = st.columns(2)
with cols[0]:
    st.subheader("🔆 Solar Charts")
    if solar_filtered.empty:
        st.warning("No solar data available for the selected date range.")
    else:
        for i in range(solar_num_charts):
            fig = plot_with_slider(solar_filtered, 'last_changed', solar_selected_params[i], solar_chart_types[i], f"{solar_selected_params[i]} ({solar_chart_types[i]})")
            st.plotly_chart(fig, use_container_width=True, key=f"solar_chart_{i}")

with cols[1]:
    st.subheader("🌦️ Weather Charts")
    if weather_filtered.empty:
        st.warning("No weather data available for the selected date range.")
    else:
        for i in range(weather_num_charts):
            fig = plot_with_slider(weather_filtered, 'period_end', weather_selected_params[i], weather_chart_types[i], f"{weather_selected_params[i]} ({weather_chart_types[i]})")
            st.plotly_chart(fig, use_container_width=True, key=f"weather_chart_{i}")

# ---- AI Assistant (Optional, no OpenAI) ----
st.subheader("🤖 AI Data Analysis (Cohere/HuggingFace/Replicate)")
question = st.text_input("Ask a question about your solar or weather data")
if question:
    if cohere_key:
        try:
            import cohere
            co = cohere.Client(cohere_key)
            with st.spinner("Thinking..."):
                response = co.chat(message=question)
                st.success(response.text)
        except Exception as e:
            st.error(f"Error with Cohere API: {e}")
    elif hug_key:
        st.info("HuggingFace model integration goes here.")
    elif replicate_key:
        st.info("Replicate model integration goes here.")
    else:
        st.info("Enter a model API key (Cohere, Hugging Face, or Replicate) for smart responses.")

# ---- Sharing Instructions ----
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
