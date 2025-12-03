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
# 2. UI DESIGN SYSTEM (CSS)
# -----------------------------------------------------------------------------
# Define Theme Colors
if st.session_state.theme == 'dark':
    theme = {
        "bg": "#0e1117",
        "card": "#1e212b",
        "text": "#ffffff",
        "subtext": "#a0a0a0",
        "border": "1px solid rgba(255, 255, 255, 0.1)",
        "chart": "plotly_dark",
        "accent": "#00C853"
    }
else:
    theme = {
        "bg": "#f8f9fb",
        "card": "#ffffff",
        "text": "#1d1d1f",
        "subtext": "#86868b",
        "border": "1px solid rgba(0, 0, 0, 0.08)",
        "chart": "plotly_white",
        "accent": "#007AFF"
    }

st.markdown(f"""
<style>
    /* Global App Background */
    .stApp {{
        background-color: {theme['bg']};
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    
    /* Inputs Fix (Readable text in both modes) */
    .stDateInput input, .stNumberInput input, .stTextInput input, .stSelectbox div {{
        color: {theme['text']} !important;
    }}
    
    /* Card Design */
    .energy-card {{
        background-color: {theme['card']};
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: {theme['border']};
        margin-bottom: 20px;
    }}
    
    /* Metric Typography */
    .metric-label {{
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        color: {theme['subtext']};
        letter-spacing: 0.5px;
    }}
    .metric-value {{
        font-size: 28px;
        font-weight: 700;
        color: {theme['text']};
        margin-top: 5px;
    }}
    
    /* Headers */
    h1, h2, h3 {{ color: {theme['text']} !important; }}
    
    /* Remove Streamlit Bloat */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. SIDEBAR
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

# -----------------------------------------------------------------------------
# 4. DATA LOGIC (STRICTLY PRESERVED)
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

# Execute Load
solar_df = load_csvs(SOLAR_URLS)
weather_df = load_weather(gti_factor, pr_ratio)
gen_df = load_csvs([GEN_URL])
factory_df = load_csvs([FACTORY_URL])
kehua_df = load_csvs([KEHUA_URL])

# Factory Diff Logic
if not factory_df.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_df.columns:
    factory_df = factory_df.sort_values('last_changed')
    factory_df['daily_factory_kwh'] = factory_df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)

# Merge Logic (As requested)
all_dfs = [df for df in [solar_df, gen_df, factory_df, kehua_df, weather_df] if not df.empty]
if all_dfs:
    merged = all_dfs[0].copy()
    for df in all_dfs[1:]:
        col = 'last_changed' if 'last_changed' in df.columns else 'period_end'
        merged = pd.merge_asof(merged.sort_values('last_changed'), df.sort_values(col),
                               left_on='last_changed', right_on=col, direction='nearest')
else:
    merged = pd.DataFrame()

# Calculation Logic
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
# 5. UI COMPONENTS & CHARTS
# -----------------------------------------------------------------------------
def plot_chart(df, x, y, title, color):
    # Dynamic Plotly Template
    if df.empty or y not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No Data", showarrow=False, font=dict(color=theme['text']))
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color, width=2.5)))
        
        # Original Logic: Expected Power Line
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

# -----------------------------------------------------------------------------
# 6. MAIN LAYOUT
# -----------------------------------------------------------------------------
st.title("Southern Paarl Energy")
st.markdown(f"<p style='color:{theme['subtext']}; margin-top:-15px'>Dashboard & Analytics System</p>", unsafe_allow_html=True)

# TABS NAVIGATION
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Solar", "Generator", "Factory", "Kehua", "Billing"])

with tab1:
    if not filtered.empty:
        # KPI ROW
        avg_val = filtered['sum_grid_power'].mean()
        max_val = filtered['sum_grid_power'].max()
        savings = (filtered['sum_grid_power'].sum() / 60) * cost_per_unit
        
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='energy-card'><div class='metric-label'>Avg Output</div><div class='metric-value'>{avg_val:.2f} kW</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='energy-card'><div class='metric-label'>Peak Output</div><div class='metric-value'>{max_val:.2f} kW</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='energy-card'><div class='metric-label'>Est. Savings</div><div class='metric-value'>R {savings:,.2f}</div></div>", unsafe_allow_html=True)
        
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
    
    # Original Billing Logic Preserved
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
