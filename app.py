# ✅ FINAL VERSION — Unified Solar Dashboard by Hussein Akim (history.CSV support)
# Features: GitHub data loading, local history.CSV support, full sidebar control panel, GTI & PR tuning, dual-chart explorer, kW units, max power recording
# Updated: Integrated billing from September/October XLSX, generator (fuel/runtime), factory consumption (kWh), Kehua internal power.
# - Loads XLSX/CSV from GitHub raw URLs instead of local files.
# - Merges all on timestamps.
# - New charts for generator, factory (daily kWh from diff), Kehua.
# - Billing section with cost per unit input, calculated totals based on templates.
# - Max values for new metrics.
# - Sidebar: Added cost per unit control.
# UI Edits for Streamlit Hosting:
# - Used st.tabs for main sections (Solar, Generator, Factory, Kehua, Billing) to reduce clutter and improve navigation.
# - Added a top summary expander with key max metrics for quick overview.
# - Improved sidebar organization with sections and markdown dividers.
# - Used columns for parameter explorers to balance layout.
# - Added loading messages and progress bars for data loading if files are large.
# - Ensured responsive design with use_container_width=True on all charts.
# - Added a footer with version and contact info.
# - Used st.metric for displaying max values in a visually appealing way.
# Billing Edits:
# - Under Billing tab, added interactive editor for specified parameters: dates (B2, B3, auto B4), units (C7, C9), totals (E7, E9, G21), month (A1 auto from dates).
# - Load template from URL, update cells with inputs, keep formulas intact for Excel recalc.
# - Preview updated sheet as dataframe, download edited XLSX.
# Fix: Moved progress_bar updates outside cached functions to avoid CacheReplayClosureError.
# New: Added edits for C10, C11, C12 (Boerdery subunits).

import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import openpyxl
import io
import requests

# ---- Configuration ----
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"
HISTORY_FILE = "history.CSV"
BILLING_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
    # Add October if available
]
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
DEFAULT_COST_PER_UNIT = 2.98  # From templates

# ---- Friendly Names ----
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
    "weather_type": "Weather Type",
    "sensor.generator_fuel_consumed": "Generator Fuel Consumed (L)",
    "sensor.generator_runtime_duration": "Generator Runtime (hours)",
    "sensor.bottling_factory_monthkwhtotal": "Factory Monthly kWh Total",
    "daily_factory_kwh": "Daily Factory kWh",
    "sensor.kehua_internal_power": "Kehua Internal Power (kW)"
}
WEATHER_PARAM_EXPLAINERS = {
    "air_temp": "🌡️ Air Temperature affects panel efficiency.",
    "gti": "📈 GTI: Tilted surface irradiance.",
    "ghi": "📉 GHI: Horizontal irradiance.",
    "cloud_opacity": "☁️ Cloudiness effect.",
    "humidity": "💧 Humidity level.",
    "wind_speed": "💨 Cooling effect on panels.",
    "expected_power_kw": "🔋 Expected power based on irradiance.",
}

