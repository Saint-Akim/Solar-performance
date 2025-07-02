import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---- Configuration Constants ----
UPLOAD_ROOT = "Uploads"
SOLAR_DIR = os.path.join(UPLOAD_ROOT, "solar")
WEATHER_DIR = os.path.join(UPLOAD_ROOT, "weather")
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'
MAX_FILE_SIZE_MB = 10

# ---- Utility Functions ----
def ensure_dirs():
    """Create upload directories if they do not exist."""
    os.makedirs(SOLAR_DIR, exist_ok=True)
    os.makedirs(WEATHER_DIR, exist_ok=True)
ensure_dirs()

def file_disk_action(folder, action, filename=None):
    """Unified file management: load, delete all, or delete one."""
    if action == "load":
        return [os.path.join(folder, fname) for fname in sorted(os.listdir(folder))
                if os.path.isfile(os.path.join(folder, fname)) and fname.lower().endswith(".csv")]
    elif action == "delete_all":
        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)
    elif action == "delete_one" and filename:
        fpath = os.path.join(folder, filename)
        if os.path.isfile(fpath):
            os.remove(fpath)

def save_files_to_disk(uploaded_files, folder):
    """Save uploaded files to disk."""
    for file in uploaded_files:
        file_path = os.path.join(folder, file.name)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

def check_file_size(uploaded_files):
    """Validate individual file size does not exceed limit."""
    for file in uploaded_files:
        if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            st.error(f"File {file.name} exceeds {MAX_FILE_SIZE_MB}MB limit.")
            return False
    return True

def validate_file_columns(df, required_columns, filetype, filename):
    """Ensure all required columns exist in the dataframe."""
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing column(s) {missing} in {filetype} file: {filename}")

def display_file_list(files, folder, filetype):
    """Display file list with delete buttons."""
    for fname in files:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"- {os.path.basename(fname)}")
        with col2:
            if st.button("Delete", key=f"del_{filetype}_{fname}"):
                file_disk_action(folder, "delete_one", os.path.basename(fname))
                st.rerun()

def upload_section(label, folder, filetype):
    """Handles the file upload, listing, and deletion UI for a given type."""
    st.write(f"### {label}")
    existing_files = file_disk_action(folder, "load")
    if existing_files:
        st.success(f"{len(existing_files)} file(s) currently stored:")
        display_file_list(existing_files, folder, filetype)
        if st.button(f"Clear all {label}", key=f"clear_{filetype}"):
            file_disk_action(folder, "delete_all")
            st.rerun()
    uploaded_files = st.file_uploader(
        f"Add/Replace {label}",
        type="csv",
        accept_multiple_files=True,
        key=f"uploader_{filetype}"
    )
    if uploaded_files and check_file_size(uploaded_files):
        existing_names = [os.path.basename(f) for f in file_disk_action(folder, "load")]
        to_overwrite = [f.name for f in uploaded_files if f.name in existing_names]
        if to_overwrite:
            st.warning(f"File(s) will be overwritten: {', '.join(to_overwrite)}")
        save_files_to_disk(uploaded_files, folder)
        st.success("Files uploaded.")
        st.rerun()
    return file_disk_action(folder, "load")

# ---- Sidebar: File Upload and Management ----
st.set_page_config(page_title="Solar Dashboard", layout="wide")
st.title("☀️ Solar Performance & Weather Analyzer")
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
    """Load and preprocess solar files into a pivot table dataframe."""
    solar_dfs = []
    for f in files:
        df = pd.read_csv(f)
        validate_file_columns(df, ['last_changed', 'state', 'entity_id'], "solar", f)
        df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
        df = df.dropna(subset=['last_changed'])
        df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
        df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
        df['entity_id'] = df['entity_id'].str.lower().str.strip()
        solar_dfs.append(df)
    solar_data = pd.concat(solar_dfs, ignore_index=True)
    solar_pivot = solar_data.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last').reset_index()
    return solar_pivot

@st.cache_data(show_spinner=False)
def load_and_prep_weather(files):
    """Load and preprocess weather files into a dataframe."""
    weather_dfs = []
    for f in files:
        df = pd.read_csv(f)
        validate_file_columns(df, ['period_end'], "weather", f)
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
        df = df.dropna(subset=['period_end'])
        df['period_end'] = df['period_end'].dt.tz_convert(TZ).dt.tz_localize(None)
        for col in df.columns:
            if col not in ['period_end', 'period']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        weather_dfs.append(df)
    weather_data = pd.concat(weather_dfs, ignore_index=True)
    # Add expected_power_kw if GTI present
    if 'gti' in weather_data.columns:
        weather_data['expected_power_kw'] = weather_data['gti'] * TOTAL_CAPACITY_KW * PERFORMANCE_RATIO / 1000
    return weather_data

try:
    with st.spinner("Loading and processing data..."):
        solar_pivot = load_and_prep_solar(solar_files)
        weather_data = load_and_prep_weather(weather_files)
except Exception as e:
    st.error(f"Error loading files: {e}")
    st.stop()

