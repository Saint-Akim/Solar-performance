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
# 1. VISUAL DESIGN SYSTEM (WORLD-CLASS UI)
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
            .stApp { background-color: var(--bg-color); color: var(--text-color); font-family: 'Inter', sans-serif; }
            #MainMenu, footer, header {visibility: hidden;}
            section[data-testid="stSidebar"] { background-color: var(--card-bg); border-right: 1px solid #334155; }
            h1, h2, h3 { color: #f8fafc; font-weight: 600; letter-spacing: -0.02em; }
            .stTabs [data-baseweb="tab"] { background-color: rgba(255,255,255,0.03); border-radius: 8px; color: var(--text-muted); }
            .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); color: var(--accent-cyan); }
        </style>
    """, unsafe_allow_html=True)

def render_metric(label, value, delta=None, color="neutral"):
    colors = {"positive": "#4ade80", "negative": "#f87171", "cyan": "#38bdf8", "neutral": "#94a3b8"}
    c = colors.get(color, colors["neutral"])
    delta_html = f"<div style='color:{c}; font-size:0.85rem; margin-top:6px; font-weight:500;'>{delta}</div>" if delta else ""
    st.markdown(f"""
    <div style="background: linear-gradient(145deg, rgba(30,41,59,0.7), rgba(15,23,42,0.6));
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
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']})

apply_design_system()

# ==============================================================================
# 2. DATA SOURCES - CORRECTED SOLAR CSV NAMES + XLSX FOR GENERATOR
# ==============================================================================
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe&Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe&Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe&Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe&Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe&Fronius_may.csv"
]
GEN_XLSX_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).xlsx"
FUEL_LEVEL_XLSX_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/history%20(5).xlsx"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
FUEL_PURCHASE_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Durr%20bottling%20Generator%20filling.xlsx"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"

def fetch_xlsx(url, sheet_name=0):
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return pd.read_excel(io.BytesIO(resp.content), sheet_name=sheet_name)
    except Exception as e:
        st.warning(f"Error loading XLSX {url}: {e}")
        return pd.DataFrame()