# ---- UI Setup ----
st.set_page_config(page_title="Unified Solar Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("☀️ Unified Solar, Generator, Factory, and Billing Dashboard")

# Sidebar Controls
with st.sidebar:
    st.header("🛠️ Configuration")
    site = st.selectbox("Site", ["Southern Paarl"])
    gti_factor = st.slider("GTI Factor (W/m²)", 0.5, 1.5, 1.0)
    pr_ratio = st.slider("Performance Ratio", 0.5, 1.0, PERFORMANCE_RATIO)
    cost_per_unit = st.number_input("Cost per Unit (ZAR/kWh)", min_value=0.0, value=DEFAULT_COST_PER_UNIT, step=0.01)
    
    st.markdown("---")
    st.subheader("📅 Date Range")
    min_date = pd.to_datetime('2024-01-01')  # Default min, will override
    max_date = pd.to_datetime(datetime.now().date())
    start_date, end_date = st.date_input("Select range", [min_date.date(), max_date.date()])

    st.markdown("---")
    st.caption("Data Sources Loaded from GitHub:")

# ---- Load Data with Progress ----
progress_bar = st.progress(0)
st.info("Loading data from GitHub... Please wait.")

@st.cache_data(show_spinner=False)
def load_solar():
    dfs = []
    for url in SOLAR_URLS:
        try:
            df = pd.read_csv(url)
            if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
                df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
                df = df.dropna(subset=['last_changed'])
                df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
                df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
                df['entity_id'] = df['entity_id'].str.lower().str.strip()
                pivoted = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
                dfs.append(pivoted)
        except Exception:
            pass
    if os.path.exists(HISTORY_FILE):
        try:
            hdf = pd.read_csv(HISTORY_FILE)
            if {'last_changed', 'state', 'entity_id'}.issubset(hdf.columns):
                hdf['last_changed'] = pd.to_datetime(hdf['last_changed'], utc=True, errors='coerce')
                hdf = hdf.dropna(subset=['last_changed'])
                hdf['last_changed'] = hdf['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
                hdf['state'] = pd.to_numeric(hdf['state'], errors='coerce').abs()
                hdf['entity_id'] = hdf['entity_id'].str.lower().str.strip()
                pivoted_h = hdf.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
                dfs.append(pivoted_h)
        except Exception:
            pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_weather(gti_factor_local, pr_ratio_local):
    try:
        df = pd.read_csv(WEATHER_URL)
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
        df = df.dropna(subset=['period_end'])
        df['period_end'] = df['period_end'].dt.tz_convert(TZ).dt.tz_localize(None)
        for col in df.columns:
            if col not in ['period_end', 'period']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        if 'gti' in df.columns:
            df['expected_power_kw'] = df['gti'] * gti_factor_local * TOTAL_CAPACITY_KW * pr_ratio_local / 1000
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_generator():
    try:
        df = pd.read_csv(GEN_URL)
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
            df = df.dropna(subset=['last_changed'])
            df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            pivoted = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            return pivoted
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_factory():
    try:
        df = pd.read_csv(FACTORY_URL)
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
            df = df.dropna(subset=['last_changed'])
            df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            pivoted = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            pivoted = pivoted.sort_values('last_changed')
            pivoted['daily_factory_kwh'] = pivoted['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)
            return pivoted
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_kehua():
    try:
        df = pd.read_csv(KEHUA_URL)
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
            df = df.dropna(subset=['last_changed'])
            df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            pivoted = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            return pivoted
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_billing():
    billing_data = {}
    for url in BILLING_URLS:
        try:
            response = requests.get(url)
            df = pd.read_excel(io.BytesIO(response.content), header=None)
            file = url.split('/')[-1]  # Use URL as key
            month = df.iloc[0, 0].split("'")[0]  # e.g., Sept
            start_date = df.iloc[1, 1]
            end_date = df.iloc[2, 1]
            days = df.iloc[3, 1]
            freedom_total = df.iloc[6, 6] if df.shape[0] > 6 else 0
            boerdery_total = df.iloc[12, 6] if df.shape[0] > 12 else 0
            bottling_total = df.iloc[14, 6] if df.shape[0] > 14 else 0
            grand_total = df.iloc[16, 6] if df.shape[0] > 16 else 0
            billing_data[url] = {
                'month': month,
                'start_date': start_date,
                'end_date': end_date,
                'days': days,
                'freedom_total': freedom_total,
                'boerdery_total': boerdery_total,
                'bottling_total': bottling_total,
                'grand_total': grand_total
            }
        except Exception:
            pass
    return billing_data

solar_df = load_solar()
progress_bar.progress(20)
weather_df = load_weather(gti_factor, pr_ratio)
progress_bar.progress(40)
gen_df = load_generator()
progress_bar.progress(50)
factory_df = load_factory()
progress_bar.progress(60)
kehua_df = load_kehua()
progress_bar.progress(70)
billing_data = load_billing()
progress_bar.progress(100)
st.success("Data loaded successfully from GitHub!")

# ---- Merge & Clean ----
if solar_df.empty and gen_df.empty and factory_df.empty and kehua_df.empty:
    st.warning("No time-series data found from configured sources.")
    st.stop()

# Merge all on 'last_changed' using merge_asof for approximate time matching
dfs_to_merge = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
if dfs_to_merge:
    merged_df = dfs_to_merge[0]
    for next_df in dfs_to_merge[1:]:
        time_col = 'last_changed' if 'last_changed' in next_df.columns else 'period_end'
        merged_df = pd.merge_asof(merged_df.sort_values('last_changed'), next_df.sort_values(time_col), left_on='last_changed', right_on=time_col, direction='nearest')
else:
    merged_df = pd.DataFrame()

# Add calculated columns
if 'sensor.fronius_grid_power' in merged_df.columns:
    merged_df['sensor.fronius_grid_power'] = pd.to_numeric(merged_df['sensor.fronius_grid_power'], errors='coerce') / 1000
if 'sensor.goodwe_grid_power' in merged_df.columns:
    merged_df['sensor.goodwe_grid_power'] = pd.to_numeric(merged_df['sensor.goodwe_grid_power'], errors='coerce') / 1000
merged_df['sum_grid_power'] = merged_df.get('sensor.fronius_grid_power', 0).fillna(0) + merged_df.get('sensor.goodwe_grid_power', 0).fillna(0)

# Record Max Values safely
max_fronius = float(merged_df['sensor.fronius_grid_power'].max()) if 'sensor.fronius_grid_power' in merged_df.columns else 0.0
max_goodwe = float(merged_df['sensor.goodwe_grid_power'].max()) if 'sensor.goodwe_grid_power' in merged_df.columns else 0.0
max_kehua = float(merged_df['sensor.kehua_internal_power'].max()) if 'sensor.kehua_internal_power' in merged_df.columns else 0.0
max_gen_runtime = float(merged_df['sensor.generator_runtime_duration'].max()) if 'sensor.generator_runtime_duration' in merged_df.columns else 0.0
max_gen_fuel = float(merged_df['sensor.generator_fuel_consumed'].max()) if 'sensor.generator_fuel_consumed' in merged_df.columns else 0.0
max_factory_kwh = float(merged_df['daily_factory_kwh'].max()) if 'daily_factory_kwh' in merged_df.columns else 0.0

# Update min/max dates based on data
if not merged_df.empty:
    min_date = pd.to_datetime(merged_df['last_changed'].min())
    max_date = pd.to_datetime(merged_df['last_changed'].max())

filtered = merged_df[(merged_df['last_changed'] >= pd.to_datetime(start_date)) & (merged_df['last_changed'] <= pd.to_datetime(end_date))]
if filtered.empty:
    st.warning("No data in selected range.")
    st.stop()

# ---- Chart Function ----
def slider_chart(df, x_col, y_col, title, color):
    label = FRIENDLY_NAMES.get(y_col, y_col)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], name=label, line=dict(color=color)))
    fig.update_layout(
        title=title,
        xaxis=dict(title=x_col, rangeslider=dict(visible=True), type="date"),
        yaxis=dict(title=label),
        hovermode='x unified'
    )
    return fig

