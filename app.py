# app.py — Southern Paarl Energy Dashboard (Professional UI Update)
# Logic: EXACTLY as requested (Original Linear Loading)
# UI: High-end Corporate SaaS Design + Fixed Inputs

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & THEME STATE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Southern Paarl Energy",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State for Theme
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# -----------------------------------------------------------------------------
# 2. CSS STYLING (PROFESSIONAL & CLEAN)
# -----------------------------------------------------------------------------
# Define Color Schemes
if st.session_state.theme == 'dark':
    # Professional Dark (Deep Slate)
    colors = {
        "bg": "#0e1117",
        "sidebar": "#161b22",
        "card": "#1f242d",
        "text": "#e6e6e6",
        "subtext": "#a0a0a0",
        "border": "#30363d",
        "primary": "#3b82f6", # Corporate Blue
        "chart_theme": "plotly_dark",
        "shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.5)"
    }
else:
    # Professional Light (Clean White/Grey)
    colors = {
        "bg": "#f0f2f5",
        "sidebar": "#ffffff",
        "card": "#ffffff",
        "text": "#1f2937",
        "subtext": "#6b7280",
        "border": "#e5e7eb",
        "primary": "#2563eb", # Corporate Blue
        "chart_theme": "plotly_white",
        "shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)"
    }

st.markdown(f"""
<style>
    /* Main Background */
    .stApp {{
        background-color: {colors['bg']};
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {colors['sidebar']};
        border-right: 1px solid {colors['border']};
    }}
    
    /* Global Typography */
    h1, h2, h3, p, div, span, label, .stMarkdown {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        color: {colors['text']} !important;
    }}
    
    /* Professional Card Container */
    .energy-card {{
        background-color: {colors['card']};
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: {colors['shadow']};
        border: 1px solid {colors['border']};
    }}
    
    /* Input Fields - FIXING THE CALENDAR BUG */
    /* We do NOT force text color on inputs globally, letting Streamlit handle the internal contrast */
    .stDateInput div, .stTextInput div, .stNumberInput div {{
        color: inherit;
    }}
    
    /* Header Styling */
    .header-title {{
        font-size: 32px;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin-bottom: 8px;
        color: {colors['text']} !important;
    }}
    
    /* Customizing the Plotly Chart Container */
    .js-plotly-plot .plotly {{
        background-color: transparent !important;
    }}
    
    /* Buttons */
    .stButton > button {{
        background-color: {colors['primary']} !important;
        color: white !important;
        border-radius: 8px;
        font-weight: 500;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        opacity: 0.9;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    
    /* Hide Streamlit Default Elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    # Profile / Brand Header
    st.markdown(f"""
    <div style="padding: 20px 0; border-bottom: 1px solid {colors['border']}; margin-bottom: 20px;">
        <div style="display:flex; align-items:center; gap:15px;">
            <div style="width:40px; height:40px; background:{colors['primary']}; border-radius:8px; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold;">HA</div>
            <div>
                <div style="font-weight:600; font-size:15px; color:{colors['text']}">Hussein Akim</div>
                <div style="font-size:12px; color:{colors['subtext']}">Durr Bottling</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Theme Toggle
    col_t1, col_t2 = st.columns([0.8, 0.2])
    with col_t1: st.write("Dark Mode")
    with col_t2: 
        if st.toggle("Theme", value=(st.session_state.theme == 'dark'), label_visibility="collapsed"):
            if st.session_state.theme == 'light':
                st.session_state.theme = 'dark'
                st.rerun()
        else:
            if st.session_state.theme == 'dark':
                st.session_state.theme = 'light'
                st.rerun()

    st.markdown("### Configuration")
    
    st.markdown(f"<span style='color:{colors['subtext']}; font-size:12px'>PARAMETERS</span>", unsafe_allow_html=True)
    gti_factor = st.slider("GTI Factor", 0.50, 1.50, 1.00, 0.01)
    pr_ratio = st.slider("Performance Ratio", 0.50, 1.00, 0.80, 0.01)
    cost_per_unit = st.number_input("Cost (ZAR/kWh)", min_value=0.0, value=2.98, step=0.01)
    
    st.markdown(f"<br><span style='color:{colors['subtext']}; font-size:12px'>TIMEFRAME</span>", unsafe_allow_html=True)
    start_date = st.date_input("From Date", datetime(2025, 5, 1))
    end_date = st.date_input("To Date", datetime(2025, 5, 31))
    
    st.markdown(f"<div style='margin: 20px 0; border-top: 1px solid {colors['border']}'></div>", unsafe_allow_html=True)
    
    # Navigation
    page = st.radio("Dashboard View", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")

# -----------------------------------------------------------------------------
# 4. DATA LOADING & LOGIC (UNCHANGED)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 5. UI COMPONENTS (CHARTS)
# -----------------------------------------------------------------------------
def plot_chart(df, x, y, title, color):
    # Dynamic styling for charts
    bg_color = 'rgba(0,0,0,0)' # Transparent to show Card color
    grid_color = '#404040' if st.session_state.theme == 'dark' else '#e5e5e5'
    
    if df.empty or y not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No Data Available", showarrow=False, font=dict(color=colors['text']))
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color, width=2.5)))
        
        # Logic: Add Expected line only for Actual Power
        if 'expected_power_kw' in df.columns and title == "Actual Power (kW)":
            fig.add_trace(go.Scatter(x=df[x], y=df['expected_power_kw'], name="Expected", 
                                     line=dict(color=colors['subtext'], width=2, dash="dot")))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, family="Inter", color=colors['text'])),
        template=colors['chart_theme'],
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        height=450,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(showgrid=False, zeroline=False, color=colors['subtext']),
        yaxis=dict(gridcolor=grid_color, gridwidth=1, color=colors['subtext']),
        hovermode='x unified'
    )
    return fig

