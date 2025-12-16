import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import io
import openpyxl
from datetime import datetime, timedelta
import concurrent.futures

# ------------------ PAGE CONFIGURATION ------------------
st.set_page_config(
    page_title="Durr Bottling Electrical Analysis", 
    page_icon="⚡", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ------------------ STYLING ------------------
def apply_professional_theme(dark_mode=True):
    if dark_mode:
        bg_main = "#1e1e2f"
        bg_card = "#2a2c41"
        text_color = "#ffffff"
        accent = "#4fd1c5"
        secondary_text = "#a0a0b0"
    else:
        bg_main = "#f5f5f8"
        bg_card = "#ffffff"
        text_color = "#000000"
        accent = "#4fd1c5"
        secondary_text = "#555555"

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        .stApp {{ background-color: {bg_main}; color: {text_color}; font-family: 'Roboto', sans-serif; }}
        .fuel-card {{ background-color: {bg_card}; color: {text_color}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); margin: 16px 0; }}
        .stMetric {{ background-color: {bg_card}; color: {text_color}; border-radius: 12px; padding: 25px 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.2); margin-bottom: 15px; }}
        .stPlotlyChart iframe {{ border-radius: 12px !important; background-color: {bg_card} !important; }}
        .stSidebar {{ background-color: {bg_card}; color: {text_color}; padding: 20px; }}
        .stButton>button {{ background-color: {accent}; color: {text_color}; border-radius: 8px; font-weight: bold; padding: 10px 15px; border: none; }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{ color: {accent}; border-bottom: 4px solid {accent}; }}
        h1, h2, h3 {{ color: {text_color} !important; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ------------------ SIDEBAR & NAVIGATION ------------------
with st.sidebar:
    st.markdown("## ⚡ Durr Bottling")
    st.caption("Electrical & Energy Intelligence")
    st.markdown("---")
    
    # Theme Toggle
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.caption("Dark Mode")
    with col2:
        dark_mode = st.toggle("", value=True, label_visibility="collapsed")
    
    apply_professional_theme(dark_mode)
    
    st.markdown("---")
    st.subheader("Date Range")
    preset = st.selectbox("Quick Select", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date", "Custom"])
    
    today = datetime.today().date()
    if preset == "Last 7 Days":
        start_date = today - timedelta(days=6)
        end_date = today
    elif preset == "Last 30 Days":
        start_date = today - timedelta(days=29)
        end_date = today
    elif preset == "Last 90 Days":
        start_date = today - timedelta(days=89)
        end_date = today
    elif preset == "Year to Date":
        start_date = datetime(today.year, 1, 1).date()
        end_date = today
    else:
        start_date = st.date_input("From", datetime(2025, 1, 1))
        end_date = st.date_input("To", today)
        
    if end_date < start_date:
        st.error("End date must be after start date")
        st.stop()
        
    st.markdown("---")

# ------------------ DATA SOURCES ------------------
# CORRECTED URLs (Fixed typos: Sloar->Solar, Goddwe->Goodwe, may->May)
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
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
FUEL_PURCHASE_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Durr%20bottling%20Generator%20filling.xlsx"

# ------------------ DATA ENGINE ------------------

def clean_home_assistant_data(df):
    """Pivots Home Assistant long-format data to wide-format"""
    try:
        # Check if it has HA columns
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce')
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            # Pivot to make entities columns
            df_pivot = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            return df_pivot
        return df
    except Exception as e:
        return df

def fetch_url(url):
    try:
        s = requests.get(url).content
        # Try reading as CSV
        df = pd.read_csv(io.StringIO(s.decode('utf-8')))
        return clean_home_assistant_data(df)
    except Exception as e:
        # Return empty if fails (e.g., if it's an Excel file accidentally passed here)
        return pd.DataFrame()

@st.cache_data(show_spinner="Loading Data Engine...")
def load_all_csv_data():
    urls = SOLAR_URLS + [GEN_URL, FACTORY_URL, KEHUA_URL, HISTORY_URL]
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_url, urls))
    
    # Process Solar (First 5 items)
    solar_results = results[:len(SOLAR_URLS)]
    valid_solar = [df for df in solar_results if not df.empty]
    solar_df = pd.concat(valid_solar, ignore_index=True) if valid_solar else pd.DataFrame()
    
    # Process Others
    gen_df = results[len(SOLAR_URLS)]
    factory_df = results[len(SOLAR_URLS)+1]
    kehua_df = results[len(SOLAR_URLS)+2]
    history_df = results[-1]
    
    return solar_df, gen_df, factory_df, kehua_df, history_df

solar_df, gen_raw_df, factory_df, kehua_df, history_df = load_all_csv_data()

# ------------------ FUEL & FINANCIAL ENGINE ------------------

@st.cache_data
def load_fuel_purchases():
    try:
        # Must read as binary for Excel
        resp = requests.get(FUEL_PURCHASE_URL)
        resp.raise_for_status()
        df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0)
    except Exception as e:
        st.warning(f"Could not load fuel purchases: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.lower().str.replace(' ', '_')
    
    # Excel date converter
    def excel_to_date(val):
        if pd.isna(val): return pd.NaT
        if isinstance(val, (int, float)):
            return datetime(1899, 12, 30) + timedelta(days=val)
        return pd.to_datetime(val, errors='coerce')

    df['date'] = df['date'].apply(excel_to_date)
    df = df.dropna(subset=['date'])
    
    # Standardize columns
    rename_map = {
        'amount(liters)': 'liters', 
        'price_per_litre': 'price_per_l', 
        'cost(rands)': 'cost_r'
    }
    df.rename(columns=rename_map, inplace=True)
    return df

fuel_purchases = load_fuel_purchases()
filtered_fuel = pd.DataFrame()
if not fuel_purchases.empty:
    filtered_fuel = fuel_purchases[
        (fuel_purchases['date'].dt.date >= start_date) & 
        (fuel_purchases['date'].dt.date <= end_date)
    ]

# Calculate Monthly Prices
def get_monthly_prices(fuel_df):
    if fuel_df.empty:
        # Fallback prices if no file found
        dates = pd.date_range('2025-01-01', '2025-12-01', freq='MS')
        return pd.DataFrame({'month': dates, 'price': 22.50})
    
    fuel_df = fuel_df.copy()
    fuel_df['month'] = fuel_df['date'].dt.to_period('M').dt.to_timestamp()
    
    monthly = fuel_df.groupby('month').apply(
        lambda g: pd.Series({'total_liters': g['liters'].sum(), 'total_cost': g['cost_r'].sum()})
    ).reset_index()
    
    monthly['price'] = monthly['total_cost'] / monthly['total_liters']
    
    # Fill missing months forward/backward
    all_months = pd.DataFrame({'month': pd.date_range('2025-01-01', '2025-12-01', freq='MS')})
    monthly = pd.merge(all_months, monthly[['month', 'price']], on='month', how='left')
    monthly['price'] = monthly['price'].ffill().bfill()
    return monthly

historical_prices = get_monthly_prices(fuel_purchases)
current_price = historical_prices['price'].iloc[-1] if not historical_prices.empty else 22.50

# ------------------ GENERATOR CALCULATIONS (FIXED LOGIC) ------------------

def process_generator_logic(df_in):
    if df_in.empty: return pd.DataFrame(), {}
    
    df = df_in.copy()
    df.columns = df.columns.str.lower()
    
    # Intelligent Column Finder
    try:
        time_col = [c for c in df.columns if 'time' in c or 'date' in c or 'last_changed' in c][0]
        # Look for fuel (liters)
        fuel_col = [c for c in df.columns if 'fuel' in c and 'l' in c][0] 
        # Look for runtime (hours)
        run_col = [c for c in df.columns if 'run' in c and 'h' in c][0]
    except IndexError:
        return pd.DataFrame(), {}

    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(time_col)
    
    # FIX 1: SMOOTHING SENSOR DATA
    # We use a rolling median to prevent "slosh" from registering as usage
    df['fuel_smooth'] = df[fuel_col].rolling(window=3, center=True).median().fillna(df[fuel_col])
    
    # Calculate Usage
    # Fuel: Negative diff = consumption. Positive diff = Refuel (clip to 0)
    df['fuel_used_l'] = -df['fuel_smooth'].diff().clip(upper=0) 
    
    # Runtime: Positive diff = run hours
    df['runtime_used_h'] = df[run_col].diff().clip(lower=0)
    
    # Aggregate Daily
    daily = df.resample('D', on=time_col).agg({
        'fuel_used_l': 'sum',
        'runtime_used_h': 'sum'
    }).reset_index().rename(columns={time_col: 'date'})
    
    # Add Pricing
    daily['month'] = daily['date'].dt.to_period('M').dt.to_timestamp()
    daily = pd.merge(daily, historical_prices[['month', 'price']], on='month', how='left')
    daily['price'] = daily['price'].fillna(current_price)
    daily['cost_r'] = daily['fuel_used_l'] * daily['price']
    
    # FIX 2: WEIGHTED TOTALS
    total_fuel = daily['fuel_used_l'].sum()
    total_time = daily['runtime_used_h'].sum()
    
    totals = {
        'total_cost': daily['cost_r'].sum(),
        'total_fuel': total_fuel,
        'total_run': total_time,
        # Weighted Average (Total L / Total H) instead of Average of Daily Averages
        'avg_lph': (total_fuel / total_time) if total_time > 0 else 0
    }
    
    # Calculate daily efficiency just for the chart
    daily['lph'] = daily.apply(lambda x: x['fuel_used_l'] / x['runtime_used_h'] if x['runtime_used_h'] > 0.1 else 0, axis=1)
    
    return daily, totals

daily_gen, gen_totals = process_generator_logic(gen_raw_df)

if not daily_gen.empty:
    filtered_gen = daily_gen[(daily_gen['date'].dt.date >= start_date) & (daily_gen['date'].dt.date <= end_date)]
    
    # Re-calculate totals for filtered period using weighted logic
    f_fuel = filtered_gen['fuel_used_l'].sum()
    f_time = filtered_gen['runtime_used_h'].sum()
    
    filtered_gen_totals = {
        'total_cost': filtered_gen['cost_r'].sum(),
        'total_fuel': f_fuel,
        'total_run': f_time,
        'avg_lph': (f_fuel / f_time) if f_time > 0 else 0
    }
else:
    filtered_gen = pd.DataFrame()
    filtered_gen_totals = {}

# ------------------ TAB INTERFACE ------------------
tab1, tab2, tab3, tab4 = st.tabs(["🔌 Generator", "☀️ Solar", "🏭 Factory", "📄 Billing"])

# === TAB 1: GENERATOR ===
with tab1:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if filtered_gen_totals:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Est. Total Cost", f"R {filtered_gen_totals['total_cost']:,.2f}")
        c2.metric("Fuel Consumed", f"{filtered_gen_totals['total_fuel']:.1f} L")
        c3.metric("Runtime", f"{filtered_gen_totals['total_run']:.1f} hrs")
        c4.metric("Avg Efficiency", f"{filtered_gen_totals['avg_lph']:.2f} L/hr")
        
        # Chart
        fig = px.bar(filtered_gen, x='date', y='fuel_used_l', title="Daily Fuel Consumption", color_discrete_sequence=[accent])
        # Add Efficiency line
        fig.add_scatter(x=filtered_gen['date'], y=filtered_gen['lph']*10, mode='lines', name='Efficiency (L/h x10)', line=dict(color='#f97316', width=2))
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No generator usage data for this period.")
    
    st.markdown("### ⛽ Fuel Purchase Log")
    if not filtered_fuel.empty:
        st.dataframe(filtered_fuel[['date', 'liters', 'price_per_l', 'cost_r']].style.format({
            'date': '{:%Y-%m-%d}', 'liters': '{:.1f}', 'price_per_l': 'R {:.2f}', 'cost_r': 'R {:,.2f}'
        }), use_container_width=True)
    else:
        st.caption("No fuel purchases recorded in this date range.")
    st.markdown("</div>", unsafe_allow_html=True)

# === TAB 2: SOLAR ===
with tab2:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not solar_df.empty:
        solar_df['last_changed'] = pd.to_datetime(solar_df['last_changed'])
        # Filter
        f_solar = solar_df[(solar_df['last_changed'].dt.date >= start_date) & (solar_df['last_changed'].dt.date <= end_date)]
        
        if not f_solar.empty:
            # Combine inverters
            f_solar['total_output'] = (f_solar.get('sensor.goodwe_grid_power', 0) + f_solar.get('sensor.fronius_grid_power', 0)) / 1000
            
            fig = px.area(f_solar, x='last_changed', y='total_output', title="Total Solar Output (kW)", color_discrete_sequence=[accent])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            
            st.success(f"Peak Output: {f_solar['total_output'].max():.2f} kW")
        else:
            st.info("No solar data in range.")
    else:
        st.error("Solar data could not be loaded. Check GitHub URLs.")
    st.markdown("</div>", unsafe_allow_html=True)

# === TAB 3: FACTORY ===
with tab3:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not factory_df.empty:
        factory_df['last_changed'] = pd.to_datetime(factory_df['last_changed'])
        f_fac = factory_df[(factory_df['last_changed'].dt.date >= start_date) & (factory_df['last_changed'].dt.date <= end_date)].copy()
        
        # Calculate daily usage from cumulative sensor
        col_name = 'sensor.bottling_factory_monthkwhtotal'
        if col_name in f_fac.columns:
            f_fac = f_fac.sort_values('last_changed')
            f_fac['daily_kwh'] = f_fac[col_name].diff().clip(lower=0)
            
            fig = px.bar(f_fac, x='last_changed', y='daily_kwh', title="Factory Daily Energy (kWh)", color_discrete_sequence=['#3498DB'])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            
            st.metric("Total Consumption", f"{f_fac['daily_kwh'].sum():,.0f} kWh")
        else:
            st.warning(f"Column '{col_name}' not found in factory data.")
    else:
        st.info("No factory data available.")
    st.markdown("</div>", unsafe_allow_html=True)

# === TAB 4: BILLING EDITOR (FIXED EXCEL WRITE) ===
with tab4:
    st.subheader("📝 Invoice Generator")
    col1, col2 = st.columns(2)
    
    # User Inputs
    with col1:
        inv_start = st.date_input("Invoice Start Date", value=datetime(2025, 9, 1))
        unit_c7 = st.number_input("Freedom Village Units (C7)", value=0.0)
    with col2:
        inv_end = st.date_input("Invoice End Date", value=datetime(2025, 9, 30))
        unit_c9 = st.number_input("Boerdery Units (C9)", value=0.0)
        
    if st.button("Generate & Download Invoice", type="primary"):
        try:
            r = requests.get(BILLING_URL)
            r.raise_for_status()
            
            wb = openpyxl.load_workbook(io.BytesIO(r.content))
            ws = wb.active
            
            # Update Cells - Use Actual Date Objects for Excel formulas
            ws['B2'] = inv_start
            ws['B3'] = inv_end
            ws['C7'] = unit_c7
            ws['C9'] = unit_c9
            
            # Save
            out_buffer = io.BytesIO()
            wb.save(out_buffer)
            out_buffer.seek(0)
            
            st.download_button(
                label="📥 Download Excel Invoice",
                data=out_buffer,
                file_name=f"Invoice_{inv_start.strftime('%b_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Invoice generated successfully!")
            
        except Exception as e:
            st.error(f"Error processing invoice: {e}")

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; opacity:0.6;'>System v2.1 | Durr Bottling Electrical</p>", unsafe_allow_html=True)