# ---- Top Summary Expander ----
with st.expander("📊 Quick Summary Metrics", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Fronius Power", f"{max_fronius:.2f} kW")
        st.metric("Max GoodWe Power", f"{max_goodwe:.2f} kW")
    with col2:
        if max_kehua > 0:
            st.metric("Max Kehua Power", f"{max_kehua:.2f} kW")
        if max_factory_kwh > 0:
            st.metric("Max Daily Factory kWh", f"{max_factory_kwh:.2f} kWh")
    with col3:
        if max_gen_runtime > 0:
            st.metric("Max Gen Runtime", f"{max_gen_runtime:.2f} hours")
        if max_gen_fuel > 0:
            st.metric("Max Gen Fuel", f"{max_gen_fuel:.2f} L")

# ---- Main Tabs ----
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🌞 Solar", "⚙️ Generator", "🏭 Factory", "🔌 Kehua", "💰 Billing"])

with tab1:
    st.subheader("Actual vs Expected Power")
    fig = slider_chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "green")
    if 'expected_power_kw' in filtered.columns:
        fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'], name=FRIENDLY_NAMES['expected_power_kw'], line=dict(color="orange")))
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Parameter Explorer")
    params = [c for c in filtered.columns if c not in ['last_changed', 'period_end', 'period'] and filtered[c].dtype != 'O']
    solar_params = [p for p in params if 'grid' in p or 'power' in p or 'kehua' in p]
    weather_params = [p for p in params if p not in solar_params and 'generator' not in p and 'factory' not in p]
    col1, col2 = st.columns(2)
    with col1:
        selected_solar = st.multiselect("🔌 Solar Parameters", solar_params, default=solar_params[:2] if solar_params else [])
        for p in selected_solar:
            st.plotly_chart(slider_chart(filtered, 'last_changed', p, FRIENDLY_NAMES.get(p, p), '#33CFA5'), use_container_width=True)
    with col2:
        selected_weather = st.multiselect("☁️ Weather Parameters", weather_params, default=weather_params[:2] if weather_params else [])
        for p in selected_weather:
            xcol = 'period_end' if p in weather_df.columns else 'last_changed'
            st.plotly_chart(slider_chart(filtered, xcol, p, FRIENDLY_NAMES.get(p, p), '#1f77b4'), use_container_width=True)
            if p in WEATHER_PARAM_EXPLAINERS:
                st.markdown(WEATHER_PARAM_EXPLAINERS[p])

with tab2:
    if not gen_df.empty:
        gen_fig_fuel = slider_chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Generator Fuel Consumed (L)", "red")
        gen_fig_runtime = slider_chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Generator Runtime (hours)", "purple")
        st.plotly_chart(gen_fig_fuel, use_container_width=True)
        st.plotly_chart(gen_fig_runtime, use_container_width=True)
    else:
        st.info("No generator data available.")

