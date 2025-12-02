# app.py — Minimal Unified Energy Dashboard (Light • Clean • Robust)
# Built by Hussein Akim — December 2025

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import openpyxl
import io
import requests
from typing import List

# ------------------ CONFIGURATION ------------------
TOTAL_CAPACITY_KW = 221.43
GOODWE_KW = 110.0
FRONIUS_KW = 60.0
INVERTER_TOTAL_KW = GOODWE_KW + FRONIUS_KW
TZ = 'Africa/Johannesburg'
DEFAULT_COST_PER_KWH = 2.98

SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"

# Friendly names for readability (when showing charts / labels)
FRIENDLY = {
    "sum_grid_power": "Solar Output (kW)",
    "expected_total_kw": "Expected (total panels) kW",
    "expected_inverter_kw": "Expected (inverter capacity) kW",
    "expected_goodwe_kw": "Expected GoodWe (kW)",
    "expected_fronius_kw": "Expected Fronius (kW)",
    "sensor.generator_fuel_consumed": "Generator Fuel (L)",
    "sensor.generator_runtime_duration": "Generator Runtime (h)",
    "daily_factory_kwh": "Factory kWh/day",
    "sensor.kehua_internal_power": "Kehua Power (kW)"
}

# ------------------ MINIMAL CSS / LIGHT THEME ------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
}
[data-testid="stAppViewContainer"] > .main {
    background: #f9fafb;
    padding: 24px 32px 48px 32px;
}
.card {
    background: white;
    padding: 16px;
    margin-bottom: 24px;
    border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
section[data-testid="stSidebar"] > div {
    padding: 24px 16px 24px 16px;
    background: #ffffff;
}
</style>
""", unsafe_allow_html=True)

# ------------------ SETUP ------------------
st.set_page_config(page_title="Energy Dashboard", layout="wide", initial_sidebar_state="expanded")

# Header with free/open‑source icon
st.markdown("""
<div style="display: flex; align-items: center; gap: 12px;">
  <img src="https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/sun.svg" width="36px" style="filter: invert(0.15);"/>
  <h1 style="margin: 0;">Southern Paarl Energy Dashboard</h1>
</div>
""", unsafe_allow_html=True)
st.write("")

# ------------------ SIDEBAR (Filters & Navigation) ------------------
with st.sidebar:
    st.header("⚙️ Configuration & Filters")
    page = st.radio("Select view", ["Solar", "Generator", "Factory", "Kehua", "Billing"], index=0)
    
    st.markdown("---")
    st.subheader("Date Range")
    today = datetime.today().date()
    start_date = st.date_input("From", value=today - timedelta(days=30))
    end_date = st.date_input("To",   value=today)
    
    st.markdown("---")
    st.subheader("Estimates & Cost Settings")
    show_estimates = st.checkbox("Show expected power & shortfall", value=True)
    cost_per_kwh = st.number_input("Cost per kWh (ZAR)", min_value=0.0, value=DEFAULT_COST_PER_KWH, step=0.01)

# ------------------ DATA LOADING & NORMALIZATION ------------------
@st.cache_data
def safe_read(url: str) -> pd.DataFrame:
    try:
        return pd.read_csv(url)
    except Exception:
        return pd.DataFrame()

def normalize_ha(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = set(map(str.lower, df.columns))
    if {'last_changed', 'state', 'entity_id'}.issubset(cols):
        df = df.rename(columns={c: c.lower() for c in df.columns})
        df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
        df['entity_id'] = df['entity_id'].str.lower().str.strip()
        pivot = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean')
        return pivot.reset_index()
    # fallback: attempt to detect a datetime/time column
    for c in df.columns:
        if 'time' in c.lower() or 'date' in c.lower() or 'period' in c.lower():
            try:
                df[c] = pd.to_datetime(df[c], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
                df = df.rename(columns={c: 'last_changed'}).reset_index(drop=True)
                return df
            except Exception:
                pass
    return pd.DataFrame()

def load_multiple(urls: List[str]) -> pd.DataFrame:
    parts = []
    for u in urls:
        df = safe_read(u)
        norm = normalize_ha(df)
        if not norm.empty:
            parts.append(norm)
    if parts:
        big = pd.concat(parts, ignore_index=True, sort=False)
        big = big.sort_values('last_changed').reset_index(drop=True)
        return big
    return pd.DataFrame()

@st.cache_data
def load_weather(gti_factor: float, pr: float) -> pd.DataFrame:
    df = safe_read(WEATHER_URL)
    if not isinstance(df, pd.DataFrame) or df.empty:
        # Return empty DataFrame with expected structure
        return pd.DataFrame(columns=['period_end', 'gti', 'expected_total_kw',
                                     'expected_inverter_kw', 'expected_goodwe_kw', 'expected_fronius_kw'])
    # attempt to detect time column
    time_col = None
    for c in df.columns:
        if 'period_end' in c.lower() or 'time' in c.lower() or 'date' in c.lower():
            time_col = c
            break
    if time_col is None:
        time_col = df.columns[0]
    try:
        df[time_col] = pd.to_datetime(df[time_col], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
    except Exception:
        pass
    # detect GTI column
    gti_col = None
    for c in df.columns:
        if 'gti' in c.lower() or 'irradi' in c.lower() or 'ghi' in c.lower():
            gti_col = c
            break
    if gti_col:
        df = df.rename(columns={time_col: 'period_end', gti_col: 'gti'})
    else:
        df = df.rename(columns={time_col: 'period_end'})
        df['gti'] = pd.Series([0.9] * len(df))
    # ensure numeric
    df['gti'] = pd.to_numeric(df['gti'], errors='coerce').fillna(0)

    # expected values
    df['expected_total_kw'] = df['gti'] * gti_factor * TOTAL_CAPACITY_KW * pr
    df['expected_inverter_kw'] = df['gti'] * gti_factor * INVERTER_TOTAL_KW * pr
    df['expected_goodwe_kw'] = df['gti'] * gti_factor * GOODWE_KW * pr
    df['expected_fronius_kw'] = df['gti'] * gti_factor * FRONIUS_KW * pr

    return df[['period_end', 'gti', 'expected_total_kw', 'expected_inverter_kw',
               'expected_goodwe_kw', 'expected_fronius_kw']]

# Load data
with st.spinner("Loading data..."):
    solar_df   = load_multiple(SOLAR_URLS)
    weather_df = load_weather(1.0, DEFAULT_COST_PER_KWH)
    gen_df     = load_multiple([GEN_URL])
    factory_df = load_multiple([FACTORY_URL])
    kehua_df   = load_multiple([KEHUA_URL])

# process factory daily kWh if available
if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

# merge datasets by time (nearest)
dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df] if not df.empty]
if dfs:
    merged = dfs[0].copy()
    for df in dfs[1:]:
        merged = pd.merge_asof(
            merged.sort_values('last_changed'),
            df.sort_values('last_changed'),
            on='last_changed', direction='nearest', tolerance=pd.Timedelta('2H')
        )
else:
    merged = pd.DataFrame()

# convert W → kW if necessary and sum
if not merged.empty:
    for col in ['sensor.fronius_grid_power', 'sensor.goodwe_grid_power', 'sensor.kehua_internal_power']:
        if col in merged.columns:
            try:
                merged[col] = pd.to_numeric(merged[col], errors='coerce') / 1000.0
            except Exception:
                pass
    merged['sum_grid_power'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

# filter by date
if not merged.empty:
    merged['last_changed'] = pd.to_datetime(merged['last_changed'], errors='coerce')
    mask = (merged['last_changed'] >= pd.to_datetime(start_date)) & (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged.loc[mask].copy()
else:
    filtered = pd.DataFrame()

# if estimates requested and weather data exists, merge expected columns
if show_estimates and not weather_df.empty:
    merged_weather = weather_df.sort_values('period_end')
    filtered = pd.merge_asof(
        filtered.sort_values('last_changed'),
        merged_weather,
        left_on='last_changed',
        right_on='period_end',
        direction='nearest',
        tolerance=pd.Timedelta('3H')
    )
    filtered['actual_kw'] = filtered.get('sum_grid_power', 0).fillna(0)
    filtered['shortfall_kw'] = filtered['expected_total_kw'] - filtered['actual_kw']
    filtered['shortfall_kw'] = filtered['shortfall_kw'].fillna(0)

# ------------------ PLOT HELPER ------------------
def plot_series(df, xcol, ycol, name, color="#2a7ae2", dash=None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x = df[xcol],
        y = df[ycol],
        name = name,
        line = dict(color=color, dash=dash or 'solid', width=2),
        mode = 'lines'
    ))
    fig.update_layout(
        margin=dict(l=20,r=20,t=30,b=20),
        hovermode="x unified",
        template="plotly_white",
        height=400
    )
    return fig

# ------------------ PAGE VIEWS ------------------
if page == "Solar":
    st.subheader("Solar Output & Forecast")
    if filtered.empty:
        st.info("No solar data available for this date range.")
    else:
        fig = plot_series(filtered, 'last_changed', 'sum_grid_power', "Actual Solar Output", "#00C853")
        if show_estimates and 'expected_total_kw' in filtered.columns:
            fig.add_trace(go.Scatter(
                x=filtered['last_changed'],
                y=filtered['expected_total_kw'],
                name="Expected (total panels)",
                line=dict(color="#007AFF", dash='dot', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=filtered['last_changed'],
                y=filtered['expected_inverter_kw'],
                name="Expected (inverter cap)",
                line=dict(color="#8B5CF6", dash='dash', width=2)
            ))
        st.plotly_chart(fig, use_container_width=True)

        # download CSV (solar + estimates)
        to_dl = filtered[['last_changed', 'sum_grid_power',
                          'expected_total_kw', 'expected_inverter_kw',
                          'expected_goodwe_kw', 'expected_fronius_kw']].copy()
        st.download_button(
            label="Download Solar CSV",
            data=to_dl.to_csv(index=False),
            file_name=f"solar_data_{start_date}_{end_date}.csv",
            mime="text/csv"
        )

elif page == "Generator":
    st.subheader("Generator Performance")
    if filtered.empty:
        st.info("No generator data for the selected date range.")
    else:
        if 'sensor.generator_fuel_consumed' in filtered.columns:
            st.plotly_chart(plot_series(filtered, 'last_changed', 'sensor.generator_fuel_consumed',
                                        FRIENDLY.get('sensor.generator_fuel_consumed', 'Fuel (L)'), "#DC2626"),
                             use_container_width=True)
        if 'sensor.generator_runtime_duration' in filtered.columns:
            st.plotly_chart(plot_series(filtered, 'last_changed', 'sensor.generator_runtime_duration',
                                        FRIENDLY.get('sensor.generator_runtime_duration', 'Runtime (h)'), "#7C3AED"),
                             use_container_width=True)

elif page == "Factory":
    st.subheader("Factory Electricity Consumption")
    if 'daily_factory_kwh' in factory_df.columns:
        df2 = factory_df.sort_values('last_changed')[['last_changed', 'daily_factory_kwh']]
        st.plotly_chart(plot_series(df2, 'last_changed', 'daily_factory_kwh',
                                    FRIENDLY.get('daily_factory_kwh', 'Factory kWh/day'), "#0E7CFF"),
                         use_container_width=True)
    else:
        st.info("No factory consumption data available.")

elif page == "Kehua":
    st.subheader("Kehua Internal Power")
    if 'sensor.kehua_internal_power' in filtered.columns:
        st.plotly_chart(plot_series(filtered, 'last_changed', 'sensor.kehua_internal_power',
                                    FRIENDLY.get('sensor.kehua_internal_power', 'Kehua kW'), "#06B6D4"),
                         use_container_width=True)
    else:
        st.info("No Kehua internal power data available.")

elif page == "Billing":
    st.subheader("Billing Editor – September 2025")
    try:
        resp = requests.get(BILLING_URL, timeout=15)
        resp.raise_for_status()
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
    except Exception as e:
        st.error(f"Could not load billing workbook: {e}")
        ws = None

    if ws:
        col1, col2 = st.columns(2)
        with col1:
            b2 = ws['B2'].value or ""
            try:
                from_date = st.date_input("From (B2)", value=datetime.strptime(b2, "%d/%m/%y").date())
            except:
                from_date = st.date_input("From (B2)")
            b3 = ws['B3'].value or ""
            try:
                to_date = st.date_input("To (B3)", value=datetime.strptime(b3, "%d/%m/%y").date())
            except:
                to_date = st.date_input("To (B3)")
        with col2:
            c7 = st.number_input("C7 – Freedom Village Units", value=float(ws['C7'].value or 0))
            c9 = st.number_input("C9 – Boerdery Units", value=float(ws['C9'].value or 0))
            e9 = st.number_input("E9 – Boerdery Cost", value=float(ws['E9'].value or 0))
            g21 = st.number_input("G21 – Drakenstein Account", value=float(ws['G21'].value or 0))

        st.subheader("Boerdery Subunits")
        c10 = st.number_input("C10", value=float(ws['C10'].value or 0))
        c11 = st.number_input("C11", value=float(ws['C11'].value or 0))
        c12 = st.number_input("C12", value=float(ws['C12'].value or 0))

        if st.button("Apply & Preview"):
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['C7'].value = c7
            ws['C9'].value = c9
            ws['C10'].value = c10
            ws['C11'].value = c11
            ws['C12'].value = c12
            ws['E7'] = '=C7*D7'
            ws['E9'].value = e9
            ws['G21'].value = g21

            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.session_state['edited_billing'] = buf.getvalue()

            preview = pd.read_excel(buf, header=None)
            st.dataframe(preview, use_container_width=True)

        if 'edited_billing' in st.session_state:
            st.download_button("Download Edited Billing (.xlsx)",
                               st.session_state['edited_billing'],
                               file_name=f"billing_{from_date}_{to_date}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ------------------ FOOTER ------------------
st.markdown("---")
st.caption("© Durr Bottling • Built by Hussein Akim • December 2025")