# -----------------------------------------------------------------------------
# 6. MAIN CONTENT RENDERING
# -----------------------------------------------------------------------------

st.markdown(f"<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:{colors['subtext']}; margin-bottom:30px;'>Dashboard Overview • {page}</p>", unsafe_allow_html=True)

if page == "Solar":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.plotly_chart(plot_chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", colors['primary']), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Fuel Consumption")
        st.plotly_chart(plot_chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel (L)", "#ef4444"), use_container_width=True)
    with col2:
        st.subheader("Runtime")
        st.plotly_chart(plot_chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (h)", "#8b5cf6"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Daily Factory Consumption")
    st.plotly_chart(plot_chart(filtered, 'last_changed', 'daily_factory_kwh', "Daily kWh", "#0ea5e9"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Kehua Internal Power")
    st.plotly_chart(plot_chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Power (kW)", "#14b8a6"), use_container_width=True)
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
        c1, c2, c3 = st.columns(3)
        with c1:
            b2 = ws['B2'].value or "30/09/25"
            from_date = st.date_input("From Date", value=datetime.strptime(b2, "%d/%m/%y").date())
            c7 = st.number_input("Freedom Village (C7)", value=float(ws['C7'].value or 0))
            g21 = st.number_input("Drakenstein (G21)", value=float(ws['G21'].value or 0))
        with c2:
            to_date = st.date_input("To Date", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
            c9 = st.number_input("Boerdery (C9)", value=float(ws['C9'].value or 0))
            e9 = st.number_input("Boerdery Cost (E9)", value=float(ws['E9'].value or 0))
        with c3:
            st.markdown("**Subunits**")
            c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
            c11 = st.number_input("Pomp, Willie (C11)", value=float(ws['C11'].value or 0))
            c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

        st.markdown("---")
        
        if st.button("Apply Changes & Generate Invoice", type="primary"):
            # Update Logic (Preserved)
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
                "Download Updated Excel",
                st.session_state.edited,
                file_name=f"September 2025 - {from_date.strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    st.markdown("</div>", unsafe_allow_html=True)