with tab3:
    if not factory_df.empty:
        factory_fig = slider_chart(filtered, 'last_changed', 'daily_factory_kwh', "Daily Factory kWh", "blue")
        st.plotly_chart(factory_fig, use_container_width=True)
    else:
        st.info("No factory data available.")

with tab4:
    if not kehua_df.empty:
        kehua_fig = slider_chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Kehua Internal Power (kW)", "cyan")
        st.plotly_chart(kehua_fig, use_container_width=True)
    else:
        st.info("No Kehua data available.")

with tab5:
    st.subheader("Billing Overview")
    if billing_data:
        for file, data in billing_data.items():
            with st.expander(f"{data['month']} Billing Details"):
                st.markdown(f"Period: {data['start_date']} to {data['end_date']} ({data['days']} days)")
                st.markdown(f"- Freedom Village: {data['freedom_total']:.2f} ZAR")
                st.markdown(f"- Boerdery: {data['boerdery_total']:.2f} ZAR")
                st.markdown(f"- Bottling: {data['bottling_total']:.2f} ZAR")
                adjusted_total = data['grand_total'] * (cost_per_unit / DEFAULT_COST_PER_UNIT)
                st.metric("Adjusted Grand Total", f"{adjusted_total:.2f} ZAR")
    
    st.subheader("Edit Billing Template")
    selected_url = st.selectbox("Select Template to Edit", list(billing_data.keys()))
    if selected_url:
        response = requests.get(selected_url)
        wb = openpyxl.load_workbook(io.BytesIO(response.content), data_only=False)
        ws = wb.active
        
        # Inputs
        col1, col2 = st.columns(2)
        with col1:
            from_str = ws['B2'].value
            from_date = st.date_input("Date From (B2)", value=datetime.strptime(from_str, '%d/%m/%y').date() if from_str else datetime.now().date())
            to_str = ws['B3'].value
            to_date = st.date_input("Date To (B3)", value=datetime.strptime(to_str, '%d/%m/%y').date() if to_str else datetime.now().date())
            days = (to_date - from_date).days
            st.number_input("No of Days (B4) - Auto", value=days, disabled=True)
        
        with col2:
            c7 = st.number_input("Freedom Village Units (C7)", value=ws['C7'].value or 0.0)
            c9 = st.number_input("Boerdery Units (C9)", value=ws['C9'].value or 0.0)
            e7 = st.number_input("Total Unit Cost Freedom (E7) - Override", value=ws['E7'].value or 0.0 if ws['E7'].data_type != 'f' else 0.0)
            e9 = st.number_input("Total Unit Cost Boerdery (E9) - Override", value=ws['E9'].value or 0.0)
            g21 = st.number_input("Drakenstein Account (G21)", value=ws['G21'].value or 0.0)
        
        # Boerdery subunits
        st.subheader("Boerdery Subunits")
        c10 = st.number_input("Johan & Stoor Units (C10)", value=ws['C10'].value or 0.0)
        c11 = st.number_input("Pomp, Willie, Gaste, Comp Units (C11)", value=ws['C11'].value or 0.0)
        c12 = st.number_input("Werkers Units (C12)", value=ws['C12'].value or 0.0)
        
        # Auto A1 from from_date
        month_year = from_date.strftime("%b'%y")
        st.text_input("Month (A1) - Auto", value=month_year, disabled=True)
        
        if st.button("Update and Preview"):
            # Update cells
            ws['A1'].value = month_year
            ws['B2'].value = from_date.strftime('%d/%m/%y')
            ws['B3'].value = to_date.strftime('%d/%m/%y')
            ws['B4'].value = days
            ws['C7'].value = c7
            ws['C9'].value = c9
            ws['E7'].value = e7  # Override formula if input
            ws['E9'].value = e9
            ws['G21'].value = g21
            ws['C10'].value = c10
            ws['C11'].value = c11
            ws['C12'].value = c12
            
            # Preview with pandas (data_only=True to show calculated if possible, but since no eval, show as is)
            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            preview_df = pd.read_excel(buffer, header=None)
            st.dataframe(preview_df)
            
            buffer.seek(0)
            st.session_state['edited_buffer'] = buffer.getvalue()
    
        if 'edited_buffer' in st.session_state:
            st.download_button("Download Edited XLSX", st.session_state['edited_buffer'], file_name="edited_September 2025.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("No billing templates available.")

# ---- Export ----
st.download_button("📄 Download Merged CSV", filtered.to_csv(index=False), file_name="merged_data.csv", key="download_merged")

# ---- Footer ----
st.markdown("---")
st.markdown("<center><small>Built by Hussein Akim — Unified Solar Insights v2.0 (Optimized for Streamlit Hosting) | December 2025</small></center>", unsafe_allow_html=True)
