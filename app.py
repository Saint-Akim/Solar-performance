# app.py — Southern Paarl Energy Dashboard (Enhanced UI • December 2025)
# Logic: UNCHANGED | UI: Dynamic Light/Dark Mode + Home Assistant Style

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ PAGE CONFIG & STATE ------------------
st.set_page_config(
    page_title="Southern Paarl Energy", 
    page_icon="⚡",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize Theme State
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'

# ------------------ DYNAMIC CSS (LIGHT/DARK) ------------------
# Define theme colors
if st.session_state.theme == 'dark':
    colors = {
        "bg": "#111111",
        "sb_bg": "#1c1c1e",
        "card_bg": "#2c2c2e",
        "text": "#ffffff",
        "subtext": "#a1a1a6",
        "border": "#3a3a3c",
        "shadow": "0 8px 32px rgba(0,0,0,0.4)",
        "chart_template": "plotly_dark",
        "input_bg": "#1c1c1e"
    }
else:
    colors = {
        "bg": "#f2f4f6",
        "sb_bg": "#ffffff",
        "card_bg": "#ffffff",
        "text": "#1d1d1f",
        "subtext": "#86868b",
        "border": "#d2d2d7",
        "shadow": "0 4px 24px rgba(0,0,0,0.04)",
        "chart_template": "plotly_white",
        "input_bg": "#ffffff"
    }

st.markdown(f"""
<style>
    /* Main Backgrounds */
    .stApp {{background-color: {colors['bg']} !important;}}
    [data-testid="stSidebar"] {{background-color: {colors['sb_bg']} !important; border-right: 1px solid {colors['border']} !important;}}
    
    /* Global Text */
    h1, h2, h3, h4, p, div, span, label, .stMarkdown {{
        color: {colors['text']} !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, sans-serif !important;
    }}
    
    /* Mushroom/HA Style Cards */
    .energy-card {{
        background-color: {colors['card_bg']} !important;
        border-radius: 20px !important;
        padding: 26px !important;
        margin: 16px 0 !important;
        box-shadow: {colors['shadow']} !important;
        border: 1px solid {colors['border']} !important;
        transition: transform 0.2s ease;
    }}
    
    /* Header Gradient */
    .header-title {{
        font-size: 42px !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #007AFF, #00C853) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-align: center !important;
        margin: 30px 0 10px 0 !important;
    }}
    
    /* Custom Input Styling */
    .stTextInput input, .stNumberInput input, .stDateInput input {{
        background-color: {colors['input_bg']} !important;
        color: {colors['text']} !important;
        border: 1px solid {colors['border']} !important;
        border-radius: 12px !important;
    }}
    
    /* Hide Streamlit Elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:20px 0;">
        <div style="width:80px; height:80px; background:linear-gradient(135deg,#007AFF,#00C853); border-radius:50%; margin:0 auto 15px; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:32px; box-shadow:0 4px 20px rgba(0,200,83,0.3);">HA</div>
        <div style="font-weight:700; font-size:22px; color:{colors['text']};">Hussein Akim</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Theme Toggle
    st.markdown("### Settings")
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1: st.markdown("**Dark Mode**")
    with col_t2: 
        if st.toggle("Theme", value=(st.session_state.theme == 'dark'), label_visibility="collapsed"):
            if st.session_state.theme == 'light':
                st.session_state.theme = 'dark'
                st.rerun()
        else:
            if st.session_state.theme == 'dark':
                st.session_state.theme = 'light'
                st.rerun()

    st.markdown("---")
    
    st.markdown("**Configuration**")
    st.markdown("<small style='color:#888'>GTI Factor</small>", unsafe_allow_html=True)
    gti_factor = st.slider("GTI", 0.50, 1.50, 1.00, 0.01, label_visibility="collapsed")
    
    st.markdown("<small style='color:#888'>Performance Ratio</small>", unsafe_allow_html=True)
    pr_ratio = st.slider("PR", 0.50, 1.00, 0.80, 0.01, label_visibility="collapsed")
    
    st.markdown("<small style='color:#888'>Cost per kWh (ZAR)</small>", unsafe_allow_html=True)
    cost_per_unit = st.number_input("Cost", min_value=0.0, value=2.98, step=0.01, label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("From", datetime(2025, 5, 1))
    with col2: end_date = st.date_input("To", datetime(2025, 5, 31))
    
    st.markdown("---")
    page = st.radio("Navigation", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")

# ------------------ DATA LOADING (LOGIC UNCHANGED) ------------------
TOTAL_CAPACITY_KW = 221.43
TZ = 'Africa/Johannesburg'

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

@st.cache_data(show_spinner="Loading data...")
def load_csvs(urls):
    dfs = []
    for url in urls:
        try:
            df = pd.read_csv(url)
            if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
                df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
                df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
                df['entity_id'] = df['entity_id'].str.lower().str.strip()
                piv = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
                dfs.append(piv)
        except Exception as e: print(f"Error loading {url}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

@st.cache_data(show_spinner="Loading weather data...")
def load_weather(gti, pr):
    try:
        df = pd.read_csv(WEATHER_URL)
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        df['expected_power_kw'] = df['gti'] * gti * TOTAL_CAPACITY_KW * pr / 1000
        return df
    except Exception as e: print(f"Error loading weather: {e}")
    return pd.DataFrame()

solar_df = load_csvs(SOLAR_URLS)
weather_df = load_weather(gti_factor, pr_ratio)
gen_df = load_csvs([GEN_URL])
factory_df = load_csvs([FACTORY_URL])
kehua_df = load_csvs([KEHUA_URL])

if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(col),
                               left_on='last_changed', right_on=col, direction='nearest')
else:
    merged = pd.DataFrame()

if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns: merged['sensor.goodwe_grid_power'] /= 1000
    merged['sum_grid_power'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

filtered = pd.DataFrame()
if not merged.empty:
    mask = (merged['last_changed'] >= pd.to_datetime(start_date)) & \
           (merged['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged.loc[mask].copy()

# ------------------ ENHANCED CHART FUNCTION (THEME AWARE) ------------------
def plot(df, x, y, title, color):
    # Determine chart background based on current theme
    chart_bg = colors['card_bg']
    grid_color = "#3a3a3c" if st.session_state.theme == 'dark' else "#f0f0f0"
    
    if df.empty or y not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(color=colors['text']))
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color, width=2.5)))
        if 'expected_power_kw' in df.columns and title == "Actual Power (kW)":
            fig.add_trace(go.Scatter(x=df[x], y=df['expected_power_kw'], name="Expected", line=dict(color="#007AFF", width=2.5, dash="dot")))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color=colors['text'])),
        xaxis_title="Time",
        yaxis_title="Value",
        hovermode='x unified',
        template=colors['chart_template'],
        height=450,
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor=chart_bg,
        paper_bgcolor=chart_bg,
        font=dict(color=colors['text']),
        xaxis=dict(gridcolor=grid_color, gridwidth=1),
        yaxis=dict(gridcolor=grid_color, gridwidth=1)
    )
    return fig

# ------------------ MAIN CONTENT ------------------
st.markdown("<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:{colors['subtext']}; font-size:18px; margin-bottom:40px;'>Solar • Generator • Factory • Billing Dashboard</p>", unsafe_allow_html=True)

if page == "Solar":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.plotly_chart(plot(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "#00C853"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Generator Performance")
    st.plotly_chart(plot(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel Consumed (L)", "#DC2626"), use_container_width=True)
    st.plotly_chart(plot(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (h)", "#7C3AED"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Daily Factory Consumption")
    st.plotly_chart(plot(filtered, 'last_changed', 'daily_factory_kwh', "Daily kWh", "#0EA5E9"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Kehua Internal Power")
    st.plotly_chart(plot(filtered, 'last_changed', 'sensor.kehua_internal_power', "Power (kW)", "#06B6D4"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Billing Editor – September 2025")
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
    except Exception as e:
        st.error(f"Could not load billing file: {e}")
        ws = None

    if ws:
        col1, col2 = st.columns(2)
        with col1:
            b2 = ws['B2'].value or "30/09/25"
            from_date = st.date_input("From", value=datetime.strptime(b2, "%d/%m/%y").date())
            to_date = st.date_input("To", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
        with col2:
            c7 = st.number_input("Freedom Village (C7)", value=float(ws['C7'].value or 0))
            c9 = st.number_input("Boerdery (C9)", value=float(ws['C9'].value or 0))
            e9 = st.number_input("Boerdery Cost (E9)", value=float(ws['E9'].value or 0))
            g21 = st.number_input("Drakenstein (G21)", value=float(ws['G21'].value or 0))

        st.markdown("### Boerdery Subunits")
        sc1, sc2, sc3 = st.columns(3)
        with sc1: c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
        with sc2: c11 = st.number_input("Pomp, Willie (C11)", value=float(ws['C11'].value or 0))
        with sc3: c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

        if st.button("Apply Changes & Preview", type="primary"):
            ws['A1'].value = from_date.strftime("%b'%y")
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['B4'].value = (to_date - from_date).days
            ws['C7'].value = c7; ws['C9'].value = c9
            ws['C10'].value = c10; ws['C11'].value = c11; ws['C12'].value = c12
            ws['E7'] = '=C7*D7'
            ws['E9'].value = e9
            ws['G21'].value = g21

            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.session_state.edited = buf.getvalue()
            st.dataframe(pd.read_excel(buf, header=None), use_container_width=True)

        if 'edited' in st.session_state:
            st.download_button(
                "Download Edited September 2025.xlsx",
                st.session_state.edited,
                file_name=f"September 2025 - {from_date.strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown(f"<p style='text-align:center; color:{colors['subtext']}; font-size:14px; margin:40px 0;'>Built with ❤️ by Hussein Akim • Durr Bottling • December 2025</p>", unsafe_allow_html=True)
