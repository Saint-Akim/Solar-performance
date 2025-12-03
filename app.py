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

# -----------------------------------------------------------------------------
# 2. ADVANCED STYLING SYSTEM (CSS)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* 1. FONT IMPORT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    /* 2. GLOBAL RESET */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* 3. DYNAMIC THEME COLORS */
    /* Light Mode Defaults */
    :root {
        --card-bg: #ffffff;
        --text-color: #1a1c23;
        --sub-text: #6b7280;
        --accent: #2563eb;
        --border: #e5e7eb;
        --input-bg: #f3f4f6;
    }

    /* Dark Mode Overrides (Streamlit handles class injection) */
    @media (prefers-color-scheme: dark) {
        :root {
            --card-bg: #1f2937;
            --text-color: #f9fafb;
            --sub-text: #9ca3af;
            --accent: #3b82f6;
            --border: #374151;
            --input-bg: #111827;
        }
    }

    /* 4. COMPONENT STYLING */
    
    /* Cards */
    .metric-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: var(--accent);
    }
    
    /* Typography */
    .metric-label {
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--sub-text);
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-color);
        letter-spacing: -0.025em;
    }
    
    /* Inputs (The Fix for "Invisible Text") */
    .stDateInput input, .stNumberInput input, .stTextInput input, .stSelectbox div {
        background-color: var(--input-bg) !important;
        color: var(--text-color) !important;
        border-color: var(--border) !important;
        border-radius: 8px !important;
    }
    
    /* Hide Streamlit Clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 8px 16px;
        color: var(--sub-text);
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--accent);
        color: white;
        border-color: var(--accent);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. HIGH-SPEED DATA ENGINE (Concurrent Loading)
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
        # Standardize columns
        df.columns = df.columns.str.lower().str.strip()
        
        # Check if it's sensor data
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            return df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        
        # Check if it's weather data
        if 'period_end' in df.columns:
            df['period_end'] = pd.to_datetime(df['period_end'], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
            return df
            
        return df
    except: return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_all_data():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Launch all downloads simultaneously
        solar_futures = [executor.submit(fetch_clean_data, u) for u in SOLAR_URLS]
        gen_future = executor.submit(fetch_clean_data, GEN_URL)
        fac_future = executor.submit(fetch_clean_data, FACTORY_URL)
        keh_future = executor.submit(fetch_clean_data, KEHUA_URL)
        wea_future = executor.submit(fetch_clean_data, WEATHER_URL)
        
        # Gather results
        s_dfs = [f.result() for f in solar_futures if not f.result().empty]
        solar = pd.concat(s_dfs, ignore_index=True) if s_dfs else pd.DataFrame()
        
        return solar, gen_future.result(), fac_future.result(), keh_future.result(), wea_future.result()

# -----------------------------------------------------------------------------
# 4. SIDEBAR NAVIGATION & SETTINGS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 20px;'>
            <div style='background: #2563eb; width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;'>DB</div>
            <div>
                <div style='font-weight: 700; font-size: 16px;'>Durr Bottling</div>
                <div style='font-size: 12px; opacity: 0.7;'>Energy Manager</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🛠️ Configuration")
    gti_factor = st.slider("GTI Factor", 0.5, 1.5, 1.00, 0.01)
    pr_ratio = st.slider("PR Ratio", 0.5, 1.0, 0.80, 0.01)
    cost_per_unit = st.number_input("Cost (ZAR/kWh)", value=2.98, step=0.01)
    
    st.markdown("### 📅 Date Filter")
    start_date = st.date_input("Start Date", datetime(2025, 5, 1))
    end_date = st.date_input("End Date", datetime(2025, 5, 31))
    
    st.markdown("---")
    st.caption(f"System Status: ● Online\nv3.0 Professional")

# -----------------------------------------------------------------------------
# 5. DATA PROCESSING ENGINE (Preserving Logic)
# -----------------------------------------------------------------------------
with st.spinner("Synchronizing with Energy Database..."):
    solar_df, gen_df, factory_df, kehua_df, weather_df = load_all_data()

# Logic: Calculate Expected Power
if not weather_df.empty:
    weather_df['expected_power_kw'] = weather_df['gti'] * gti_factor * TOTAL_CAPACITY_KW * pr_ratio / 1000

# Logic: Calculate Factory Daily Load
if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

# Logic: Merge All Datasets
dfs_to_merge = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
merged = pd.DataFrame()

if dfs_to_merge:
    merged = dfs_to_merge[0].copy()
    for df in dfs_to_merge[1:]:
        # Determine time column name
        time_col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        target_col = 'last_changed' if 'last_changed' in merged.columns else 'period_end'
        
        merged = pd.merge_asof(
            merged.sort_values(target_col),
            df.sort_values(time_col),
            left_on=target_col,
            right_on=time_col,
            direction='nearest'
        )

# Logic: Total Solar Calculation
if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns: merged['sensor.fronius_grid_power'] /= 1000
    if 'sensor.goodwe_grid_power' in merged.columns: merged['sensor.goodwe_grid_power'] /= 1000
    merged['total_solar'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

# Filter by Date
filtered = pd.DataFrame()
if not merged.empty:
    time_col = 'last_changed' if 'last_changed' in merged.columns else 'period_end'
    mask = (merged[time_col] >= pd.to_datetime(start_date)) & (merged[time_col] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged.loc[mask].copy()

# -----------------------------------------------------------------------------
# 6. DASHBOARD UI
# -----------------------------------------------------------------------------
st.title("Energy Overview")

# A. KPI CARDS
if not filtered.empty:
    k1, k2, k3, k4 = st.columns(4)
    
    # KPIs
    solar_kwh = (filtered['total_solar'].sum() / 4) # approx kWh (15 min intervals assumed or simple sum)
    savings = (filtered['total_solar'].sum() / 60) * cost_per_unit # Logic from previous code
    fuel = filtered['sensor.generator_fuel_consumed'].max() - filtered['sensor.generator_fuel_consumed'].min() if 'sensor.generator_fuel_consumed' in filtered else 0
    factory_load = filtered['daily_factory_kwh'].sum() if 'daily_factory_kwh' in filtered else 0

    def card(col, label, value, subtext):
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div style="font-size:12px; color:grey; margin-top:4px;">{subtext}</div>
        </div>
        """, unsafe_allow_html=True)

    card(k1, "Est. Savings", f"R {savings:,.0f}", "Based on current cost/unit")
    card(k2, "Avg Solar Output", f"{filtered['total_solar'].mean():.1f} kW", "Real-time generation")
    card(k3, "Generator Fuel", f"{fuel:.0f} L", "Total consumption")
    card(k4, "Factory Load", f"{factory_load:,.0f} kWh", "Total energy demand")

st.markdown("<br>", unsafe_allow_html=True)

# B. MAIN TABS
tabs = st.tabs(["☀️ Solar Analysis", "⛽ Generator", "🏭 Factory", "🔋 Kehua", "📝 Billing"])

def plot_line(df, x, y, title, color, show_expected=False):
    if df.empty or y not in df.columns: return st.warning("No data available for this period.")
    
    fig = go.Figure()
    # Main Line
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name="Actual", line=dict(color=color, width=3), fill='tozeroy', fillcolor=f"rgba{color[3:-1]}, 0.1)"))
    
    # Expected Line
    if show_expected and 'expected_power_kw' in df.columns:
        fig.add_trace(go.Scatter(x=df[x], y=df['expected_power_kw'], name="Expected", line=dict(color="#9ca3af", width=2, dash="dot")))
        
    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        template="plotly_white",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#f3f4f6"),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)

with tabs[0]: # Solar
    plot_line(filtered, 'last_changed', 'total_solar', 'Solar Output (kW)', 'rgb(37, 99, 235)', show_expected=True)

with tabs[1]: # Generator
    c1, c2 = st.columns(2)
    with c1: plot_line(filtered, 'last_changed', 'sensor.generator_fuel_consumed', 'Fuel (Litres)', 'rgb(220, 38, 38)')
    with c2: plot_line(filtered, 'last_changed', 'sensor.generator_runtime_duration', 'Runtime (Hours)', 'rgb(147, 51, 234)')

with tabs[2]: # Factory
    plot_line(filtered, 'last_changed', 'daily_factory_kwh', 'Factory Consumption (kWh)', 'rgb(5, 150, 105)')

with tabs[3]: # Kehua
    plot_line(filtered, 'last_changed', 'sensor.kehua_internal_power', 'Kehua Internal Load (kW)', 'rgb(8, 145, 178)')

with tabs[4]: # Billing
    st.markdown("### 🧾 Invoice Generator")
    
    try:
        resp = requests.get(BILLING_URL)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
        
        # Layout for Billing Inputs
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Freedom Village**")
            v_c7 = st.number_input("Unit 7 Reading", value=float(ws['C7'].value or 0))
        with c2:
            st.markdown("**Boerdery Main**")
            v_c9 = st.number_input("Unit 9 Reading", value=float(ws['C9'].value or 0))
            v_e9 = st.number_input("Cost (R)", value=float(ws['E9'].value or 0))
        with c3:
            st.markdown("**Drakenstein**")
            v_g21 = st.number_input("G21 Reading", value=float(ws['G21'].value or 0))
            
        st.markdown("**Sub-Units**")
        s1, s2, s3 = st.columns(3)
        with s1: v_c10 = st.number_input("Johan & Stoor", value=float(ws['C10'].value or 0))
        with s2: v_c11 = st.number_input("Pomp & Willie", value=float(ws['C11'].value or 0))
        with s3: v_c12 = st.number_input("Werkers", value=float(ws['C12'].value or 0))

        if st.button("🔄 Generate & Download Invoice", type="primary"):
            # Update Logic (Preserved)
            ws['A1'].value = start_date.strftime("%b'%y")
            ws['B2'].value = start_date.strftime("%d/%m/%y")
            ws['B3'].value = end_date.strftime("%d/%m/%y")
            ws['B4'].value = (end_date - start_date).days
            
            ws['C7'].value = v_c7
            ws['C9'].value = v_c9; ws['E9'].value = v_e9
            ws['C10'].value = v_c10; ws['C11'].value = v_c11; ws['C12'].value = v_c12
            ws['G21'].value = v_g21
            
            # Save
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            
            st.success("Invoice Generated Successfully!")
            st.download_button("📥 Download Excel File", buf, f"Invoice_{start_date}.xlsx")
            
    except Exception as e:
        st.error(f"Billing Module Error: {e}")
