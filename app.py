import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ==============================================================================
# 1. VISUAL DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="Durr Bottling Energy Intelligence", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

def apply_design_system():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            :root { --bg-color: #0f172a; --card-bg: #1e293b; --text-color: #e2e8f0; --text-muted: #94a3b8; --accent-cyan: #38bdf8; --accent-green: #4ade80; --accent-red: #f87171; }
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
        st.info("No data available for this chart.")
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
        height=450,
        hovermode="x unified",
        xaxis=dict(showgrid=False, linecolor="#334155", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False, title=y_label),
        margin=dict(l=40, r=20, t=60, b=40),
        showlegend=False
    )
   
    fig = go.Figure(data=[trace], layout=layout)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']})

apply_design_system()

# ==============================================================================
# 2. DATA SOURCES
# ==============================================================================
GEN_XLSX_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).xlsx"
FUEL_LEVEL_XLSX_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/history%20(5).xlsx"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
FUEL_PURCHASE_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Durr%20bottling%20Generator%20filling.xlsx"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"

SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe&Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe&Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe&Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe&Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe&Fronius_may.csv"
]

def fetch_xlsx(url):
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return pd.read_excel(io.BytesIO(resp.content))
    except Exception as e:
        st.warning(f"Failed to load XLSX {url}: {e}")
        return pd.DataFrame()

def fetch_csv(url):
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return pd.read_csv(io.StringIO(resp.text))
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner="Loading data from GitHub...")
def load_data():
    gen_df = fetch_xlsx(GEN_XLSX_URL)
    fuel_level_df = fetch_xlsx(FUEL_LEVEL_XLSX_URL)
    factory_df = fetch_csv(FACTORY_URL)
    
    solar_dfs = []
    for u in SOLAR_URLS:
        df = fetch_csv(u)
        if not df.empty:
            solar_dfs.append(df)
    solar_df = pd.concat(solar_dfs, ignore_index=True) if solar_dfs else pd.DataFrame()
    
    return solar_df, gen_df, fuel_level_df, factory_df

solar_df, gen_df, fuel_level_df, factory_df = load_data()

@st.cache_data
def load_fuel_purchases():
    try:
        resp = requests.get(FUEL_PURCHASE_URL)
        df = pd.read_excel(io.BytesIO(resp.content))
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        df.rename(columns={'amount(liters)':'liters', 'price_per_litre':'price_per_l', 'cost(rands)':'cost_r'}, inplace=True)
        return df
    except Exception as e:
        st.warning(f"Failed to load fuel purchases: {e}")
        return pd.DataFrame()

fuel_purchases = load_fuel_purchases()

# ==============================================================================
# 3. GENERATOR CALCULATIONS (USING BOTH XLSX FILES)
# ==============================================================================
@st.cache_data
def process_generator(gen_df, fuel_level_df, fuel_purchases):
    sources = []

    # From gen (2).xlsx - cumulative fuel consumed
    if not gen_df.empty:
        if 'entity_id' in gen_df.columns:
            fuel_gen = gen_df[gen_df['entity_id'] == 'sensor.generator_fuel_consumed'].copy()
        else:
            fuel_gen = gen_df.copy()
        if not fuel_gen.empty and 'state' in fuel_gen.columns and 'last_changed' in fuel_gen.columns:
            fuel_gen['last_changed'] = pd.to_datetime(fuel_gen['last_changed'])
            fuel_gen = fuel_gen.sort_values('last_changed')
            fuel_gen['state'] = pd.to_numeric(fuel_gen['state'], errors='coerce')
            fuel_gen = fuel_gen.dropna(subset=['state'])
            fuel_gen['fuel_delta'] = fuel_gen['state'].diff().clip(lower=0).fillna(0)
            sources.append(fuel_gen[['last_changed', 'fuel_delta']].rename(columns={'last_changed': 'time'}))

    # From history (5).xlsx - fuel level sensor
    if not fuel_level_df.empty:
        if 'entity_id' in fuel_level_df.columns:
            level_df = fuel_level_df[fuel_level_df['entity_id'].str.contains('fuel_level', case=False, na=False)].copy()
        else:
            level_df = fuel_level_df.copy()
        if not level_df.empty and 'state' in level_df.columns and 'last_changed' in level_df.columns:
            level_df['last_changed'] = pd.to_datetime(level_df['last_changed'])
            level_df = level_df.sort_values('last_changed')
            level_df['state'] = pd.to_numeric(level_df['state'], errors='coerce')
            level_df = level_df.dropna(subset=['state'])
            level_df['level_smooth'] = level_df['state'].rolling(5, min_periods=1, center=True).median()
            level_df['fuel_delta'] = -level_df['level_smooth'].diff().clip(upper=0).fillna(0)
            sources.append(level_df[['last_changed', 'fuel_delta']].rename(columns={'last_changed': 'time'}))

    if not sources:
        return pd.DataFrame(), {'cost': 0, 'liters': 0}

    # Combine and aggregate daily
    combined = pd.concat(sources)
    daily = combined.groupby(pd.Grouper(key='time', freq='D'))['fuel_delta'].sum().reset_index()
    daily.rename(columns={'time': 'date', 'fuel_delta': 'liters'}, inplace=True)

    # Apply pricing
    if not fuel_purchases.empty:
        prices = fuel_purchases.set_index('date')['price_per_l'].resample('D').ffill().bfill()
        daily = daily.merge(prices.to_frame(), left_on='date', right_index=True, how='left')
        daily['price_per_l'] = daily['price_per_l'].fillna(22.50)
    else:
        daily['price_per_l'] = 22.50

    daily['cost'] = daily['liters'] * daily['price_per_l']

    totals = {
        'cost': daily['cost'].sum(),
        'liters': daily['liters'].sum()
    }

    return daily, totals

