import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
# 2. FUELSA DESIGN SYSTEM (CSS)
# -----------------------------------------------------------------------------
# FuelSA uses a very specific "Utility" look: High contrast, white cards, distinct headers.
if st.session_state.theme == 'dark':
    theme = {
        "bg": "#121212",
        "card": "#1E1E1E",
        "text": "#E0E0E0",
        "label": "#A0A0A0",
        "border": "1px solid #333",
        "header_bg": "#2C2C2C",
        "accent": "#F59E0B" # Orange/Gold used in fuel apps
    }
else:
    theme = {
        "bg": "#F4F7F6",
        "card": "#FFFFFF",
        "text": "#2C3E50",
        "label": "#7F8C8D",
        "border": "1px solid #E3E7E8",
        "header_bg": "#ECF0F1",
        "accent": "#2980B9" # FuelSA Blue
    }

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    
    .stApp {{
        background-color: {theme['bg']};
        font-family: 'Roboto', sans-serif;
        color: {theme['text']};
    }}

    /* SIDEBAR - Clean Utility Style */
    [data-testid="stSidebar"] {{
        background-color: {theme['card']};
        border-right: {theme['border']};
    }}
    [data-testid="stSidebar"] * {{
        color: {theme['text']} !important;
    }}

    /* FUELSA STYLE CARDS */
    .fuel-card {{
        background-color: {theme['card']};
        border: {theme['border']};
        border-radius: 4px; /* Sharper corners like FuelSA */
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        overflow: hidden;
    }}
    
    .fuel-header {{
        background-color: {theme['header_bg']};
        padding: 12px 20px;
        border-bottom: {theme['border']};
        font-weight: 700;
        font-size: 16px;
        color: {theme['text']};
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    
    .fuel-body {{
        padding: 20px;
    }}

    /* DATA ROWS (The "Unleaded 95" look) */
    .data-row {{
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px dashed {theme['border'].replace('solid', 'dashed')};
        font-size: 14px;
    }}
    .data-row:last-child {{
        border-bottom: none;
    }}
    .data-label {{
        color: {theme['label']};
        font-weight: 500;
    }}
    .data-value {{
        color: {theme['text']};
        font-weight: 700;
    }}

    /* INPUTS */
    .stDateInput input, .stNumberInput input, .stSelectbox div {{
        background-color: {theme['bg']} !important;
        border: {theme['border']} !important;
        color: {theme['text']} !important;
        border-radius: 4px !important;
    }}

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px;
        background-color: transparent;
        border-bottom: 2px solid {theme['header_bg']};
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent;
        border: none;
        color: {theme['label']};
        font-weight: 700;
        text-transform: uppercase;
        font-size: 13px;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: {theme['accent']};
        border-bottom: 2px solid {theme['accent']};
        background-color: transparent;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. DATA ENGINE (UNCHANGED LOGIC)
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

def fetch_clean_data(url):
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
        s_futures = [executor.submit(fetch_clean_data, u) for u in SOLAR_URLS]
        gen_fut = executor.submit(fetch_clean_data, GEN_URL)
        fac_fut = executor.submit(fetch_clean_data, FACTORY_URL)
        keh_fut = executor.submit(fetch_clean_data, KEHUA_URL)
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
        <h3 style="margin:0; font-weight:700; color:{theme['text']};">Fuel SA Client</h3>
        <p style="margin:0; font-size:12px; color:{theme['label']};">Energy Edition • v2.0</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Theme
    col_t1, col_t2 = st.columns([0.7, 0.3])
    with col_t1: st.write("Dark Mode")
    with col_t2: 
        if st.toggle("Theme", value=(st.session_state.theme == 'dark'), label_visibility="collapsed"):
            st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
            st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Parameters")
    gti_factor = st.slider("GTI Factor", 0.5, 1.5, 1.00, 0.01)
    pr_ratio = st.slider("PR Ratio", 0.5, 1.0, 0.80, 0.01)
    cost_per_unit = st.number_input("Cost (R/kWh)", value=2.98, step=0.01)
    
    st.markdown("### 📅 Date Filter")
    start_date = st.date_input("From", datetime(2025, 5, 1))
    end_date = st.date_input("To", datetime(2025, 5, 31))

# -----------------------------------------------------------------------------
# 5. LOGIC
# -----------------------------------------------------------------------------
with st.spinner("Fetching FuelSA Data..."):
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
        t_col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        m_col = 'last_changed' if 'last_changed' in merged.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values(m_col), df.sort_values(t_col), left_on=m_col, right_on=t_col, direction='nearest')

if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns: merged['sensor.goodwe_grid_power'] /= 1000
    merged['total_solar'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

filtered = pd.DataFrame()
if not merged.empty:
    time_col = 'last_changed' if 'last_changed' in merged.columns else 'period_end'
    mask = (merged[time_col] >= pd.to_datetime(start_date)) & (merged[time_col] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged.loc[mask].copy()

# -----------------------------------------------------------------------------
# 6. DASHBOARD (FuelSA Layout)
# -----------------------------------------------------------------------------
st.title("Southern Paarl Energy")

if not filtered.empty:
    # Calculations
    solar_sum = filtered['total_solar'].mean() if 'total_solar' in filtered else 0
    max_solar = filtered['total_solar'].max() if 'total_solar' in filtered else 0
    savings = (filtered['total_solar'].sum() / 60) * cost_per_unit if 'total_solar' in filtered else 0
    
    fuel = filtered['sensor.generator_fuel_consumed'].max() - filtered['sensor.generator_fuel_consumed'].min() if 'sensor.generator_fuel_consumed' in filtered else 0
    runtime = filtered['sensor.generator_runtime_duration'].max() if 'sensor.generator_runtime_duration' in filtered else 0
    
    factory_kwh = filtered['daily_factory_kwh'].sum() if 'daily_factory_kwh' in filtered else 0
    kehua_load = filtered['sensor.kehua_internal_power'].mean() if 'sensor.kehua_internal_power' in filtered else 0

    # --- THE FUELSA "PRICE BOARD" LAYOUT ---
    
    c1, c2 = st.columns(2)
    
    # CARD 1: SOLAR (Mimics "Petrol")
    with c1:
        st.markdown(f"""
        <div class="fuel-card">
            <div class="fuel-header">
                <span>SOLAR OUTPUT</span>
                <span style="color:{theme['accent']}">Live</span>
            </div>
            <div class="fuel-body">
                <div class="data-row">
                    <span class="data-label">Average Generation</span>
                    <span class="data-value">{solar_sum:.2f} kW</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Peak Output</span>
                    <span class="data-value">{max_solar:.2f} kW</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Est. Savings</span>
                    <span class="data-value" style="color:#27ae60">R {savings:,.2f}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # CARD 2: GENERATOR (Mimics "Diesel")
    with c2:
        st.markdown(f"""
        <div class="fuel-card">
            <div class="fuel-header">
                <span>GENERATOR STATUS</span>
                <span style="color:#E74C3C">Standby</span>
            </div>
            <div class="fuel-body">
                <div class="data-row">
                    <span class="data-label">Diesel Consumed</span>
                    <span class="data-value">{fuel:.1f} Litres</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Total Runtime</span>
                    <span class="data-value">{runtime:.1f} Hours</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Factory Load</span>
                    <span class="data-value">{factory_kwh:,.0f} kWh</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- TABS & CHARTS ---
    tabs = st.tabs(["Solar Graph", "Generator", "Factory", "Kehua", "Billing"])

    def fuel_chart(df, x, y, title, color):
        if df.empty or y not in df.columns: return st.info("No Data")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x], y=df[y], mode='lines', line=dict(color=color, width=2.5), name="Actual"))
        
        if 'expected_power_kw' in df.columns and "Solar" in title:
            fig.add_trace(go.Scatter(x=df[x], y=df['expected_power_kw'], name="Expected", line=dict(color="#BDC3C7", width=2, dash="dot")))

        fig.update_layout(
            template="plotly_white" if st.session_state.theme == 'light' else "plotly_dark",
            title=dict(text=title, font=dict(size=14, color=theme['label'])),
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor=theme['bg'])
        )
        st.plotly_chart(fig, use_container_width=True)

    with tabs[0]: # Solar
        fuel_chart(filtered, 'last_changed', 'total_solar', "Solar Output vs Forecast", theme['accent'])
    
    with tabs[1]: # Gen
        c_g1, c_g2 = st.columns(2)
        with c_g1: fuel_chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel (L)", "#E74C3C")
        with c_g2: fuel_chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (h)", "#9B59B6")

    with tabs[2]: # Factory
        fuel_chart(filtered, 'last_changed', 'daily_factory_kwh', "Factory Load (kWh)", "#2ECC71")

    with tabs[3]: # Kehua
        fuel_chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Kehua Internal (kW)", "#3498DB")

    with tabs[4]: # Billing
        st.markdown(f"<div class='fuel-card'><div class='fuel-header'><span>INVOICE GENERATOR</span></div><div class='fuel-body'>", unsafe_allow_html=True)
        try:
            resp = requests.get(BILLING_URL)
            wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
            ws = wb.active
            
            # Form Logic
            c1, c2 = st.columns(2)
            with c1:
                b2 = ws['B2'].value or "30/09/25"
                from_date = st.date_input("From Date", value=datetime.strptime(b2, "%d/%m/%y").date())
                v_c7 = st.number_input("Freedom Village (Unit 7)", value=float(ws['C7'].value or 0))
                v_c9 = st.number_input("Boerdery (Unit 9)", value=float(ws['C9'].value or 0))
            with c2:
                to_date = st.date_input("To Date", value=datetime.strptime(ws['B3'].value or "05/11/25", "%d/%m/%y").date())
                v_e9 = st.number_input("Boerdery Cost (R)", value=float(ws['E9'].value or 0))
                v_g21 = st.number_input("Drakenstein (G21)", value=float(ws['G21'].value or 0))
            
            st.markdown("---")
            s1, s2, s3 = st.columns(3)
            with s1: v_c10 = st.number_input("Johan & Stoor", value=float(ws['C10'].value or 0))
            with s2: v_c11 = st.number_input("Pomp & Willie", value=float(ws['C11'].value or 0))
            with s3: v_c12 = st.number_input("Werkers", value=float(ws['C12'].value or 0))

            if st.button("Generate Invoice", type="primary"):
                ws['A1'].value = from_date.strftime("%b'%y")
                ws['B2'].value = from_date.strftime("%d/%m/%y")
                ws['B3'].value = to_date.strftime("%d/%m/%y")
                ws['B4'].value = (to_date - from_date).days
                ws['C7'].value = v_c7; ws['C9'].value = v_c9; ws['E9'].value = v_e9
                ws['C10'].value = v_c10; ws['C11'].value = v_c11; ws['C12'].value = v_c12
                ws['G21'].value = v_g21
                
                buf = io.BytesIO()
                wb.save(buf)
                buf.seek(0)
                st.download_button("Download Excel", buf, f"Invoice_{from_date}.xlsx")

        except: st.error("Billing module unavailable")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("System Ready. Waiting for data sync...")
