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
        .secondary-text {{ color: {secondary_text}; font-size: 0.9em; }}
        #MainMenu, footer, header {{ visibility: hidden; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚡ Durr Bottling")
    st.caption("Electrical & Energy Intelligence")
    st.markdown("---")
    st.subheader("Appearance")
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.caption("Dark Mode")
    with col2:
        dark_mode = st.toggle("", value=True, label_visibility="collapsed")
        if 'theme' not in st.session_state or dark_mode != (st.session_state.theme == 'dark'):
            st.session_state.theme = 'dark' if dark_mode else 'light'
            st.rerun()
    apply_professional_theme(dark_mode)
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

# ------------------ GENERATOR PROCESSING (AUTOMATED & ACCURATE) ------------------
@st.cache_data(show_spinner=False)
def process_generator_data(_gen_df: pd.DataFrame):
    if _gen_df.empty:
        return pd.DataFrame(), {}

    cols = set(_gen_df.columns.str.lower())

    if {'entity_id', 'state', 'last_changed'}.issubset(cols):
        df = _gen_df.copy()
        df['last_changed'] = pd.to_datetime(df['last_changed'], errors='coerce')
        df['state'] = pd.to_numeric(df['state'], errors='coerce')
        df = df.dropna(subset=['last_changed', 'state'])

        pivot = df.pivot_table(
            index='last_changed',
            columns='entity_id',
            values='state',
            aggfunc='last'
        ).sort_index()

        fuel_cols = pivot.filter(like='fuel')
        runtime_cols = pivot.filter(like='runtime')
        if fuel_cols.empty or runtime_cols.empty:
            return pd.DataFrame(), {}

        fuel = fuel_cols.iloc[:, 0]
        runtime = runtime_cols.iloc[:, 0]

        daily_fuel = fuel.diff().clip(lower=0).resample('D').sum()
        daily_runtime = runtime.diff().clip(lower=0).resample('D').sum()

        daily = pd.DataFrame({
            'last_changed': daily_fuel.index,
            'fuel_used_l': daily_fuel.values,
            'runtime_used_h': daily_runtime.values
        })

    else:
        df = _gen_df.copy()
        df.columns = df.columns.str.lower()

        time_cols = [c for c in df.columns if 'time' in c or 'date' in c]
        if not time_cols:
            return pd.DataFrame(), {}

        time_col = time_cols[0]
        fuel_col = [c for c in df.columns if 'fuel' in c][0]
        runtime_col = [c for c in df.columns if 'run' in c][0]

        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values(time_col)

        df['fuel_l'] = pd.to_numeric(df[fuel_col], errors='coerce')
        df['runtime_h'] = pd.to_numeric(df[runtime_col], errors='coerce')

        df['fuel_used_l'] = -df['fuel_l'].diff()
        df['fuel_used_l'] = df['fuel_used_l'].where(df['fuel_used_l'] > 0, 0)
        df['runtime_used_h'] = df['runtime_h'].diff().clip(lower=0)

        daily = df.resample('D', on=time_col).agg({
            'fuel_used_l': 'sum',
            'runtime_used_h': 'sum'
        }).reset_index().rename(columns={time_col: 'last_changed'})

    # Pricing
    daily['month'] = daily['last_changed'].dt.to_period('M').dt.to_timestamp()
    daily = daily.merge(historical_prices[['month', 'price']], on='month', how='left')
    daily['price_final'] = daily['price'].fillna(current_price)
    daily['daily_cost_r'] = daily['fuel_used_l'] * daily['price_final']
    daily.drop(columns=['month', 'price'], inplace=True)

    # Liters per Hour (safe average)
    daily['liters_per_hour'] = daily.apply(lambda r: r['fuel_used_l'] / r['runtime_used_h'] if r['runtime_used_h'] > 0 else 0, axis=1)

    # Totals
    totals = {
        "total_cost_r": daily['daily_cost_r'].sum(),
        "total_fuel_l": daily['fuel_used_l'].sum(),
        "total_runtime_h": daily['runtime_used_h'].sum(),
        "avg_liters_per_hour": daily['liters_per_hour'][daily['liters_per_hour'] > 0].mean() if (daily['liters_per_hour'] > 0).any() else 0
    }

    return daily, totals

daily_gen, totals = process_generator_data(gen_df.copy())

if not daily_gen.empty:
    filtered_gen = daily_gen[
        (daily_gen['last_changed'].dt.date >= start_date) &
        (daily_gen['last_changed'].dt.date <= end_date)
    ].copy()
    filtered_totals = {
        "total_cost_r": filtered_gen['daily_cost_r'].sum(),
        "total_fuel_l": filtered_gen['fuel_used_l'].sum(),
        "total_runtime_h": filtered_gen['runtime_used_h'].sum(),
        "avg_liters_per_hour": filtered_gen['liters_per_hour'][filtered_gen['liters_per_hour'] > 0].mean() if (filtered_gen['liters_per_hour'] > 0).any() else 0
    }