daily_gen, gen_totals = process_generator(gen_df, fuel_level_df, fuel_purchases)

# ==============================================================================
# 4. SIDEBAR & DATE FILTERING
# ==============================================================================
with st.sidebar:
    st.title("⚡ Durr Bottling")
    st.caption("Energy Intelligence v5.0 – Complete Dashboard")
    st.markdown("---")
    
    st.subheader("Date Range")
    preset = st.selectbox("Quick Select", ["Last 30 Days", "Last 90 Days", "Year to Date", "Custom"])
    today = datetime(2025, 12, 16).date()
    
    if preset == "Last 30 Days":
        start_date = today - timedelta(days=29)
        end_date = today
    elif preset == "Last 90 Days":
        start_date = today - timedelta(days=89)
        end_date = today
    elif preset == "Year to Date":
        start_date = datetime(2025, 1, 1).date()
        end_date = today
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From", datetime(2025, 1, 1))
        with col2:
            end_date = st.date_input("To", today)
    
    if end_date < start_date:
        st.error("End date must be after start date")
        st.stop()

# Filter generator data
if not daily_gen.empty:
    filtered_gen = daily_gen[(daily_gen['date'].dt.date >= start_date) & (daily_gen['date'].dt.date <= end_date)].copy()
    f_gen_totals = {
        'cost': filtered_gen['cost'].sum(),
        'liters': filtered_gen['liters'].sum()
    }
else:
    filtered_gen = pd.DataFrame()
    f_gen_totals = {'cost': 0, 'liters': 0}

# ==============================================================================
# 5. COMPLETE DASHBOARD TABS
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs(["🔌 Generator Cost & Fuel", "☀️ Solar Performance", "🏭 Factory Load", "📄 Billing Editor"])

# ==================== GENERATOR TAB ====================
with tab1:
    st.markdown("## 🔌 Generator Performance Overview")
    st.caption("Fuel consumption and cost calculated from cumulative sensor + tank level cross-validation")
    
    if f_gen_totals['liters'] > 0:
        col1, col2 = st.columns(2)
        with col1:
            render_metric("Estimated Total Cost", f"R {f_gen_totals['cost']:,.0f}", "Using actual purchase prices", "neutral")
        with col2:
            render_metric("Total Fuel Used", f"{f_gen_totals['liters']:.1f} L", "Cross-validated from sensors", "cyan")
        
        st.markdown("### Daily Breakdown")
        col1, col2 = st.columns(2)
        with col1:
            plot_interactive_chart(filtered_gen, 'date', 'liters', "Daily Fuel Consumption", color="#38bdf8", kind='bar', y_label="Liters")
        with col2:
            plot_interactive_chart(filtered_gen, 'date', 'cost', "Daily Fuel Cost", color="#f87171", kind='bar', y_label="Rands")
    else:
        st.info("No generator fuel consumption recorded in the selected period.")

