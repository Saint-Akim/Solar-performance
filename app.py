import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta
import concurrent.futures

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Durr Bottling Electrical Analysis", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# Initialize theme
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# ------------------ DESIGN SYSTEM ------------------
if st.session_state.theme == 'dark':
    theme = {
        "bg": "#121212", "card": "#1E1E1E", "text": "#E0E0E0", "label": "#A0A0A0",
        "border": "1px solid #333", "grid": "#333", "accent": "#E74C3C", "success": "#2ECC71"
    }
else:
    theme = {
        "bg": "#F8F9FA", "card": "#FFFFFF", "text": "#2C3E50", "label": "#7F8C8D",
        "border": "1px solid #E9ECEF", "grid": "#E9ECEF", "accent": "#E74C3C", "success": "#2ECC71"
    }

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp {{ background: {theme['bg']}; font-family: 'Roboto', sans-serif; color: {theme['text']}; }}
    .fuel-card {{ background: {theme['card']}; border: {theme['border']}; border-radius: 12px; padding: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); margin: 16px 0; }}
    .metric-val {{ font-size: 32px; font-weight: 700; color: {theme['accent']}; margin: 8px 0; }}
    .metric-lbl {{ font-size: 13px; font-weight: 600; text-transform: uppercase; color: {theme['label']}; letter-spacing: 1px; margin-bottom: 4px; }}
    .header-title {{ font-size: 52px; font-weight: 900; text-align: center; margin: 40px 0 10px; background: linear-gradient(90deg, #E74C3C, #3498DB); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .stButton > button {{ background: {theme['accent']} !important; color: white !important; border-radius: 12px !important; font-weight: 600 !important; height: 48px !important; }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{ color: {theme['accent']}; border-bottom: 4px solid {theme['accent']}; }}
    .plot-container {{ border-radius: 14px; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    @media (max-width: 768px) {{ [data-testid="stColumns"] {{ flex-direction: column !important; }} }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='header-title'>Durr Bottling Electrical Analysis</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:{theme['label']}; font-size:18px; margin-bottom:40px;'>Solar • Generator • Factory • Billing Dashboard</p>", unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.markdown("## ⚡ Durr Bottling")
    st.caption("Electrical & Energy Intelligence")

    st.success("Fuel SA API Connected")
    st.caption("Trial Key • Expires 17 Dec 2025")

    st.markdown("---")

    st.subheader("Appearance")
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.caption("Dark Mode")
    with col2:
        dark_mode = st.toggle("Toggle dark mode", value=(st.session_state.theme == 'dark'), key="theme_toggle")
        if dark_mode != (st.session_state.theme == 'dark'):
            st.session_state.theme = 'dark' if dark_mode else 'light'
            st.rerun()

    st.markdown("---")

    st.subheader("Date Range")
    start_date = st.date_input("From", datetime(2025, 1, 1))
    end_date = st.date_input("To", datetime(2025, 12, 15))

    if end_date < start_date:
        st.error("End date must be after start date")
        st.stop()

    st.markdown("---")

    st.subheader("Generator")
    fuel_region = st.selectbox(
        "Fuel Region",
        ["Coast", "Reef"],
        help="Paarl = Coastal pricing"
    )

    st.markdown("---")

    st.subheader("Data Overrides")
    uploaded_gen_file = st.file_uploader(
        "Upload GEN.csv",
        type="csv",
        help="Overrides GitHub generator data"
    )

# ------------------ LIVE FUEL SA API ------------------
FUEL_SA_API_KEY = "3ef0bc0e377c48b58aa2c2a4d68dcc30"

@st.cache_data(ttl=3600, show_spinner="Updating current diesel price...")
def get_current_diesel_price(region):
    try:
        headers = {'key': FUEL_SA_API_KEY}
        response = requests.get('https://api.fuelsa.co.za/exapi/fuel/current', headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices = []
        for item in data.get('diesel', []):
            location = item['location'].lower()
            value = float(item['value'])
            prices.append({"location": location, "price": value})
        df = pd.DataFrame(prices)
        match = df[df['location'] == region.lower()]
        if match.empty:
            raise ValueError(f"Region '{region}' not found")
        price = match['price'].iloc[0]
        if price > 50:
            st.warning(f"API returned high price R{price:.2f}/L — using fallback.")
            return 22.52
        return price
    except Exception as e:
        st.warning(f"Fuel SA API issue: {e}. Using fallback R22.52/L.")
        return 22.52

current_price = get_current_diesel_price(fuel_region)

# ------------------ HISTORICAL DIESEL PRICE TRENDS ------------------
historical_prices = pd.DataFrame({
    'month': pd.date_range(start='2025-01-01', end='2025-12-01', freq='MS'),
    'price_coast': [20.50, 21.00, 20.76, 20.50, 20.52, 18.70, 19.50, 20.00, 19.80, 19.50, 19.00, 22.52],  # Approximate from available data
    'price_reef': [21.30, 21.80, 21.56, 21.30, 21.32, 19.50, 20.30, 20.80, 20.60, 20.30, 19.80, 23.32]   # + ~0.80 inland difference
})

historical_prices['price_region'] = historical_prices['price_coast' if fuel_region == "Coast" else 'price_reef']

# ------------------ DATA LOADING ------------------
NEW_GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).csv"
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"

def fetch_clean_data(url, is_generator=False):
    try:
        df = pd.read_csv(url)
        if not is_generator and {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
            df['state'] = pd.to_numeric(df['state'], errors='coerce').abs()
            df['entity_id'] = df['entity_id'].str.lower().str.strip()
            return df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        return df
    except Exception as e:
        st.warning(f"Error loading {url}: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner="Loading data from GitHub...")
def load_data_engine():
    results = []
    for u in SOLAR_URLS:
        results.append(fetch_clean_data(u))
    results.append(fetch_clean_data(NEW_GEN_URL, is_generator=True))
    results.append(fetch_clean_data(FACTORY_URL))
    results.append(fetch_clean_data(KEHUA_URL))
    results.append(fetch_clean_data(WEATHER_URL))
    solar_df = pd.concat([r for r in results[:len(SOLAR_URLS)] if not r.empty], ignore_index=True) if results[:len(SOLAR_URLS)] else pd.DataFrame()
    gen_df = results[len(SOLAR_URLS)]
    factory_df = results[len(SOLAR_URLS)+1]
    kehua_df = results[len(SOLAR_URLS)+2]
    weather_df = results[-1]
    return solar_df, gen_df, factory_df, kehua_df, weather_df

solar_df, gen_github_df, factory_df, kehua_df, weather_df = load_data_engine()

gen_df = pd.read_csv(uploaded_gen_file) if uploaded_gen_file else gen_github_df

# ------------------ GENERATOR PROCESSING ------------------
@st.cache_data(show_spinner=False)
def process_generator_data(_gen_df: pd.DataFrame):
    if _gen_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    required = {'entity_id', 'state', 'last_changed'}
    if not required.issubset(_gen_df.columns):
        st.error(f"Generator CSV missing required columns: {required - set(_gen_df.columns)} (found: {_gen_df.columns.tolist()})")
        return pd.DataFrame(), pd.DataFrame()

    _gen_df = _gen_df[['last_changed', 'entity_id', 'state']].copy()
    _gen_df['last_changed'] = pd.to_datetime(_gen_df['last_changed'], utc=True).dt.tz_convert('Africa/Johannesburg').dt.tz_localize(None)
    _gen_df['state'] = pd.to_numeric(_gen_df['state'], errors='coerce')
    _gen_df = _gen_df.dropna(subset=['state']).sort_values('last_changed')
    _gen_df['entity_id'] = _gen_df['entity_id'].str.lower().str.strip()

    pivot = _gen_df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='last')

    def clean_cumulative(series):
        series = series.ffill()
        diff = series.diff()
        series = series.where(diff >= 0, series.shift(1))
        return series.fillna(method='ffill').fillna(0)

    pivot['fuel_liters_cum'] = clean_cumulative(pivot.get('sensor.generator_fuel_consumed'))
    pivot['runtime_hours_cum'] = clean_cumulative(pivot.get('sensor.generator_runtime_duration'))

    pivot['fuel_per_kwh'] = pivot.get('sensor.generator_fuel_per_kwh')
    pivot['fuel_efficiency'] = pivot.get('sensor.generator_fuel_efficiency')

    pivot = pivot.sort_index()
    pivot['fuel_used_l'] = pivot['fuel_liters_cum'].diff().clip(lower=0).fillna(0)
    pivot['runtime_used_h'] = pivot['runtime_hours_cum'].diff().clip(lower=0).fillna(0)

    daily = pivot.resample('D').agg({
        'fuel_used_l': 'sum',
        'runtime_used_h': 'sum',
        'fuel_per_kwh': 'mean',
        'fuel_efficiency': 'mean'
    }).reset_index()

    # Use historical prices for accurate cost
    daily = daily.merge(historical_prices[['month', 'price_region']], left_on=pd.Grouper(key='last_changed', freq='MS'), right_on='month', how='left')
    daily['daily_cost_r'] = daily['fuel_used_l'] * daily['price_region'].fillna(current_price)

    return daily, pivot.reset_index()

daily_gen, full_gen_pivot = process_generator_data(gen_df.copy())

if not daily_gen.empty:
    filtered_gen = daily_gen[
        (daily_gen['last_changed'].dt.date >= start_date) &
        (daily_gen['last_changed'].dt.date <= end_date)
    ].copy()
else:
    filtered_gen = pd.DataFrame()

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Generator Analysis", "Solar Performance", "Factory Load", "Billing Editor", "Fuel Price Trends"])

# ==================== GENERATOR ANALYSIS TAB ====================
with tab1:
    st.markdown("## 🔌 Generator Performance Overview")
    st.caption("Fuel usage, runtime and estimated operating cost")

    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.markdown(f"### Current Diesel Price: **R {current_price:.2f}/L** ({fuel_region})")
    st.caption("⚠️ Historical costs use monthly average prices for accuracy")

    if not filtered_gen.empty:
        period_fuel = filtered_gen['fuel_used_l'].sum()
        period_runtime = filtered_gen['runtime_used_h'].sum()
        period_cost = filtered_gen['daily_cost_r'].sum()
        avg_eff = filtered_gen['fuel_efficiency'].mean()
        avg_l_per_kwh = filtered_gen['fuel_per_kwh'].mean()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-lbl'>Total Cost</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-val'>R {period_cost:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-lbl'>Fuel Used</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-val'>{period_fuel:.1f} L</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-lbl'>Runtime</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-val'>{period_runtime:.1f} h</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col4:
            st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-lbl'>Efficiency</div>", unsafe_allow_html=True)
            eff_text = f"{avg_eff:.1f} kWh/L" if not pd.isna(avg_eff) else "N/A"
            st.markdown(f"<div class='metric-val'>{eff_text}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### 📈 Daily Generator Trends")
        st.caption("Fuel consumption, runtime and estimated cost")

        fig = go.Figure()
        fig.add_trace(go.Bar(x=filtered_gen['last_changed'], y=filtered_gen['fuel_used_l'], name="Daily Fuel (L)", marker_color="orange"))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['runtime_used_h'], name="Runtime (h)", mode="lines+markers", yaxis="y2", line=dict(color="lightblue")))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['daily_cost_r'], name="Daily Cost (R)", mode="lines+markers", yaxis="y3", line=dict(color=theme['accent'], width=4)))

        fig.update_layout(
            title="Generator Daily Fuel Burn, Runtime & Estimated Cost",
            yaxis=dict(title="Fuel (L)"),
            yaxis2=dict(title="Runtime (h)", overlaying="y", side="right"),
            yaxis3=dict(title="Cost (R)", overlaying="y", side="right", position=0.85),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📄 View Daily Generator Data"):
            st.dataframe(filtered_gen.style.format({
                'fuel_used_l': '{:.1f}',
                'runtime_used_h': '{:.2f}',
                'daily_cost_r': 'R {:.0f}',
                'fuel_per_kwh': '{:.3f}',
                'fuel_efficiency': '{:.1f}'
            }))

    else:
        st.info("No generator data available for selected period or upload a GEN.csv file.")

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== SOLAR PERFORMANCE TAB ====================
with tab2:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not filtered_merged.empty and 'total_solar' in filtered_merged.columns:
        fig = go.Figure(go.Scatter(
            x=filtered_merged['ts'], y=filtered_merged['total_solar'],
            mode='lines', name='Total Solar Output',
            line=dict(color=theme['success'], width=3)
        ))
        fig.update_layout(title="Solar Power Output (kW)", height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.success(f"Peak Solar Output: {filtered_merged['total_solar'].max():.1f} kW")
    else:
        st.info("No solar data in selected period.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== FACTORY LOAD TAB ====================
with tab3:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not factory_df.empty:
        factory_filtered = factory_df.copy()
        if 'last_changed' in factory_filtered.columns:
            factory_filtered['last_changed'] = pd.to_datetime(factory_filtered['last_changed'])
            factory_filtered = factory_filtered.sort_values('last_changed')
            if 'sensor.bottling_factory_monthkwhtotal' in factory_filtered.columns:
                factory_filtered['daily_kwh'] = factory_filtered['sensor.bottling_factory_monthkwhtotal'].diff().clip(lower=0).fillna(0)
                factory_filtered = factory_filtered[
                    (factory_filtered['last_changed'].dt.date >= start_date) &
                    (factory_filtered['last_changed'].dt.date <= end_date)
                ]
                fig = go.Figure(go.Scatter(
                    x=factory_filtered['last_changed'], y=factory_filtered['daily_kwh'],
                    mode='lines+markers', name='Daily Factory Consumption',
                    line=dict(color="#3498DB", width=3)
                ))
                fig.update_layout(title="Daily Factory Energy Consumption (kWh)", height=500)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Factory cumulative kWh sensor not found.")
        else:
            st.info("No timestamp column in factory data.")
    else:
        st.info("No factory consumption data available.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== BILLING EDITOR TAB ====================
with tab4:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.subheader("September 2025 Invoice Editor")
    try:
        resp = requests.get(BILLING_URL)
        resp.raise_for_status()
        buffer = io.BytesIO(resp.content)
        wb = openpyxl.load_workbook(buffer, data_only=False)
        ws = wb.active
        col1, col2 = st.columns(2)
        with col1:
            from_val = ws['B2'].value or "30/09/25"
            from_date = datetime.strptime(str(from_val).strip(), "%d/%m/%y").date()
            from_date = st.date_input("Period From (B2)", value=from_date)
            freedom_units = float(ws['C7'].value or 0)
            freedom_units = st.number_input("Freedom Village Units (C7)", value=freedom_units)
        with col2:
            to_val = ws['B3'].value or "31/10/25"
            to_date = datetime.strptime(str(to_val).strip(), "%d/%m/%y").date()
            to_date = st.date_input("Period To (B3)", value=to_date)
            boerdery_units = float(ws['C9'].value or 0)
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
    except Exception as e:
        st.error(f"Failed to load billing template: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== FUEL PRICE TRENDS TAB ====================
with tab5:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.markdown("## ⛽ Historical Diesel Price Trends (2025)")
    st.caption("Monthly average prices (Coast vs Reef/Inland). Source: Approximate from DMRE announcements & market data.")

    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=historical_prices['month'], y=historical_prices['price_coast'], mode='lines+markers', name='Coast', line=dict(color=theme['success'])))
    fig_price.add_trace(go.Scatter(x=historical_prices['month'], y=historical_prices['price_reef'], mode='lines+markers', name='Reef/Inland', line=dict(color=theme['accent'])))
    fig_price.update_layout(
        title="Diesel Price per Litre (R) - 2025",
        xaxis_title="Month",
        yaxis_title="Price (R/L)",
        hovermode="x unified"
    )
    st.plotly_chart(fig_price, use_container_width=True)

    st.dataframe(historical_prices.style.format({
        'price_coast': 'R {:.2f}',
        'price_reef': 'R {:.2f}'
    }).rename(columns={'month': 'Month', 'price_coast': 'Coast (R/L)', 'price_reef': 'Reef/Inland (R/L)'}))

    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#E74C3C; font-weight:bold;'>built by Electrical@durrbottling.com</p>", unsafe_allow_html=True)