def fetch_csv(url):
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return pd.read_csv(io.StringIO(resp.text))
    except Exception as e:
        st.warning(f"Error loading CSV {url}: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner="Loading Intelligence Engine...")
def load_data():
    # Solar CSVs - now with correct filenames (typos fixed where present)
    solar_dfs = []
    for u in SOLAR_URLS:
        df = fetch_csv(u)
        if not df.empty:
            solar_dfs.append(df)
    solar_df = pd.concat(solar_dfs, ignore_index=True) if solar_dfs else pd.DataFrame()
    
    # Generator XLSX files
    gen_df = fetch_xlsx(GEN_XLSX_URL)
    fuel_level_df = fetch_xlsx(FUEL_LEVEL_XLSX_URL)
    
    # Factory
    factory_df = fetch_csv(FACTORY_URL)
    
    return solar_df, gen_df, fuel_level_df, factory_df

solar_df, gen_df, fuel_level_df, factory_df = load_data()

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
# 3. ADVANCED GENERATOR CALCULATIONS USING XLSX DATA
# ==============================================================================
@st.cache_data
def process_generator_advanced(gen_df, fuel_level_df, fuel_purchases):
    data_frames = []

    # 1. From gen (2).xlsx - cumulative fuel consumed + runtime
    if not gen_df.empty:
        # Adjust column names if needed - common variations
        fuel_col = next((c for c in gen_df.columns if 'fuel_consumed' in str(c).lower()), None)
        run_col = next((c for c in gen_df.columns if 'runtime' in str(c).lower()), None)
        time_col = next((c for c in gen_df.columns if 'last_changed' in str(c).lower() or 'time' in str(c).lower()), None)
        if fuel_col and time_col:
            temp = gen_df[[time_col, fuel_col]]
            if run_col:
                temp = gen_df[[time_col, fuel_col, run_col]]
                temp.rename(columns={run_col: 'run_cum'}, inplace=True)
            temp.rename(columns={time_col: 'time', fuel_col: 'fuel_cum'}, inplace=True)
            temp['time'] = pd.to_datetime(temp['time'])
            temp = temp.sort_values('time')
            temp['fuel_delta'] = temp['fuel_cum'].diff().clip(lower=0).fillna(0)
            temp['run_delta'] = temp.get('run_cum', 0).diff().clip(lower=0).fillna(0)
            data_frames.append(temp[['time', 'fuel_delta', 'run_delta']])

    # 2. From history (5).xlsx - fuel level sensor
    if not fuel_level_df.empty:
        level_cols = [col for col in fuel_level_df.columns if 'fuel_level' in str(col).lower()]
        time_col = next((c for c in fuel_level_df.columns if 'last_changed' in str(c).lower() or 'time' in str(c).lower()), None)
        if level_cols and time_col:
            temp = fuel_level_df[[time_col] + level_cols].copy()
            temp[time_col] = pd.to_datetime(temp[time_col])
            temp = temp.sort_values(time_col)
            level_col = level_cols[0]
            temp['level_smooth'] = temp[level_col].rolling(window=5, center=True, min_periods=1).median()
            temp['fuel_delta'] = -temp['level_smooth'].diff().clip(upper=0).fillna(0)
            temp['run_delta'] = 0  # No runtime in this file
            temp.rename(columns={time_col: 'time'}, inplace=True)
            data_frames.append(temp[['time', 'fuel_delta', 'run_delta']])

    if not data_frames:
        return pd.DataFrame(), {}

    # Combine all sources
    combined = pd.concat(data_frames, ignore_index=True)
    combined = combined.sort_values('time').reset_index(drop=True)

    # Daily aggregation
    daily = combined.resample('D', on='time').sum(numeric_only=True).reset_index()
    daily.rename(columns={'fuel_delta': 'liters', 'run_delta': 'hours'}, inplace=True)

    # Pricing
    if not fuel_purchases.empty:
        prices = fuel_purchases.set_index('date')['price_per_l'].resample('D').ffill()
        daily = daily.merge(prices.to_frame(), left_on='date', right_index=True, how='left')
        daily['price_per_l'] = daily['price_per_l'].fillna(method='bfill').fillna(22.50)
    else:
        daily['price_per_l'] = 22.50

    daily['cost'] = daily['liters'] * daily['price_per_l']

    total_l = daily['liters'].sum()
    total_h = daily['hours'].sum()
    avg_lph = total_l / total_h if total_h > 0 else 0

    totals = {
        'cost': daily['cost'].sum(),
        'liters': total_l,
        'hours': total_h,
        'lph': avg_lph
    }

    return daily, totals

daily_gen, gen_totals = process_generator_advanced(gen_df, fuel_level_df, fuel_purchases)

# ==============================================================================
# 4. SIDEBAR & DATE FILTERING
# ==============================================================================
with st.sidebar:
    st.title("⚡ Durr Bottling")
    st.caption("Energy Intelligence v4.1 – Fixed Solar URLs + XLSX")
    st.markdown("---")
    
    st.subheader("Date Range")
    preset = st.selectbox("Quick Select", ["Last 7 Days", "Last 30 Days", "Year to Date", "Custom"])
    today = datetime.today().date()
    
    if preset == "Last 7 Days":
        start_date = today - timedelta(days=6)
    elif preset == "Last 30 Days":
        start_date = today - timedelta(days=29)
    elif preset == "Year to Date":
        start_date = datetime(today.year, 1, 1).date()
    else:
        start_date = st.date_input("From", datetime(2025, 1, 1))
    
    end_date = st.date_input("To", today) if preset == "Custom" else today

# Filter generator data
if not daily_gen.empty:
    mask = (daily_gen['date'].dt.date >= start_date) & (daily_gen['date'].dt.date <= end_date)
    filtered_gen = daily_gen[mask].copy()
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

# ==============================================================================
# 5. TABS & DASHBOARD
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs(["🔌 Generator", "☀️ Solar", "🏭 Factory", "📄 Billing"])

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
        plot_interactive_chart(filtered_gen, 'date', 'cost', "Daily Fuel Cost", color="#f87171", kind='bar', y_label="Rands")
    else:
        st.info("No generator data available for this period (check XLSX files).")

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
            st.warning("No solar data in selected range.")
    else:
        st.info("Solar data partially loaded (some monthly files may have typos in names). Available months will still show.")

with tab3:
    st.markdown("### 🏭 Factory Load")
    if not factory_df.empty:
        factory_df['last_changed'] = pd.to_datetime(factory_df['last_changed'])
        f_mask = (factory_df['last_changed'].dt.date >= start_date) & (factory_df['last_changed'].dt.date <= end_date)
        f_filt = factory_df[f_mask].copy().sort_values('last_changed')
        if 'sensor.bottling_factory_monthkwhtotal' in f_filt.columns:
            f_filt['daily_kwh'] = f_filt['sensor.bottling_factory_monthkwhtotal'].diff().clip(lower=0).fillna(0)
            render_metric("Total Consumption", f"{f_filt['daily_kwh'].sum():,.0f} kWh", "Factory Energy", "cyan")
            plot_interactive_chart(f_filt, 'last_changed', 'daily_kwh', "Factory Energy (kWh)", color="#60a5fa", kind='bar', y_label="kWh")
        else:
            st.info("Factory kWh sensor not found in data.")
    else:
        st.info("No factory data available.")

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

st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8rem;'>v4.1 – Fixed Solar URLs + Robust XLSX Handling | Durr Bottling Electrical Intelligence</div>", unsafe_allow_html=True)
