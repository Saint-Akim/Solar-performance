import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import io
import openpyxl
from datetime import datetime, timedelta
import concurrent.futures

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & "WORLD CLASS" CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Durr Bottling Energy Intelligence", 
    page_icon="⚡", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

def apply_world_class_theme():
    # This injects a high-end Glassmorphism theme and hides Streamlit branding
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
            
            /* GLOBAL RESET */
            .stApp {
                background-color: #0f172a; /* Deep Slate */
                font-family: 'Inter', sans-serif;
                color: #e2e8f0;
            }
            
            /* HIDE DEFAULT CHROME */
            #MainMenu, footer, header {visibility: hidden;}
            
            /* SIDEBAR */
            section[data-testid="stSidebar"] {
                background-color: #1e293b;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
            }
            
            /* TYPOGRAPHY */
            h1, h2, h3 {
                color: #f8fafc !important;
                font-weight: 800 !important;
                letter-spacing: -0.5px;
            }
            
            /* GLASSMORPHISM CARD COMPONENT */
            .metric-card {
                background: linear-gradient(145deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.6));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                backdrop-filter: blur(10px);
                margin-bottom: 16px;
                transition: transform 0.2s ease;
            }
            .metric-card:hover {
                transform: translateY(-2px);
                border-color: rgba(56, 189, 248, 0.4);
            }
            .metric-label {
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #94a3b8;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .metric-value {
                font-size: 1.8rem;
                font-weight: 800;
                background: linear-gradient(to right, #ffffff, #cbd5e1);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .metric-sub {
                font-size: 0.85rem;
                margin-top: 8px;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            /* CHART CONTAINER */
            .chart-box {
                background: rgba(30, 41, 59, 0.4);
                border-radius: 16px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                margin-top: 20px;
            }
            
            /* TABS */
            .stTabs [data-baseweb="tab-list"] { gap: 8px; }
            .stTabs [data-baseweb="tab"] {
                background-color: rgba(255,255,255,0.03);
                border-radius: 8px;
                color: #94a3b8;
                padding: 10px 20px;
                border: 1px solid transparent;
            }
            .stTabs [data-baseweb="tab"][aria-selected="true"] {
                background-color: rgba(56, 189, 248, 0.1); /* Cyan tint */
                border: 1px solid rgba(56, 189, 248, 0.3);
                color: #38bdf8;
            }
        </style>
    """, unsafe_allow_html=True)

def render_metric(label, value, sub_text=None, color="neutral"):
    """Renders a custom HTML metric card"""
    color_map = {"positive": "#4ade80", "negative": "#f87171", "neutral": "#94a3b8", "cyan": "#38bdf8"}
    c = color_map.get(color, "#94a3b8")
    
    sub_html = f"<span style='color:{c}'>●</span> {sub_text}" if sub_text else ""
    
    html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub_html}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA LOADING ENGINE
# -----------------------------------------------------------------------------

# Fixed URLs (Ensuring Capitalization Matches GitHub)
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

# Excel Files
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
FUEL_PURCHASE_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Durr%20bottling%20Generator%20filling.xlsx"

def clean_home_assistant_data(df):
    """Pivots Home Assistant long-format data (Entity, State, Time) to wide-format"""
    try:
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce')
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            return df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        return df
    except Exception:
        return df

def fetch_csv(url):
    """Robust CSV Fetcher"""
    try:
        s = requests.get(url, timeout=10).content
        df = pd.read_csv(io.StringIO(s.decode('utf-8')))
        return clean_home_assistant_data(df)
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner="Loading Intelligence Engine...")
def load_all_data():
    csv_urls = SOLAR_URLS + [GEN_URL, FACTORY_URL, KEHUA_URL, HISTORY_URL]
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_csv, csv_urls))
    
    # 1. Solar (Combine 5 months)
    solar_raw = results[:len(SOLAR_URLS)]
    valid_solar = [df for df in solar_raw if not df.empty]
    solar_df = pd.concat(valid_solar, ignore_index=True) if valid_solar else pd.DataFrame()
    
    # 2. Other Systems
    gen_df = results[len(SOLAR_URLS)]
    factory_df = results[len(SOLAR_URLS)+1]
    kehua_df = results[len(SOLAR_URLS)+2]
    history_df = results[-1]
    
    return solar_df, gen_df, factory_df, kehua_df, history_df

# -----------------------------------------------------------------------------
# 3. ENGINEERING LOGIC (The "Brains")
# -----------------------------------------------------------------------------

@st.cache_data
def load_fuel_purchases():
    try:
        resp = requests.get(FUEL_PURCHASE_URL, timeout=10)
        df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0)
        
        # Robust Date Parsing for Excel Serial Dates
        def parse_date(x):
            if isinstance(x, (int, float)): return datetime(1899, 12, 30) + timedelta(days=x)
            return pd.to_datetime(x, errors='coerce')
            
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        df['date'] = df['date'].apply(parse_date)
        df = df.dropna(subset=['date'])
        
        rename = {'amount(liters)': 'liters', 'price_per_litre': 'price_per_l', 'cost(rands)': 'cost_r'}
        df.rename(columns=rename, inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def process_generator_engineering(gen_df, prices_df, default_price):
    if gen_df.empty: return pd.DataFrame(), {}
    
    df = gen_df.copy()
    df.columns = df.columns.str.lower()
    
    # Dynamic Column Detection
    try:
        time_col = [c for c in df.columns if 'time' in c or 'last_changed' in c][0]
        fuel_col = [c for c in df.columns if 'fuel' in c and 'l' in c][0]
        run_col = [c for c in df.columns if 'run' in c and 'h' in c][0]
    except IndexError: return pd.DataFrame(), {}

    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(time_col)
    
    # --- ENGINEERING FIX: SENSOR SMOOTHING ---
    # Fix: Added min_periods=1 to prevent data loss at start/end of streams
    df['fuel_smooth'] = df[fuel_col].rolling(window=5, center=True, min_periods=1).median().fillna(df[fuel_col])
    
    # Calculate Deltas
    # Usage = Negative Difference. Refueling = Positive Difference (ignored here)
    df['fuel_used_l'] = -df['fuel_smooth'].diff().clip(upper=0) 
    df['runtime_used_h'] = df[run_col].diff().clip(lower=0)
    
    # Daily Aggregation
    daily = df.resample('D', on=time_col).agg({'fuel_used_l':'sum', 'runtime_used_h':'sum'}).reset_index()
    
    # Financials
    daily['month'] = daily[time_col].dt.to_period('M').dt.to_timestamp()
    daily = daily.merge(prices_df, on='month', how='left')
    daily['price'] = daily['price'].fillna(default_price)
    daily['cost'] = daily['fuel_used_l'] * daily['price']
    
    # --- ENGINEERING FIX: EFFICIENCY CALCULATION ---
    # 
    # Correct: Sum of Total Fuel / Sum of Total Hours.
    total_fuel = daily['fuel_used_l'].sum()
    total_run = daily['runtime_used_h'].sum()
    
    avg_lph = (total_fuel / total_run) if total_run > 0 else 0
    
    totals = {
        'cost': daily['cost'].sum(),
        'fuel': total_fuel,
        'hours': total_run,
        'lph': avg_lph
    }
    
    # Daily L/h for charts only
    daily['lph_chart'] = daily.apply(lambda x: x['fuel_used_l']/x['runtime_used_h'] if x['runtime_used_h'] > 0.1 else 0, axis=1)
    
    return daily, totals

# -----------------------------------------------------------------------------
# 4. MAIN APP EXECUTION
# -----------------------------------------------------------------------------

# A. Init & Sidebar
apply_world_class_theme()
solar_df, gen_df, factory_df, kehua_df, history_df = load_all_data()

with st.sidebar:
    st.markdown("## ⚡ Durr Bottling")
    st.markdown("### Controls")
    
    # Date Picker
    preset = st.selectbox("Timeframe", ["Last 7 Days", "Last 30 Days", "Year to Date", "Custom"])
    today = datetime.today().date()
    
    if preset == "Last 7 Days":
        start_date, end_date = today - timedelta(days=6), today
    elif preset == "Last 30 Days":
        start_date, end_date = today - timedelta(days=29), today
    elif preset == "Year to Date":
        start_date, end_date = datetime(today.year, 1, 1).date(), today
    else:
        start_date = st.date_input("From", datetime(2025, 1, 1))
        end_date = st.date_input("To", today)

# B. Fuel Pricing Logic
fuel_purchases = load_fuel_purchases()

# Fix: Dynamic Year Detection to prevent code breaking in 2026+
current_year = datetime.now().year
monthly_prices = pd.DataFrame({'month': pd.date_range(f'{current_year}-01-01', f'{current_year}-12-01', freq='MS'), 'price': 22.50})

if not fuel_purchases.empty:
    fp = fuel_purchases.copy()
    fp['month'] = fp['date'].dt.to_period('M').dt.to_timestamp()
    monthly_agg = fp.groupby('month').apply(lambda x: pd.Series({'p': x['cost_r'].sum()/x['liters'].sum()})).reset_index()
    monthly_prices = pd.merge(monthly_prices, monthly_agg, on='month', how='left')
    monthly_prices['price'] = monthly_prices['p'].fillna(monthly_prices['price']).ffill().bfill()

current_price = monthly_prices['price'].iloc[-1]

# C. Process Data
gen_daily, gen_totals = process_generator_engineering(gen_df, monthly_prices, current_price)

# Filter Logic
if not gen_daily.empty:
    mask_gen = (gen_daily[gen_daily.columns[0]].dt.date >= start_date) & (gen_daily[gen_daily.columns[0]].dt.date <= end_date)
    gen_filtered = gen_daily[mask_gen].copy()
    
    # Recalculate totals for filtered range
    f_fuel = gen_filtered['fuel_used_l'].sum()
    f_run = gen_filtered['runtime_used_h'].sum()
    f_totals = {
        'cost': gen_filtered['cost'].sum(),
        'fuel': f_fuel,
        'hours': f_run,
        'lph': (f_fuel/f_run) if f_run > 0 else 0
    }
else:
    gen_filtered = pd.DataFrame()
    f_totals = {}

# -----------------------------------------------------------------------------
# 5. UI TABS
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["🔌 Generator", "☀️ Solar", "🏭 Factory", "📄 Billing"])

# === GENERATOR TAB ===
with tab1:
    if f_totals:
        # 1. KPI Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_metric("Total Cost", f"R {f_totals['cost']:,.0f}", "Est. Spend", "neutral")
        with c2: render_metric("Fuel Used", f"{f_totals['fuel']:.1f} L", "Diesel", "cyan")
        with c3: render_metric("Runtime", f"{f_totals['hours']:.1f} h", "Hours Run", "neutral")
        with c4: 
            eff_color = "positive" if f_totals['lph'] < 4.0 else "negative"
            render_metric("Efficiency", f"{f_totals['lph']:.2f} L/h", "Target: <4.0", eff_color)
            
        # 2. Main Chart
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        fig = px.bar(gen_filtered, x=gen_filtered.columns[0], y='fuel_used_l', 
                     title="Daily Fuel Consumption", color_discrete_sequence=['#38bdf8'])
        
        # Overlay Efficiency Line
        fig.add_scatter(x=gen_filtered[gen_filtered.columns[0]], y=gen_filtered['lph_chart']*10, 
                        mode='lines', name='Efficiency (Scaled x10)', 
                        line=dict(color='#f97316', width=3, shape='spline'))
        
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", family="Inter"),
            hovermode="x unified",
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    else:
        st.info("No generator data available for this period.")

# === SOLAR TAB ===
with tab2:
    if not solar_df.empty:
        solar_df['last_changed'] = pd.to_datetime(solar_df['last_changed'])
        mask_sol = (solar_df['last_changed'].dt.date >= start_date) & (solar_df['last_changed'].dt.date <= end_date)
        sol_f = solar_df[mask_sol].copy()
        
        if not sol_f.empty:
            # Combine Inverters
            sol_f['total_kw'] = (sol_f.get('sensor.goodwe_grid_power', 0) + sol_f.get('sensor.fronius_grid_power', 0)) / 1000
            
            # Metrics
            c1, c2 = st.columns(2)
            with c1: render_metric("Peak Power", f"{sol_f['total_kw'].max():.1f} kW", "Max Output", "cyan")
            with c2: render_metric("Data Points", f"{len(sol_f):,}", "Telemetry", "neutral")
            
            # Area Chart
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            fig = px.area(sol_f, x='last_changed', y='total_kw', title="Total Solar Output",
                          color_discrete_sequence=['#4ade80'])
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8", family="Inter"),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No solar data in this date range.")
    else:
        st.error("Could not load solar data. Check GitHub URLs.")

# === FACTORY TAB ===
with tab3:
    if not factory_df.empty:
        factory_df['last_changed'] = pd.to_datetime(factory_df['last_changed'])
        f_fac = factory_df[(factory_df['last_changed'].dt.date >= start_date) & (factory_df['last_changed'].dt.date <= end_date)].copy()
        
        if 'sensor.bottling_factory_monthkwhtotal' in f_fac.columns:
            f_fac = f_fac.sort_values('last_changed')
            f_fac['daily_kwh'] = f_fac['sensor.bottling_factory_monthkwhtotal'].diff().clip(lower=0)
            
            render_metric("Total Consumption", f"{f_fac['daily_kwh'].sum():,.0f} kWh", "Factory Load", "cyan")
            
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            fig = px.bar(f_fac, x='last_changed', y='daily_kwh', title="Factory Energy (kWh)", 
                         color_discrete_sequence=['#60a5fa'])
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8", family="Inter"),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# === BILLING TAB ===
with tab4:
    st.markdown("### 📝 Invoice Generator")
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        inv_start = st.date_input("Invoice Start", value=datetime(2025, 9, 1))
        unit_c7 = st.number_input("Freedom Village (Units)", value=0.0)
    with col2:
        inv_end = st.date_input("Invoice End", value=datetime(2025, 9, 30))
        unit_c9 = st.number_input("Boerdery (Units)", value=0.0)
        
    if st.button("Generate Excel Invoice", type="primary"):
        try:
            r = requests.get(BILLING_URL)
            wb = openpyxl.load_workbook(io.BytesIO(r.content))
            ws = wb.active
            
            # Correctly write Date objects (not strings) so Excel formulas work
            ws['B2'] = inv_start
            ws['B3'] = inv_end
            ws['C7'] = unit_c7
            ws['C9'] = unit_c9
            
            out = io.BytesIO()
            wb.save(out)
            out.seek(0)
            
            st.download_button(
                "📥 Download .xlsx", data=out, 
                file_name=f"Invoice_{inv_start.strftime('%b_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Invoice generated!")
        except Exception as e:
            st.error(f"Error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8rem;'>System v3.0 | Durr Bottling Electrical Intelligence</div>", unsafe_allow_html=True)
