import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import io
import openpyxl
from datetime import datetime, timedelta
import concurrent.futures

# ==============================================================================
# 1. VISUAL DESIGN SYSTEM (THE "WORLD CLASS" LOOK)
# ==============================================================================
st.set_page_config(
    page_title="Durr Bottling Energy Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)
def apply_design_system():
    st.markdown("""
        <style>
            /* Import Inter Font */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            :root {
                --bg-color: #0f172a;
                --card-bg: #1e293b;
                --text-color: #e2e8f0;
                --text-muted: #94a3b8;
                --accent-cyan: #38bdf8;
                --accent-green: #4ade80;
                --accent-red: #f87171;
            }
            /* Global Reset */
            .stApp {
                background-color: var(--bg-color);
                color: var(--text-color);
                font-family: 'Inter', sans-serif;
            }
            /* Hide Streamlit Chrome */
            #MainMenu, footer, header {visibility: hidden;}
           
            /* Sidebar */
            section[data-testid="stSidebar"] {
                background-color: var(--card-bg);
                border-right: 1px solid #334155;
            }
            /* Typography */
            h1, h2, h3 { color: #f8fafc; font-weight: 600; letter-spacing: -0.02em; }
            p, label { color: var(--text-muted); }
           
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] { gap: 8px; }
            .stTabs [data-baseweb="tab"] {
                background-color: rgba(255,255,255,0.03);
                border-radius: 8px;
                color: var(--text-muted);
                border: 1px solid transparent;
            }
            .stTabs [data-baseweb="tab"][aria-selected="true"] {
                background-color: rgba(56, 189, 248, 0.1);
                border: 1px solid rgba(56, 189, 248, 0.3);
                color: var(--accent-cyan);
            }
        </style>
    """, unsafe_allow_html=True)
def render_metric(label, value, delta=None, color="neutral"):
    """Renders a Glassmorphism Metric Card"""
    colors = {
        "positive": "#4ade80", "negative": "#f87171",
        "cyan": "#38bdf8", "neutral": "#94a3b8"
    }
    c = colors.get(color, colors["neutral"])
    delta_html = f"<div style='color:{c}; font-size:0.85rem; margin-top:6px; font-weight:500;'>{delta}</div>" if delta else ""
    st.markdown(f"""
    <div style="
        background: linear-gradient(145deg, rgba(30,41,59,0.7), rgba(15,23,42,0.6));
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">{label}</div>
        <div style="font-size: 1.8rem; font-weight: 700; color: #f1f5f9; margin-top: 4px;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
def plot_interactive_chart(df, x_col, y_col, title, color="#38bdf8", kind='bar', y_label="Value"):
    """Renders a minimalist, zoomable Plotly chart"""
    if df.empty:
        st.info("No data available for chart.")
        return
    if kind == 'bar':
        trace = go.Bar(x=df[x_col], y=df[y_col], marker_color=color, name=y_label)
    elif kind == 'line':
        trace = go.Scatter(x=df[x_col], y=df[y_col], mode='lines', line=dict(color=color, width=3), name=y_label)
    elif kind == 'area':
        trace = go.Scatter(x=df[x_col], y=df[y_col], fill='tozeroy', mode='lines', line=dict(color=color, width=2), name=y_label)
   
    layout = go.Layout(
        title=dict(text=title, font=dict(size=16, color="#f8fafc", family="Inter")),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter", color="#94a3b8"),
        height=400,
        hovermode="x unified",
        xaxis=dict(showgrid=False, linecolor="#334155", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False, title=y_label),
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False
    )
   
    fig = go.Figure(data=[trace], layout=layout)
    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': True, 'scrollZoom': True,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
    })
apply_design_system()
# ==============================================================================
# 2. DATA ENGINE
# ==============================================================================
# Corrected URLs (Fixed typos like Sloar -> Solar)
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_May.csv"
]
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
HISTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/history.csv"
FUEL_PURCHASE_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Durr%20bottling%20Generator%20filling.xlsx"
FUEL_LEVEL_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/history%20(5).csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
def fetch_csv(url):
    try:
        s = requests.get(url, timeout=10).content
        df = pd.read_csv(io.StringIO(s.decode('utf-8')))
        # Home Assistant Pivot Logic
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce')
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            return df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        # For gen, state to numeric
        if 'state' in df.columns:
            df['state'] = pd.to_numeric(df['state'], errors='coerce')
        return df
    except: return pd.DataFrame()
@st.cache_data(show_spinner="Loading Intelligence Engine...")
def load_data():
    urls = SOLAR_URLS + [GEN_URL, FACTORY_URL, KEHUA_URL, HISTORY_URL, FUEL_LEVEL_URL]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_csv, urls))
   
    solar_df = pd.concat([r for r in results[:len(SOLAR_URLS)] if not r.empty], ignore_index=True) if any(not r.empty for r in results[:len(SOLAR_URLS)]) else pd.DataFrame()
    gen_df = results[len(SOLAR_URLS)]
    factory_df = results[len(SOLAR_URLS)+1]
    kehua_df = results[len(SOLAR_URLS)+2]
    history_df = results[len(SOLAR_URLS)+3]
    fuel_level_df = results[-1]
   
    return solar_df, gen_df, factory_df, kehua_df, history_df, fuel_level_df
solar_df, gen_df, factory_df, kehua_df, history_df, fuel_level_df = load_data()
@st.cache_data
def load_fuel_purchases():
    try:
        resp = requests.get(FUEL_PURCHASE_URL)
        df = pd.read_excel(io.BytesIO(resp.content))
        df.columns = df.columns.str.lower().str.replace(' ', '_')
       
        def parse_date(x):
            if isinstance(x, (int, float)): return datetime(1899, 12, 30) + timedelta(days=x)
            return pd.to_datetime(x, errors='coerce')
           
        df['date'] = df['date'].apply(parse_date)
        df = df.dropna(subset=['date'])
        df.rename(columns={'amount(liters)':'liters', 'price_per_litre':'price_per_l', 'cost(rands)':'cost_r'}, inplace=True)
        return df
    except: return pd.DataFrame()
fuel_purchases = load_fuel_purchases()
# ==============================================================================
# 3. ENGINEERING LOGIC (ALGORITHMS A, B, C)
# ==============================================================================
@st.cache_data
def process_generator_advanced(gen_df, fuel_level_df, fuel_purchases):
    # 1. MERGE & CLEAN
    # We prefer the specific 'fuel_consumed' sensor if available, else derive from level
    data = pd.DataFrame()
   
    # Logic for Gen 2 (Cumulative Sensor)
    if not gen_df.empty and 'sensor.generator_fuel_consumed' in gen_df.columns:
        temp = gen_df[['last_changed', 'sensor.generator_fuel_consumed', 'sensor.generator_runtime_duration']].copy()
        temp.columns = ['time', 'fuel_cum', 'run_cum']
        temp = temp.sort_values('time')
        # Calculate diffs
        temp['fuel_delta'] = temp['fuel_cum'].diff().clip(lower=0)
        temp['run_delta'] = temp['run_cum'].diff().clip(lower=0)
        data = temp
       
    # Logic for History 5 (Fuel Level) - Use if Gen 2 is empty or as backup
    elif not fuel_level_df.empty:
        temp = fuel_level_df[['last_changed', 'sensor.generator_fuel_level']].copy()
        temp.columns = ['time', 'level']
        temp = temp.sort_values('time')
        # ROLLING MEDIAN FILTER (Anti-Slosh Algorithm)
        temp['level_smooth'] = temp['level'].rolling(window=5, center=True, min_periods=1).median()
        # Drops in level = consumption
        temp['fuel_delta'] = -temp['level_smooth'].diff().clip(upper=0)
        # Runtime derived: if fuel dropped, we assume it ran for that interval
        temp['run_delta'] = temp['fuel_delta'].apply(lambda x: 0.16 if x > 0.1 else 0) # Approx 10 mins
        data = temp
    if data.empty: return pd.DataFrame(), {}
    # 2. DAILY AGGREGATION
    daily = data.resample('D', on='time').agg({
        'fuel_delta': 'sum',
        'run_delta': 'sum'
    }).reset_index()
    daily.rename(columns={'time': 'date', 'fuel_delta': 'liters', 'run_delta': 'hours'}, inplace=True)
   
    # 3. DYNAMIC PRICING (Algorithm C)
    if not fuel_purchases.empty:
        # Create a price map (forward fill from purchase date)
        prices = fuel_purchases.set_index('date').resample('D').ffill()['price_per_l']
        daily['price'] = daily['date'].map(prices).fillna(method='bfill').fillna(22.50)
    else:
        daily['price'] = 22.50
       
    daily['cost'] = daily['liters'] * daily['price']
   
    # 4. WEIGHTED EFFICIENCY (Algorithm B)
    total_l = daily['liters'].sum()
    total_h = daily['hours'].sum()
    avg_lph = (total_l / total_h) if total_h > 0 else 0
   
    totals = {
        'cost': daily['cost'].sum(),
        'liters': total_l,
        'hours': total_h,
        'lph': avg_lph
    }
   
    return daily, totals
daily_gen, gen_totals = process_generator_advanced(gen_df, fuel_level_df, fuel_purchases)
# ==============================================================================
# 4. MAIN APP LAYOUT
# ==============================================================================
with st.sidebar:
    st.title("⚡ Durr Bottling")
    st.caption("Energy Intelligence v3.0")
    st.markdown("---")
   
    st.subheader("Date Range")
    preset = st.selectbox("Quick Select", ["Last 7 Days", "Last 30 Days", "Year to Date", "Custom"])
    today = datetime.today().date()
   
    if preset == "Last 7 Days": start_date = today - timedelta(days=6)
    elif preset == "Last 30 Days": start_date = today - timedelta(days=29)
    elif preset == "Year to Date": start_date = datetime(today.year, 1, 1).date()
    else: start_date = st.date_input("From", datetime(2025, 1, 1))
   
    end_date = st.date_input("To", today) if preset == "Custom" else today
# Filtering
if not daily_gen.empty:
    mask = (daily_gen['date'].dt.date >= start_date) & (daily_gen['date'].dt.date <= end_date)
    filtered_gen = daily_gen[mask].copy()
   
    # Recalculate totals for filter
    f_l = filtered_gen['liters'].sum()
    f_h = filtered_gen['hours'].sum()
    f_totals = {
        'cost': filtered_gen['cost'].sum(),
        'liters': f_l,
        'hours': f_h,
        'lph': (f_l / f_h) if f_h > 0 else 0
    }
else:
    filtered_gen = pd.DataFrame()
    f_totals = {}
# TABS
tab1, tab2, tab3, tab4 = st.tabs(["🔌 Generator", "☀️ Solar", "🏭 Factory", "📄 Billing"])
# --- GENERATOR TAB ---
with tab1:
    st.markdown("### 🔌 Generator Overview")
    if f_totals:
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_metric("Total Cost", f"R {f_totals['cost']:,.0f}", "Est. Period Cost", "neutral")
        with c2: render_metric("Fuel Used", f"{f_totals['liters']:.1f} L", "Diesel Volume", "cyan")
        with c3: render_metric("Runtime", f"{f_totals['hours']:.1f} hrs", "Total Duration", "neutral")
        with c4:
            eff_color = "positive" if f_totals['lph'] < 4.0 else "negative"
            render_metric("Efficiency", f"{f_totals['lph']:.2f} L/h", "Target: < 4.0", eff_color)
           
        st.markdown("---")
        plot_interactive_chart(filtered_gen, 'date', 'liters', "Daily Fuel Consumption", color="#38bdf8", kind='bar', y_label="Liters")
    else:
        st.info("No generator data available for this period.")
# --- SOLAR TAB ---
with tab2:
    st.markdown("### ☀️ Solar Performance")
    if not solar_df.empty:
        solar_df['last_changed'] = pd.to_datetime(solar_df['last_changed'])
        s_mask = (solar_df['last_changed'].dt.date >= start_date) & (solar_df['last_changed'].dt.date <= end_date)
        s_filt = solar_df[s_mask].copy()
       
        if not s_filt.empty:
            s_filt['total_kw'] = (s_filt.get('sensor.goodwe_grid_power', 0) + s_filt.get('sensor.fronius_grid_power', 0)) / 1000
           
            c1, c2 = st.columns(2)
            with c1: render_metric("Peak Power", f"{s_filt['total_kw'].max():.1f} kW", "Max Output", "positive")
            with c2: render_metric("Data Points", f"{len(s_filt):,}", "Telemetry", "neutral")
           
            plot_interactive_chart(s_filt, 'last_changed', 'total_kw', "Total Solar Output (kW)", color="#4ade80", kind='area', y_label="kW")
        else:
            st.warning("No solar data in range.")
    else:
        st.error("Solar data could not be loaded.")
# --- FACTORY TAB ---
with tab3:
    st.markdown("### 🏭 Factory Load")
    if not factory_df.empty:
        factory_df['last_changed'] = pd.to_datetime(factory_df['last_changed'])
        f_mask = (factory_df['last_changed'].dt.date >= start_date) & (factory_df['last_changed'].dt.date <= end_date)
        f_filt = factory_df[f_mask].copy().sort_values('last_changed')
       
        if 'sensor.bottling_factory_monthkwhtotal' in f_filt.columns:
            f_filt['daily_kwh'] = f_filt['sensor.bottling_factory_monthkwhtotal'].diff().clip(lower=0)
            render_metric("Total Consumption", f"{f_filt['daily_kwh'].sum():,.0f} kWh", "Factory Energy", "cyan")
            plot_interactive_chart(f_filt, 'last_changed', 'daily_kwh', "Factory Energy (kWh)", color="#60a5fa", kind='bar', y_label="kWh")
    else:
        st.info("No factory data available.")
# --- BILLING TAB ---
with tab4:
    st.markdown("### 📝 Invoice Generator")
    c1, c2 = st.columns(2)
    with c1:
        inv_start = st.date_input("Start Date", value=datetime(2025, 9, 1))
        unit_c7 = st.number_input("Freedom Village Units", value=0.0)
    with c2:
        inv_end = st.date_input("End Date", value=datetime(2025, 9, 30))
        unit_c9 = st.number_input("Boerdery Units", value=0.0)
       
    if st.button("Generate Invoice", type="primary"):
        try:
            r = requests.get(BILLING_URL)
            wb = openpyxl.load_workbook(io.BytesIO(r.content))
            ws = wb.active
            ws['B2'] = inv_start
            ws['B3'] = inv_end
            ws['C7'] = unit_c7
            ws['C9'] = unit_c9
           
            out = io.BytesIO()
            wb.save(out)
            out.seek(0)
           
            st.download_button("Download .xlsx", out, f"Invoice_{inv_start.strftime('%b_%Y')}.xlsx")
            st.success("Generated!")
        except Exception as e: st.error(f"Error: {e}")
# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8rem;'>System v5.0 | Durr Bottling Electrical Intelligence</div>", unsafe_allow_html=True)
