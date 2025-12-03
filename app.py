import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
import concurrent.futures
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & THEME STATE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Southern Paarl Energy",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed" # Cleaner look
)

# Initialize Session State for Theme
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# -----------------------------------------------------------------------------
# 2. UI DESIGN SYSTEM (CSS + THEME LOGIC)
# -----------------------------------------------------------------------------
# Define Theme Colors (Logic from Code 1)
if st.session_state.theme == 'dark':
    theme = {
        "bg": "#0e1117",
        "card": "#1e212b",
        "text": "#ffffff",
        "subtext": "#a0a0a0",
        "border": "1px solid rgba(255, 255, 255, 0.1)",
        "chart": "plotly_dark",
        "accent": "#00C853",
        "input_bg": "rgba(255, 255, 255, 0.05)"
    }
else:
    theme = {
        "bg": "#f8f9fb",
        "card": "#ffffff",
        "text": "#1d1d1f",
        "subtext": "#86868b",
        "border": "1px solid rgba(0, 0, 0, 0.08)",
        "chart": "plotly_white",
        "accent": "#007AFF",
        "input_bg": "rgba(0, 0, 0, 0.03)"
    }

st.markdown(f"""
<style>
    /* IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* GLOBAL APP BACKGROUND */
    .stApp {{
        background-color: {theme['bg']};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* HIDE STREAMLIT CHROME */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* CARD DESIGN (Glassmorphism) */
    .energy-card, .metric-card {{
        background-color: {theme['card']};
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: {theme['border']};
        margin-bottom: 20px;
        transition: transform 0.2s;
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.1);
    }}

    /* METRIC TYPOGRAPHY */
    .metric-label {{
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        color: {theme['subtext']};
        letter-spacing: 0.5px;
    }}
    .metric-value {{
        font-size: 32px;
        font-weight: 700;
        color: {theme['text']};
        margin-top: 5px;
    }}

    /* INPUTS FIX (Crucial for visibility) */
    .stDateInput input, .stNumberInput input, .stTextInput input, .stSelectbox div {{
        color: {theme['text']} !important;
        background-color: {theme['input_bg']} !important;
        border: {theme['border']} !important;
        border-radius: 8px !important;
    }}
    
    /* TABS STYLING */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 45px;
        border-radius: 10px;
        background-color: {theme['input_bg']};
        border: none;
        color: {theme['subtext']};
        font-weight: 600;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background-color: {theme['accent']};
        color: white;
    }}

    /* HEADERS */
    h1, h2, h3, p {{ color: {theme['text']} !important; }}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. FAST DATA LOADING (PARALLEL PROCESSING)
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

def fetch_url(url):
    try:
        df = pd.read_csv(url)
        # Apply strict data cleaning from Code 1
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            return df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        return df
    except: return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_data_parallel():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        s_futures = [executor.submit(fetch_url, u) for u in SOLAR_URLS]
        gen_fut = executor.submit(fetch_url, GEN_URL)
        fac_fut = executor.submit(fetch_url, FACTORY_URL)
        keh_fut = executor.submit(fetch_url, KEHUA_URL)
        
        # Weather data is small, load directly
        try:
            w_df = pd.read_csv(WEATHER_URL)
            w_df['period_end'] = pd.to_datetime(w_df['period_end'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        except: w_df = pd.DataFrame()
        
        s_dfs = [f.result() for f in s_futures if not f.result().empty]
        solar = pd.concat(s_dfs, ignore_index=True) if s_dfs else pd.DataFrame()
        
        return solar, gen_fut.result(), fac_fut.result(), keh_fut.result(), w_df

# Execute Load
with st.spinner("Syncing Energy Systems..."):
    solar_df, gen_df, factory_df, kehua_df, weather_df = load_data_parallel()

# -----------------------------------------------------------------------------
# 4. SIDEBAR & SETTINGS (Preserved from Code 1)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding: 20px 0;">
        <div style="width:60px; height:60px; background: linear-gradient(135deg, #007AFF, #00C853); border-radius: 50%; margin: 0 auto; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:20px;">HA</div>
        <h3 style="margin-top:10px; font-size:18px;">Hussein Akim</h3>
        <p style="color:{theme['subtext']}; font-size:12px;">Durr Bottling</p>
    </div>
    """, unsafe_allow_html=True)

    # Theme Toggle
    col_t1, col_t2 = st.columns([0.7, 0.3])
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

    st.markdown("---")
    st.markdown("### Settings")
    gti_factor = st.slider("GTI Factor", 0.50, 1.50, 1.00, 0.01)
    pr_ratio = st.slider("Performance Ratio", 0.50, 1.00, 0.80, 0.01)
    cost_per_unit = st.number_input("Cost (ZAR/kWh)", min_value=0.0, value=2.98, step=0.01)
    
    st.markdown("### Date Range")
    start_date = st.date_input("From", datetime(2025, 5, 1))
    end_date = st.date_input("To", datetime(2025, 5, 31))

    # Process Weather with sliders
    if not weather_df.empty:
        weather_df['expected_power_kw'] = weather_df['gti'] * gti_factor * TOTAL_CAPACITY_KW * pr_ratio / 1000