# ---- Date Filter ----
st.sidebar.header("📅 Filter")
solar_min = solar_pivot['last_changed'].min() if not solar_pivot.empty else pd.Timestamp.today()
solar_max = solar_pivot['last_changed'].max() if not solar_pivot.empty else pd.Timestamp.today()
start, end = st.sidebar.date_input(
    "Select Date Range",
    [solar_min, solar_max],
    help="Select the range of dates for analysis."
)
sdate, edate = pd.to_datetime(start), pd.to_datetime(end)
solar_filtered = solar_pivot[(solar_pivot['last_changed'] >= sdate) & (solar_pivot['last_changed'] <= edate)]
weather_filtered = weather_data[(weather_data['period_end'] >= sdate) & (weather_data['period_end'] <= edate)]

# ---- Parameter Selection ----
with st.sidebar.expander("🔆 Solar Chart Controls", expanded=True):
    solar_params = [col for col in solar_filtered.columns if col != 'last_changed']
    solar_num_charts = st.number_input(
        "Number of Solar Charts",
        min_value=1, max_value=min(3, len(solar_params)), value=1, key="solar_num",
        help="Number of different solar parameters to plot."
    )
    solar_selected_params = []
    solar_chart_types = []
    solar_colors = []
    for i in range(solar_num_charts):
        param = st.selectbox(f"Solar Parameter {i+1}", solar_params, key=f'solar_param_{i}', help="Select a solar parameter to plot.")
        ctype = st.selectbox(f"Chart Type {i+1}", ["Line", "Bar", "Scatter", "Area"], key=f'solar_ctype_{i}', help="Chart display type.")
        color = st.color_picker(f"Pick Chart Color {i+1}", "#00f900", key=f'solar_color_{i}')
        solar_selected_params.append(param)
        solar_chart_types.append(ctype)
        solar_colors.append(color)

with st.sidebar.expander("🌦️ Weather Chart Controls", expanded=True):
    weather_params = [col for col in weather_filtered.columns if col not in ['period_end', 'period']]
    weather_num_charts = st.number_input(
        "Number of Weather Charts",
        min_value=1, max_value=min(3, len(weather_params)), value=1, key="weather_num",
        help="Number of different weather parameters to plot."
    )
    weather_selected_params = []
    weather_chart_types = []
    weather_colors = []
    for i in range(weather_num_charts):
        param = st.selectbox(f"Weather Parameter {i+1}", weather_params, key=f'weather_param_{i}', help="Select a weather parameter to plot.")
        ctype = st.selectbox(f"Chart Type {i+1}", ["Line", "Bar", "Scatter", "Area"], key=f'weather_ctype_{i}', help="Chart display type.")
        color = st.color_picker(f"Pick Chart Color {i+1}", "#1e90ff", key=f'weather_color_{i}')
        weather_selected_params.append(param)
        weather_chart_types.append(ctype)
        weather_colors.append(color)

# ---- Chart Plot Function ----
def plot_with_slider(df, x_col, y_col, chart_type, title, color):
    """Plot interactive charts with a slider and custom options."""
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
        fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], name=y_col, marker_color=color))
    else:
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[y_col],
            mode=mode,
            fill=fill,
            name=y_col,
            line=dict(color=color) if mode == "lines" else None,
            marker=dict(color=color) if mode == "markers" else None,
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

# ---- Layout: Solar & Weather Charts Side by Side ----
st.markdown("## Compare Solar & Weather Data")
cols = st.columns(2)
with cols[0]:
    st.subheader("🔆 Solar Charts")
    if solar_filtered.empty:
        st.warning("No solar data available for the selected date range.")
    else:
        for i in range(solar_num_charts):
            fig = plot_with_slider(
                solar_filtered, 'last_changed', solar_selected_params[i],
                solar_chart_types[i], f"{solar_selected_params[i]} ({solar_chart_types[i]})",
                solar_colors[i]
            )
            st.plotly_chart(fig, use_container_width=True, key=f"solar_chart_{i}")

with cols[1]:
    st.subheader("🌦️ Weather Charts")
    if weather_filtered.empty:
        st.warning("No weather data available for the selected date range.")
    else:
        for i in range(weather_num_charts):
            fig = plot_with_slider(
                weather_filtered, 'period_end', weather_selected_params[i],
                weather_chart_types[i], f"{weather_selected_params[i]} ({weather_chart_types[i]})",
                weather_colors[i]
            )
            st.plotly_chart(fig, use_container_width=True, key=f"weather_chart_{i}")

# ---- Sharing Instructions ----
st.markdown("---")
with st.expander("How to Share or Deploy This Dashboard"):
    st.markdown("""
    **Deploying:**
    1. Go to [Streamlit Community Cloud](https://share.streamlit.io/).
    2. Connect your GitHub repo and deploy.
    3. Share the generated URL.

    **Local Sharing:**
    - Find your IP address and use `http://<your-ip>:8501` for network access.
    """)

st.markdown("<center><small>Built by Hussein Akim — Solar Insights</small></center>", unsafe_allow_html=True)