# ==================== SOLAR TAB ====================
with tab2:
    st.markdown("## ☀️ Solar Performance")
    if not solar_df.empty:
        solar_df['last_changed'] = pd.to_datetime(solar_df['last_changed'])
        solar_filtered = solar_df[(solar_df['last_changed'].dt.date >= start_date) & (solar_df['last_changed'].dt.date <= end_date)]
        
        if not solar_filtered.empty:
            solar_filtered['total_kw'] = (
                solar_filtered.get('sensor.goodwe_grid_power', 0) + 
                solar_filtered.get('sensor.fronius_grid_power', 0)
            ) / 1000
            
            peak = solar_filtered['total_kw'].max()
            total_points = len(solar_filtered)
            
            col1, col2 = st.columns(2)
            with col1:
                render_metric("Peak Output", f"{peak:.1f} kW", "Highest instantaneous power", "positive")
            with col2:
                render_metric("Data Points", f"{total_points:,}", "Telemetry records", "neutral")
            
            st.markdown("### Real-Time Solar Power")
            plot_interactive_chart(solar_filtered, 'last_changed', 'total_kw', "Solar Power Output Over Time", color="#4ade80", kind='area', y_label="kW")
            
            st.markdown("### Average Output by Hour of Day")
            solar_filtered['hour'] = solar_filtered['last_changed'].dt.hour
            hourly_avg = solar_filtered.groupby('hour')['total_kw'].mean().reset_index()
            plot_interactive_chart(hourly_avg, 'hour', 'total_kw', "Average Solar by Hour", color="#4ade80", kind='bar', y_label="kW")
        else:
            st.warning("No solar data available in the selected date range.")
    else:
        st.info("Solar data files could not be loaded or are empty.")

# ==================== FACTORY TAB ====================
with tab3:
    st.markdown("## 🏭 Factory Energy Consumption")
    if not factory_df.empty:
        factory_df['last_changed'] = pd.to_datetime(factory_df['last_changed'])
        factory_filtered = factory_df[(factory_df['last_changed'].dt.date >= start_date) & (factory_df['last_changed'].dt.date <= end_date)].copy()
        
        if not factory_filtered.empty and 'sensor.bottling_factory_monthkwhtotal' in factory_filtered.columns:
            factory_filtered = factory_filtered.sort_values('last_changed')
            factory_filtered['daily_kwh'] = factory_filtered['sensor.bottling_factory_monthkwhtotal'].diff().clip(lower=0).fillna(0)
            total_kwh = factory_filtered['daily_kwh'].sum()
            
            render_metric("Total Consumption", f"{total_kwh:,.0f} kWh", "Factory energy used in period", "cyan")
            
            plot_interactive_chart(factory_filtered, 'last_changed', 'daily_kwh', "Daily Factory Energy Consumption", color="#60a5fa", kind='bar', y_label="kWh")
        else:
            st.info("Factory cumulative kWh sensor not found or no data in range.")
    else:
        st.info("Factory data could not be loaded.")

# ==================== BILLING TAB ====================
with tab4:
    st.markdown("## 📄 September 2025 Invoice Editor")
    try:
        resp = requests.get(BILLING_URL)
        resp.raise_for_status()
        buffer = io.BytesIO(resp.content)
        wb = openpyxl.load_workbook(buffer, data_only=False)
        ws = wb.active
        
        # Read current values
        from_val = ws['B2'].value or "30/09/25"
        to_val = ws['B3'].value or "31/10/25"
        freedom_units = float(ws['C7'].value or 0)
        boerdery_units = float(ws['C9'].value or 0)
        
        # Parse dates
        try:
            from_date = pd.to_datetime(from_val).date()
        except:
            from_date = datetime(2025, 9, 30).date()
        try:
            to_date = pd.to_datetime(to_val).date()
        except:
            to_date = datetime(2025, 10, 31).date()
        
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("Period From (B2)", value=from_date)
            freedom_units = st.number_input("Freedom Village Units (C7)", value=freedom_units)
        with col2:
            to_date = st.date_input("Period To (B3)", value=to_date)
            boerdery_units = st.number_input("Boerdery Units (C9)", value=boerdery_units)
        
        if st.button("Generate Updated Invoice", type="primary"):
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['C7'].value = freedom_units
            ws['C9'].value = boerdery_units
            
            new_buffer = io.BytesIO()
            wb.save(new_buffer)
            new_buffer.seek(0)
            
            st.download_button(
                label="Download Updated Invoice",
                data=new_buffer,
                file_name=f"Invoice_{from_date.strftime('%b%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Invoice updated and ready for download!")
    except Exception as e:
        st.error(f"Failed to load billing template: {e}")

# ==============================================================================
# FOOTER
# ==============================================================================
st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.9rem;'>Durr Bottling Electrical Intelligence Dashboard v5.0<br>Built with ❤️ using real sensor data and actual fuel prices</div>", unsafe_allow_html=True)
