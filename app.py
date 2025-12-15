import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import io
import openpyxl
from datetime import datetime, timedelta
import concurrent.futures

st.set_page_config(page_title="Durr Bottling Electrical Analysis", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

theme = {
    "bg": "#121212" if st.session_state.theme == 'dark' else "#F8F9FA",
    "card": "#1E1E1E" if st.session_state.theme == 'dark' else "#FFFFFF",
    "text": "#E0E0E0" if st.session_state.theme == 'dark' else "#2C3E50",
    "label": "#A0A0A0" if st.session_state.theme == 'dark' else "#7F8C8D",
    "border": "1px solid #333" if st.session_state.theme == 'dark' else "1px solid #E9ECEF",
    "grid": "#333" if st.session_state.theme == 'dark' else "#E9ECEF",
    "accent": "#E74C3C",
    "success": "#2ECC71"
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

with st.sidebar:
    st.markdown("## ⚡ Durr Bottling")
    st.caption("Electrical & Energy Intelligence")
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
    preset = st.selectbox("Quick Select", ["Custom", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date"])
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
    st.subheader("Generator")
    fuel_region = st.selectbox("Fuel Region", ["Coast", "Reef"], help="Paarl = Coastal pricing")
    st.markdown("---")
    st.subheader("Data Overrides")
    uploaded_gen_file = st.file_uploader("Upload GEN.csv", type="csv", help="Overrides GitHub generator data")

historical_prices = pd.DataFrame({
    'month': pd.to_datetime(['2025-01-01', '2025-02-01', '2025-03-01', '2025-04-01', '2025-05-01', '2025-06-01', '2025-07-01', '2025-08-01', '2025-09-01', '2025-10-01', '2025-11-01', '2025-12-01']),
    'coast_50ppm': [20.28, 21.62, 21.55, 20.79, 20.57, 17.81, 18.53, 19.20, 19.80, 19.50, 19.00, 22.52],
    'reef_50ppm': [21.08, 22.42, 22.35, 21.59, 21.37, 18.61, 19.33, 20.00, 20.60, 20.30, 19.80, 23.32]
})

price_col = 'coast_50ppm' if fuel_region == "Coast" else 'reef_50ppm'
historical_prices['price'] = historical_prices[price_col]
current_price = historical_prices.iloc[-1]['price']

SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv"
]
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
HISTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/history.csv"

def fetch_clean_data(args):
    url, is_generator = args
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
    urls = SOLAR_URLS + [GEN_URL, FACTORY_URL, KEHUA_URL, HISTORY_URL]
    flags = [False] * len(SOLAR_URLS) + [True, False, False, False]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_clean_data, zip(urls, flags)))
    solar_df = pd.concat([r for r in results[:len(SOLAR_URLS)] if not r.empty], ignore_index=True) if any(not r.empty for r in results[:len(SOLAR_URLS)]) else pd.DataFrame()
    gen_df = results[len(SOLAR_URLS)]
    factory_df = results[len(SOLAR_URLS)+1]
    kehua_df = results[len(SOLAR_URLS)+2]
    history_df = results[-1]
    return solar_df, gen_df, factory_df, kehua_df, history_df

solar_df, gen_github_df, factory_df, kehua_df, history_df = load_data_engine()

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

    daily['month_start'] = daily['last_changed'].dt.to_period('M').dt.start_time
    daily = daily.merge(historical_prices[['month', 'price']], left_on='month_start', right_on='month', how='left')
    daily['daily_cost_r'] = daily['fuel_used_l'] * daily['price'].fillna(current_price)
    daily = daily.drop(columns=['month', 'month_start'])

    return daily, pivot.reset_index()

daily_gen, full_gen_pivot = process_generator_data(gen_df.copy())

if not daily_gen.empty:
    filtered_gen = daily_gen[
        (daily_gen['last_changed'].dt.date >= start_date) &
        (daily_gen['last_changed'].dt.date <= end_date)
    ].copy()
else:
    filtered_gen = pd.DataFrame()

# ------------------ MERGED DATA WITH SAFE 'ts' ------------------
def get_time_column(df):
    for col in df.columns:
        if 'last_changed' in col.lower():
            return col
    return None

all_dfs = [df for df in [solar_df, factory_df, kehua_df, history_df] if not df.empty]
merged = pd.DataFrame()
if all_dfs:
    base_df = all_dfs[0].copy()
    time_col = get_time_column(base_df)
    if time_col:
        base_df = base_df.set_index(time_col)
        base_df.index = pd.to_datetime(base_df.index)
        base_df = base_df.sort_index()
        merged = base_df
        for df in all_dfs[1:]:
            col = get_time_column(df)
            if col:
                df = df.set_index(col)
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                merged = pd.merge_asof(merged, df, left_index=True, right_index=True, direction='nearest', tolerance=pd.Timedelta('1h'))
        merged = merged.reset_index()
        merged = merged.rename(columns={'index': 'ts'})

if not merged.empty:
    merged['fronius_kw'] = merged.get('sensor.fronius_grid_power', pd.Series(0, index=merged.index)) / 1000
    merged['goodwe_kw'] = merged.get('sensor.goodwe_grid_power', pd.Series(0, index=merged.index)) / 1000
    merged['total_solar'] = merged['fronius_kw'].fillna(0) + merged['goodwe_kw'].fillna(0)

filtered_merged = merged[(merged['ts'] >= pd.to_datetime(start_date)) & (merged['ts'] <= pd.to_datetime(end_date) + timedelta(days=1))] if not merged.empty and 'ts' in merged.columns else pd.DataFrame()

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs(["Generator Analysis", "Solar Performance", "Factory Load", "Billing Editor"])

# ==================== GENERATOR ANALYSIS TAB ====================
with tab1:
    st.markdown("## 🔌 Generator Performance Overview")
    st.caption("Fuel usage, runtime and estimated operating cost using historical diesel prices")

    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.markdown(f"### Current Diesel Price: **R {current_price:.2f}/L** ({fuel_region})")

    if not filtered_gen.empty:
        period_fuel = filtered_gen['fuel_used_l'].sum()
        period_runtime = filtered_gen['runtime_used_h'].sum()
        period_cost = filtered_gen['daily_cost_r'].sum()
        avg_eff = filtered_gen['fuel_efficiency'].mean()

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
            st.markdown("<div class='metric-lbl'>Avg Efficiency</div>", unsafe_allow_html=True)
            eff_text = f"{avg_eff:.1f} kWh/L" if not pd.isna(avg_eff) else "N/A"
            st.markdown(f"<div class='metric-val'>{eff_text}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=filtered_gen['last_changed'], y=filtered_gen['fuel_used_l'], name="Fuel (L)", marker_color="orange"))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['runtime_used_h'], name="Runtime (h)", mode="lines+markers", yaxis="y2", line=dict(color="lightblue")))
        fig.add_trace(go.Scatter(x=filtered_gen['last_changed'], y=filtered_gen['daily_cost_r'], name="Cost (R)", mode="lines+markers", yaxis="y3", line=dict(color=theme['accent'], width=4)))

        fig.update_layout(
            yaxis=dict(title="Fuel (L)"),
            yaxis2=dict(title="Runtime (h)", overlaying="y", side="right"),
            yaxis3=dict(title="Cost (R)", overlaying="y", side="right", position=0.85),
            hovermode="x unified"
        )
        st.plotly_chart(fig, width='stretch')

        st.markdown("### Fuel Consumption Chart")
        fig_fuel = px.line(filtered_gen, x='last_changed', y='fuel_used_l', title="Daily Fuel Consumption (L)", markers=True)
        fig_fuel.update_layout(yaxis_title="Fuel Used (L)", xaxis_title="Date")
        st.plotly_chart(fig_fuel, width='stretch')

        st.download_button("Download Generator Data", filtered_gen.to_csv(index=False).encode(), "generator_data.csv", "text/csv")

        with st.expander("View Raw Data"):
            st.dataframe(filtered_gen.style.format({
                'fuel_used_l': '{:.1f}',
                'runtime_used_h': '{:.2f}',
                'daily_cost_r': 'R {:.0f}',
                'fuel_per_kwh': '{:.3f}',
                'fuel_efficiency': '{:.1f}'
            }))

    else:
        st.info("No generator data available.")

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
        st.plotly_chart(fig, width='stretch')

        st.success(f"Peak Solar Output: {filtered_merged['total_solar'].max():.1f} kW")

        filtered_merged['hour'] = filtered_merged['ts'].dt.hour
        heatmap_data = filtered_merged.groupby('hour')['total_solar'].mean().reset_index()
        fig_heat = px.bar(heatmap_data, x='hour', y='total_solar', title="Average Solar Output by Hour of Day")
        st.plotly_chart(fig_heat, width='stretch')

        st.download_button("Download Solar Data", filtered_merged.to_csv(index=False).encode(), "solar_data.csv", "text/csv")

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
                st.plotly_chart(fig, width='stretch')

                st.metric("Total Factory kWh", f"{factory_filtered['daily_kwh'].sum():,.0f} kWh")

                st.download_button("Download Factory Data", factory_filtered.to_csv(index=False).encode(), "factory_data.csv", "text/csv")

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

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#E74C3C; font-weight:bold;'>built by Electrical@durrbottling.com</p>", unsafe_allow_html=True)