# -----------------------------------------------------------------------------
# 5. DATA LOGIC & MERGING (Preserved from Code 1)
# -----------------------------------------------------------------------------
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
# 6. DASHBOARD LAYOUT (UI from Code 2 + Logic from Code 1)
# -----------------------------------------------------------------------------
st.title("Southern Paarl Energy")
st.markdown(f"<p style='color:{theme['subtext']}; margin-top:-15px'>Dashboard & Analytics System</p>", unsafe_allow_html=True)

# TOP KPI ROW (High-End UI)
if not filtered.empty:
    avg_val = filtered['sum_grid_power'].mean() if 'sum_grid_power' in filtered else 0
    max_val = filtered['sum_grid_power'].max() if 'sum_grid_power' in filtered else 0
    savings = (filtered['sum_grid_power'].sum() / 60) * cost_per_unit if 'sum_grid_power' in filtered else 0
    factory_load = filtered['daily_factory_kwh'].sum() if 'daily_factory_kwh' in filtered else 0
    
    k1, k2, k3, k4 = st.columns(4)
    def kpi(col, label, val):
        col.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>{label}</div>
            <div class='metric-value'>{val}</div>
        </div>""", unsafe_allow_html=True)
        
    kpi(k1, "Avg Solar", f"{avg_val:.1f} kW")
    kpi(k2, "Peak Solar", f"{max_val:.1f} kW")
    kpi(k3, "Est. Savings", f"R {savings:,.0f}")
    kpi(k4, "Factory Load", f"{factory_load:,.0f} kWh")

st.markdown("---")

# CHART FUNCTION (Preserved features from Code 1)
def plot_chart(df, x, y, title, color):
    if df.empty or y not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No Data", showarrow=False, font=dict(color=theme['text']))
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color, width=2.5)))
        # Expected Power Logic
        if 'expected_power_kw' in df.columns and "Actual" in title:
            fig.add_trace(go.Scatter(x=df[x], y=df['expected_power_kw'], name="Expected", 
                                     line=dict(color="gray", width=2, dash="dot")))
    fig.update_layout(
        template=theme['chart'],
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=420,
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode='x unified',
        title=dict(text=title, font=dict(color=theme['text'], size=18))
    )
    return fig

# TABS NAVIGATION
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Solar", "Generator", "Factory", "Kehua", "Billing"])

with tab1:
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.plotly_chart(plot_chart(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "#00C853"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Fuel Consumption")
        st.plotly_chart(plot_chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel (L)", "#FF3B30"), use_container_width=True)
    with c2:
        st.subheader("Runtime Duration")
        st.plotly_chart(plot_chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (h)", "#AF52DE"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Factory Daily Load")
    st.plotly_chart(plot_chart(filtered, 'last_changed', 'daily_factory_kwh', "Daily kWh", "#007AFF"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Kehua Internal Power")
    st.plotly_chart(plot_chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Power (kW)", "#5856D6"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab5:
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Billing Editor")
    
    # EXACT BILLING LOGIC PRESERVED FROM CODE 1
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
    except Exception as e:
        st.error(f"Could not load billing file: {e}")
        ws = None

    if ws:
        c1, c2 = st.columns(2)
        with c1:
            b2 = ws['B2'].value or "30/09/25"
            from_date = st.date_input("From Date", value=datetime.strptime(b2, "%d/%m/%y").date())
            c7 = st.number_input("Freedom Village (C7)", value=float(ws['C7'].value or 0))
            c9 = st.number_input("Boerdery (C9)", value=float(ws['C9'].value or 0))
            e9 = st.number_input("Boerdery Cost (E9)", value=float(ws['E9'].value or 0))
        with c2:
            to_date = st.date_input("To Date", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
            g21 = st.number_input("Drakenstein (G21)", value=float(ws['G21'].value or 0))
        
        st.markdown("---")
        st.markdown("**Boerdery Subunits**")
        sc1, sc2, sc3 = st.columns(3)
        with sc1: c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
        with sc2: c11 = st.number_input("Pomp, Willie (C11)", value=float(ws['C11'].value or 0))
        with sc3: c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

        if st.button("Generate Invoice", type="primary"):
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
                "Download Excel",
                st.session_state.edited,
                file_name=f"Invoice_{from_date.strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    st.markdown("</div>", unsafe_allow_html=True)
