import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
import concurrent.futures
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Southern Paarl Energy",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# -----------------------------------------------------------------------------
# 2. ADVANCED CSS & THEME ENGINE
# -----------------------------------------------------------------------------
# Theme Variables
if st.session_state.theme == 'dark':
    theme = {
        "bg": "#0e1117",
        "sidebar": "#161b22",
        "card": "#1e212b",
        "text": "#ffffff",
        "subtext": "#9ca3af",
        "border": "1px solid rgba(255, 255, 255, 0.1)",
        "accent": "#00C853",
        "input": "rgba(255,255,255,0.05)",
        "chart_theme": "plotly_dark"
    }
else:
    theme = {
        "bg": "#f3f4f6",
        "sidebar": "#ffffff",
        "card": "#ffffff",
        "text": "#111827",
        "subtext": "#6b7280",
        "border": "1px solid rgba(0,0,0,0.06)",
        "accent": "#2563eb",
        "input": "#ffffff",
        "chart_theme": "plotly_white"
    }

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* BASE STYLES */
    .stApp {{
        background-color: {theme['bg']};
        font-family: 'Inter', sans-serif;
        color: {theme['text']};
    }}
    
    /* REMOVE PADDING */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}

    /* SIDEBAR */
    [data-testid="stSidebar"] {{
        background-color: {theme['sidebar']};
        border-right: {theme['border']};
    }}
    [data-testid="stSidebar"] * {{
        color: {theme['text']} !important;
    }}

    /* CARDS */
    .metric-card {{
        background-color: {theme['card']};
        border: {theme['border']};
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        display: flex;
        flex-direction: column;
        height: 100%;
        transition: transform 0.2s;
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }}
    
    /* ICONS IN CARDS */
    .icon-box {{
        width: 40px;
        height: 40px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        margin-bottom: 12px;
    }}

    /* TYPOGRAPHY */
    .metric-label {{
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        color: {theme['subtext']};
        margin-bottom: 4px;
    }}
    .metric-value {{
        font-size: 28px;
        font-weight: 700;
        color: {theme['text']};
        letter-spacing: -0.5px;
    }}

    /* INPUTS (Fixed Visibility) */
    .stDateInput input, .stNumberInput input, .stTextInput input, .stSelectbox div {{
        background-color: {theme['input']} !important;
        border: {theme['border']} !important;
        color: {theme['text']} !important;
        border-radius: 8px !important;
    }}

    /* TABS (Segmented Control Look) */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
        padding-bottom: 10px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {theme['card']};
        border: {theme['border']};
        border-radius: 8px;
        padding: 8px 20px;
        height: auto;
        font-weight: 600;
        color: {theme['subtext']};
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background-color: {theme['accent']};
        color: white !important;
        border-color: {theme['accent']};
    }}

    /* HIDE JUNK */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. FAST DATA LOADING
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
        try:
            w_df = pd.read_csv(WEATHER_URL)
            w_df['period_end'] = pd.to_datetime(w_df['period_end'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        except: w_df = pd.DataFrame()
        s_dfs = [f.result() for f in s_futures if not f.result().empty]
        solar = pd.concat(s_dfs, ignore_index=True) if s_dfs else pd.DataFrame()
        return solar, gen_fut.result(), fac_fut.result(), keh_fut.result(), w_df

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 10px 0 20px 0;">
        <h2 style="margin:0; font-size:20px; color:{theme['text']};">Durr Bottling</h2>
        <p style="margin:0; font-size:12px; color:{theme['subtext']};">Energy Management System</p>
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
    st.markdown("### ⚙️ Parameters")
    gti_factor = st.slider("GTI Factor", 0.50, 1.50, 1.00, 0.01)
    pr_ratio = st.slider("PR Ratio", 0.50, 1.00, 0.80, 0.01)
    cost_per_unit = st.number_input("Cost (ZAR/kWh)", min_value=0.0, value=2.98, step=0.01)
    
    st.markdown("### 📅 Date Filter")
    start_date = st.date_input("From", datetime(2025, 5, 1))
    end_date = st.date_input("To", datetime(2025, 5, 31))

# -----------------------------------------------------------------------------
# 5. LOGIC & PROCESSING
# -----------------------------------------------------------------------------
with st.spinner("Synchronizing..."):
    solar_df, gen_df, factory_df, kehua_df, weather_df = load_data_parallel()

if not weather_df.empty:
    weather_df['expected_power_kw'] = weather_df['gti'] * gti_factor * TOTAL_CAPACITY_KW * pr_ratio / 1000

if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
merged = pd.DataFrame()
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(col),
                               left_on='last_changed', right_on=col, direction='nearest')

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
# 6. DASHBOARD UI
# -----------------------------------------------------------------------------
st.markdown(f"<h1 style='margin-bottom:10px;'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:{theme['subtext']}; margin-bottom:30px;'>Real-time production and consumption overview.</p>", unsafe_allow_html=True)

if not filtered.empty:
    # 6A. METRIC CARDS WITH ICONS
    avg_val = filtered['sum_grid_power'].mean() if 'sum_grid_power' in filtered else 0
    max_val = filtered['sum_grid_power'].max() if 'sum_grid_power' in filtered else 0
    savings = (filtered['sum_grid_power'].sum() / 60) * cost_per_unit if 'sum_grid_power' in filtered else 0
    factory_load = filtered['daily_factory_kwh'].sum() if 'daily_factory_kwh' in filtered else 0
    
    k1, k2, k3, k4 = st.columns(4)
    
    def metric_box(col, label, value, icon, icon_bg):
        col.markdown(f"""
        <div class="metric-card">
            <div class="icon-box" style="background-color: {icon_bg}; color: white;">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    metric_box(k1, "Est. Savings", f"R {savings:,.0f}", "💰", "#10B981")
    metric_box(k2, "Avg Solar", f"{avg_val:.1f} kW", "☀️", "#F59E0B")
    metric_box(k3, "Factory Load", f"{factory_load:,.0f} kWh", "🏭", "#3B82F6")
    metric_box(k4, "Peak Output", f"{max_val:.1f} kW", "⚡", "#6366F1")

st.markdown("<br>", unsafe_allow_html=True)

# 6B. CHARTING FUNCTION
def clean_chart(df, x, y, title, color):
    if df.empty or y not in df.columns: return st.info("No data available.")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name="Actual", line=dict(color=color, width=3), fill='tozeroy', fillcolor=f"rgba{color[3:-1]}, 0.1)"))
    
    if 'expected_power_kw' in df.columns and "Solar" in title:
        fig.add_trace(go.Scatter(x=df[x], y=df['expected_power_kw'], name="Expected", line=dict(color="#A0A0A0", width=2, dash="dot")))

    fig.update_layout(
        template=theme['chart_theme'],
        title=dict(text=title, font=dict(size=18, family="Inter", color=theme['text'])),
        height=450,
        margin=dict(l=0, r=0, t=50, b=0),
        xaxis=dict(showgrid=False, color=theme['subtext']),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.1)", color=theme['subtext']),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

# 6C. TABS
t1, t2, t3, t4, t5 = st.tabs(["Solar Analysis", "Generator", "Factory Load", "Kehua Power", "Billing Invoices"])

with t1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    clean_chart(filtered, 'last_changed', 'sum_grid_power', "Solar Output vs Expected (kW)", "#F59E0B")
    st.markdown("</div>", unsafe_allow_html=True)

with t2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: clean_chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel Consumption (L)", "#EF4444")
    with c2: clean_chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime Duration (h)", "#8B5CF6")
    st.markdown("</div>", unsafe_allow_html=True)

with t3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    clean_chart(filtered, 'last_changed', 'daily_factory_kwh', "Daily Factory Consumption (kWh)", "#3B82F6")
    st.markdown("</div>", unsafe_allow_html=True)

with t4:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    clean_chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Kehua Internal Load (kW)", "#06B6D4")
    st.markdown("</div>", unsafe_allow_html=True)

with t5:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.subheader("🧾 Invoice Editor")
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
        
        c1, c2 = st.columns(2)
        with c1:
            b2 = ws['B2'].value or "30/09/25"
            from_date = st.date_input("From Date", value=datetime.strptime(b2, "%d/%m/%y").date())
            v_c7 = st.number_input("Freedom Village (Unit 7)", value=float(ws['C7'].value or 0))
            v_c9 = st.number_input("Boerdery (Unit 9)", value=float(ws['C9'].value or 0))
            v_e9 = st.number_input("Boerdery Cost (R)", value=float(ws['E9'].value or 0))
        with c2:
            to_date = st.date_input("To Date", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
            v_g21 = st.number_input("Drakenstein (G21)", value=float(ws['G21'].value or 0))
            
        st.markdown("**Sub-Units**")
        s1, s2, s3 = st.columns(3)
        with s1: v_c10 = st.number_input("Johan & Stoor", value=float(ws['C10'].value or 0))
        with s2: v_c11 = st.number_input("Pomp & Willie", value=float(ws['C11'].value or 0))
        with s3: v_c12 = st.number_input("Werkers", value=float(ws['C12'].value or 0))

        if st.button("Generate & Download Invoice", type="primary"):
            ws['A1'].value = from_date.strftime("%b'%y")
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['B4'].value = (to_date - from_date).days
            ws['C7'].value = v_c7; ws['C9'].value = v_c9; ws['E9'].value = v_e9
            ws['C10'].value = v_c10; ws['C11'].value = v_c11; ws['C12'].value = v_c12
            ws['G21'].value = v_g21
            ws['E7'] = '=C7*D7' # Re-inject formula
            
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.success("Invoice generated successfully!")
            st.download_button("Download Excel File", buf, f"Invoice_{from_date}.xlsx")
            
    except Exception as e:
        st.error(f"Billing System Error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)
    
st.toast("System Synced & Ready", icon="✅")