else:
    filtered_gen = pd.DataFrame()
    filtered_totals = {}

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
tab1, tab2, tab3, tab4 = st.tabs(["🔌 Generator Cost & Fuel", "☀️ Solar Performance", "🏭 Factory Load", "📄 Billing Editor"])

# ==================== GENERATOR ANALYSIS TAB ====================
with tab1:
    st.markdown("## 🔌 Generator Performance Overview")
    st.caption("Fuel usage, runtime and estimated operating cost using historical diesel prices")

    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    st.markdown(f"### Current Diesel Price: **R {current_price:.2f}/L** ({fuel_region})")

    if filtered_totals:
        cols = st.columns(4)
        cols[0].metric("Total Diesel Cost", f"R {filtered_totals['total_cost_r']:,.0f}")
        cols[1].metric("Fuel Used", f"{filtered_totals['total_fuel_l']:.1f} L")
        cols[2].metric("Runtime", f"{filtered_totals['total_runtime_h']:.1f} h")
        cols[3].metric("Avg Liters per Hour", f"{filtered_totals['avg_liters_per_hour']:.2f} L/h")

        fig = px.bar(filtered_gen, x='last_changed', y='fuel_used_l', text='fuel_used_l', labels={'fuel_used_l': 'Fuel Used (L)'})
        fig.add_scatter(x=filtered_gen['last_changed'], y=filtered_gen['liters_per_hour'], mode="lines+markers", name="L/h", line=dict(color="#f97316", width=3))
        fig.update_layout(
            height=520,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(rangeslider=dict(visible=True)),
            yaxis=dict(title="Fuel Used (L) / L/h"),
            xaxis_title="Date",
            legend=dict(orientation="h")
        )
        st.plotly_chart(fig, use_container_width=True)

        lph = filtered_totals['avg_liters_per_hour']
        if lph < 3.5:
            st.success(f"Average Consumption: {lph:.2f} L/h (Excellent)")
        elif lph < 4.5:
            st.success(f"Average Consumption: {lph:.2f} L/h (Good)")
        elif lph < 5.5:
            st.warning(f"Average Consumption: {lph:.2f} L/h (Average)")
        else:
            st.error(f"Average Consumption: {lph:.2f} L/h (High)")

        st.caption("⚠️ Cost variance may occur due to timing of fuel purchases vs consumption and sensor inaccuracies at high tank levels.")

        st.download_button("Download Generator Data", filtered_gen.to_csv(index=False).encode(), "generator_data.csv", "text/csv")

        with st.expander("View Raw Daily Data"):
            st.dataframe(filtered_gen.style.format({
                'fuel_used_l': '{:.1f}',
                'runtime_used_h': '{:.2f}',
                'daily_cost_r': 'R {:.0f}',
                'liters_per_hour': '{:.2f}'
            }))

    else:
        st.info("No generator data available in selected period.")

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== SOLAR PERFORMANCE TAB ====================
with tab2:
    st.markdown("<div class='fuel-card'>", unsafe_allow_html=True)
    if not filtered_merged.empty and 'total_solar' in filtered_merged.columns:
        fig = go.Figure(go.Scatter(
            x=filtered_merged['ts'], y=filtered_merged['total_solar'],
            mode='lines', name='Total Solar Output',
            line=dict(color="#4fd1c5", width=3)
        ))
        fig.update_layout(title="Solar Power Output (kW)", height=500, xaxis=dict(rangeslider=dict(visible=True)))
        st.plotly_chart(fig, use_container_width=True)

        st.success(f"Peak Solar Output: {filtered_merged['total_solar'].max():.1f} kW")

        filtered_merged = filtered_merged.copy()
        filtered_merged['hour'] = filtered_merged['ts'].dt.hour
        heatmap_data = filtered_merged.groupby('hour')['total_solar'].mean().reset_index()
        fig_heat = px.bar(heatmap_data, x='hour', y='total_solar', title="Average Solar Output by Hour of Day")
        st.plotly_chart(fig_heat, use_container_width=True)

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
                fig.update_layout(title="Daily Factory Energy Consumption (kWh)", height=500, xaxis=dict(rangeslider=dict(visible=True)))
                st.plotly_chart(fig, use_container_width=True)

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
            if isinstance(from_val, datetime):
                from_date = from_val.date()
            else:
                from_date = datetime.strptime(str(from_val).strip(), "%d/%m/%y").date()
            from_date = st.date_input("Period From (B2)", value=from_date)
            freedom_units = float(ws['C7'].value or 0)
            freedom_units = st.number_input("Freedom Village Units (C7)", value=freedom_units)
        with col2:
            to_val = ws['B3'].value or "31/10/25"
            if isinstance(to_val, datetime):
                to_date = to_val.date()
            else:
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
st.markdown("<p style='text-align:center; font-weight:bold;'>built by Electrical@durrbottling.com</p>", unsafe_allow_html=True)
