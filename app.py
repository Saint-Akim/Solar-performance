# app.py — Southern Paarl Energy Dashboard
# Integrated: inverter shortfall, PR sliders, anomalies, robust merging, billing edit
# Run: streamlit run app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta
import numpy as np

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Southern Paarl Energy", layout="wide", initial_sidebar_state="expanded")
st.title("Southern Paarl Energy — Unified Dashboard")

# ------------------ CONSTANTS & DEFAULTS ------------------
TOTAL_CAPACITY_KW = 221.43
GOODWE_KW = 110.0
FRONIUS_KW = 60.0
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

# ------------------ SMALL HELPERS ------------------
def safe_read_csv(url):
    try:
        df = pd.read_csv(url)
        # lowercase & strip
        df.columns = df.columns.str.lower().str.strip()
        return df
    except Exception:
        return pd.DataFrame()

def normalize_homeassistant_df(df):
    """
    Expecting HA style rows with last_changed, state, entity_id.
    Return pivoted DF with last_changed column and entity_id columns as fields.
    """
    if df.empty:
        return df
    if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
        df = df.copy()
        # parse times
        df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
        df = df.dropna(subset=['last_changed'])
        df['last_changed'] = df['last_changed'].dt.tz_convert(TZ).dt.tz_localize(None)
        df['state'] = pd.to_numeric(df['state'], errors='coerce')
        df['entity_id'] = df['entity_id'].astype(str).str.lower().str.strip()
        piv = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
        return piv
    # if time series with period_end (weather), parse and return
    if 'period_end' in df.columns:
        df = df.copy()
        df['period_end'] = pd.to_datetime(df['period_end'], utc=True, errors='coerce')
        df = df.dropna(subset=['period_end'])
        df['period_end'] = df['period_end'].dt.tz_convert(TZ).dt.tz_localize(None)
        return df
    return df

@st.cache_data(show_spinner=False)
def load_csv_list(urls):
    dfs = []
    for u in urls:
        raw = safe_read_csv(u)
        if raw.empty:
            continue
        norm = normalize_homeassistant_df(raw)
        if not norm.empty:
            dfs.append(norm)
    if not dfs:
        return pd.DataFrame()
    try:
        combined = pd.concat(dfs, ignore_index=True)
        # if combined has last_changed but duplicates, ensure sorted
        if 'last_changed' in combined.columns:
            combined = combined.sort_values('last_changed').reset_index(drop=True)
        return combined
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_weather_df():
    df = safe_read_csv(WEATHER_URL)
    if df.empty:
        return pd.DataFrame()
    df = normalize_homeassistant_df(df)
    return df

# ------------------ SIDEBAR: Controls ------------------
st.sidebar.header("Configuration")
gti_factor = st.sidebar.slider("GTI Factor (multiply GTI)", 0.5, 1.5, 1.0, 0.01)
pr_overall = st.sidebar.slider("Performance Ratio (overall)", 0.5, 1.0, 0.80, 0.01)
pr_goodwe = st.sidebar.slider("GoodWe PR", 0.5, 1.0, 0.80, 0.01)
pr_fronius = st.sidebar.slider("Fronius PR", 0.5, 1.0, 0.80, 0.01)
apply_pr = st.sidebar.button("Apply PR settings")

today = datetime.now().date()
default_start = (today - timedelta(days=30))
start_date = st.sidebar.date_input("Start date", default_start)
end_date = st.sidebar.date_input("End date", today)

st.sidebar.markdown("---")
st.sidebar.markdown("Navigation")
page = st.sidebar.radio("Pick page", ["Solar Performance", "Inverter Shortfall", "Generator Costs", "Factory", "Billing"])

# remember PR apply behaviour: store last applied values in session state
if 'applied_pr' not in st.session_state:
    st.session_state.applied_pr = {'overall': pr_overall, 'goodwe': pr_goodwe, 'fronius': pr_fronius}
if apply_pr:
    st.session_state.applied_pr = {'overall': pr_overall, 'goodwe': pr_goodwe, 'fronius': pr_fronius}
# use applied values for calculations
PR_OVERALL = st.session_state.applied_pr['overall']
PR_GOODWE = st.session_state.applied_pr['goodwe']
PR_FRONIUS = st.session_state.applied_pr['fronius']

# ------------------ LOAD DATA ------------------
with st.spinner("Loading data from GitHub..."):
    solar_df = load_csv_list(SOLAR_URLS)
    weather_df = load_weather_df()
    gen_df = load_csv_list([GEN_URL])
    factory_df = load_csv_list([FACTORY_URL])
    kehua_df = load_csv_list([KEHUA_URL])

# ------------------ POST-PROCESSING & MERGE ------------------
all_dfs = []
# prefer to use pivoted dataframes (with last_changed) first
for df in [solar_df, gen_df, factory_df, kehua_df]:
    if not df.empty:
        all_dfs.append(df)

# include weather (which may have 'period_end')
if not weather_df.empty:
    all_dfs.append(weather_df)

merged = pd.DataFrame()
if all_dfs:
    # start with first df and merge_asof others onto it
    base = all_dfs[0].copy()
    # ensure base has time column
    if 'last_changed' in base.columns:
        base_time_col = 'last_changed'
    elif 'period_end' in base.columns:
        base_time_col = 'period_end'
    else:
        base_time_col = None

    merged = base.copy()
    for df in all_dfs[1:]:
        # pick time columns
        if 'last_changed' in merged.columns:
            left_on = 'last_changed'
        elif 'period_end' in merged.columns:
            left_on = 'period_end'
        else:
            # can't merge properly
            continue

        if 'last_changed' in df.columns:
            right_on = 'last_changed'
        elif 'period_end' in df.columns:
            right_on = 'period_end'
        else:
            continue

        # ensure datetimes
        merged[left_on] = pd.to_datetime(merged[left_on], errors='coerce')
        df[right_on] = pd.to_datetime(df[right_on], errors='coerce')
        merged = pd.merge_asof(merged.sort_values(left_on), df.sort_values(right_on),
                               left_on=left_on, right_on=right_on, direction='nearest', tolerance=pd.Timedelta('1H'))

# canonical timestamp column
if not merged.empty:
    if 'last_changed' in merged.columns:
        merged['timestamp'] = pd.to_datetime(merged['last_changed'])
    elif 'period_end' in merged.columns:
        merged['timestamp'] = pd.to_datetime(merged['period_end'])
    else:
        merged['timestamp'] = pd.to_datetime(merged.columns[0])  # fallback

    # convert inverter readings from W to kW if needed (some sources already in W)
    # we check magnitudes: if values are big (>1000) assume Watts.
    if 'sensor.fronius_grid_power' in merged.columns:
        # handle non-numeric gracefully
        merged['sensor.fronius_grid_power'] = pd.to_numeric(merged['sensor.fronius_grid_power'], errors='coerce')
        if merged['sensor.fronius_grid_power'].abs().median(skipna=True) > 1000:
            merged['sensor.fronius_grid_power'] = merged['sensor.fronius_grid_power'] / 1000.0
    if 'sensor.goodwe_grid_power' in merged.columns:
        merged['sensor.goodwe_grid_power'] = pd.to_numeric(merged['sensor.goodwe_grid_power'], errors='coerce')
        if merged['sensor.goodwe_grid_power'].abs().median(skipna=True) > 1000:
            merged['sensor.goodwe_grid_power'] = merged['sensor.goodwe_grid_power'] / 1000.0

    # total solar
    merged['actual_goodwe_kw'] = merged.get('sensor.goodwe_grid_power', 0).fillna(0)
    merged['actual_fronius_kw'] = merged.get('sensor.fronius_grid_power', 0).fillna(0)
    merged['actual_total_kw'] = merged['actual_goodwe_kw'] + merged['actual_fronius_kw']

    # expected calculations based on GTI if present, otherwise based on inverter rated capacities * PR
    # If weather has 'gti', use it: gti (W/m2) * gti_factor * capacity(kW) * PR / 1000
    if 'gti' in merged.columns:
        # ensure numeric
        merged['gti'] = pd.to_numeric(merged['gti'], errors='coerce').fillna(0)
        merged['expected_goodwe_kw'] = (merged['gti'] * gti_factor * GOODWE_KW * PR_GOODWE) / 1000.0
        merged['expected_fronius_kw'] = (merged['gti'] * gti_factor * FRONIUS_KW * PR_FRONIUS) / 1000.0
    else:
        # fallback: use rated capacities × PR × gti_factor (interpreted as scaling)
        merged['expected_goodwe_kw'] = GOODWE_KW * PR_GOODWE * gti_factor
        merged['expected_fronius_kw'] = FRONIUS_KW * PR_FRONIUS * gti_factor

    merged['expected_total_kw'] = merged['expected_goodwe_kw'] + merged['expected_fronius_kw']

    # shortfall (positive => expected > actual)
    merged['shortfall_goodwe_kw'] = (merged['expected_goodwe_kw'] - merged['actual_goodwe_kw']).fillna(0)
    merged['shortfall_fronius_kw'] = (merged['expected_fronius_kw'] - merged['actual_fronius_kw']).fillna(0)
    merged['shortfall_total_kw'] = (merged['expected_total_kw'] - merged['actual_total_kw']).fillna(0)

    # anomaly detection: actual less than 90% of expected or actual greater than 110% of expected
    merged['anomaly_goodwe'] = False
    merged['anomaly_fronius'] = False
    try:
        merged.loc[merged['expected_goodwe_kw'] > 0, 'anomaly_goodwe'] = (
            (merged['actual_goodwe_kw'] < 0.9 * merged['expected_goodwe_kw']) |
            (merged['actual_goodwe_kw'] > 1.1 * merged['expected_goodwe_kw'])
        )
        merged.loc[merged['expected_fronius_kw'] > 0, 'anomaly_fronius'] = (
            (merged['actual_fronius_kw'] < 0.9 * merged['expected_fronius_kw']) |
            (merged['actual_fronius_kw'] > 1.1 * merged['expected_fronius_kw'])
        )
    except Exception:
        pass

# filter by dates
if not merged.empty:
    mask = (merged['timestamp'] >= pd.to_datetime(start_date)) & (merged['timestamp'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged.loc[mask].copy()
else:
    filtered = pd.DataFrame()

# ------------------ PLOT HELPERS ------------------
def plot_actual_vs_expected(df, timestamp_col, actual_col, expected_col, title, color_actual, color_expected):
    if df.empty:
        st.info("No data for this selection")
        return
    x = df[timestamp_col]
    y_act = df[actual_col]
    y_exp = df[expected_col]

    anomaly_mask = None
    if actual_col == 'actual_goodwe_kw':
        anomaly_mask = df.get('anomaly_goodwe', pd.Series(False, index=df.index))
    elif actual_col == 'actual_fronius_kw':
        anomaly_mask = df.get('anomaly_fronius', pd.Series(False, index=df.index))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y_act, mode='lines+markers', name='Actual',
                             line=dict(color=color_actual, width=3),
                             marker=dict(size=6, color=['red' if a else 'white' for a in (anomaly_mask.values if anomaly_mask is not None else [False]*len(x))],
                                         line=dict(color=color_actual, width=2)
                                         )))
    fig.add_trace(go.Scatter(x=x, y=y_exp, mode='lines', name='Expected', line=dict(color=color_expected, dash='dash', width=3)))
    # add shortfall as area
    shortfall = (df[expected_col] - df[actual_col]).clip(lower=0)
    fig.add_trace(go.Bar(x=x, y=shortfall, name='Shortfall (kW)', marker_color='rgba(255,99,71,0.25)', opacity=0.6, yaxis='y'))

    fig.update_layout(title=title, hovermode='x unified', template='simple_white', height=480,
                      xaxis=dict(rangeslider_visible=True), legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    st.plotly_chart(fig, use_container_width=True)

def plot_total_solar(df):
    if df.empty:
        st.info("No solar data for this selection")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['actual_total_kw'], name='Actual total (kW)', line=dict(color='#00C853', width=3)))
    if 'expected_total_kw' in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['expected_total_kw'], name='Expected total (kW)', line=dict(color='#007AFF', dash='dash', width=3)))
    fig.update_layout(title="Total Solar — Actual vs Expected", hovermode='x unified', height=520, xaxis=dict(rangeslider_visible=True))
    st.plotly_chart(fig, use_container_width=True)

# ------------------ PAGES ------------------
if page == "Solar Performance":
    st.header("Solar Performance — Actual vs Expected")
    plot_total_solar(filtered)

    st.markdown("### Per-inverter details")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("GoodWe")
        plot_actual_vs_expected(filtered, 'timestamp', 'actual_goodwe_kw', 'expected_goodwe_kw', "GoodWe — Actual vs Expected (kW)", color_actual='#E74C3C', color_expected='#FFB347')
    with c2:
        st.subheader("Fronius")
        plot_actual_vs_expected(filtered, 'timestamp', 'actual_fronius_kw', 'expected_fronius_kw', "Fronius — Actual vs Expected (kW)", color_actual='#3498DB', color_expected='#88CCFF')

    # summary table of shortfalls
    if not filtered.empty:
        st.markdown("### Shortfall summary")
        sum_short = {
            'GoodWe shortfall kW (sum)': filtered['shortfall_goodwe_kw'].sum(),
            'Fronius shortfall kW (sum)': filtered['shortfall_fronius_kw'].sum(),
            'Total shortfall kW (sum)': filtered['shortfall_total_kw'].sum()
        }
        st.table(pd.DataFrame([sum_short]).T.rename(columns={0:'value'}))

elif page == "Inverter Shortfall":
    st.header("Inverter Shortfall Analysis")
    st.markdown("Use the PR sliders in the sidebar to tune expected output. Click **Apply PR settings** to apply.")
    # rolling shortfall charts
    if filtered.empty:
        st.info("No data for the current date range")
    else:
        # rolling 24-hr shortfall sums (assuming timestamp frequency)
        window = 24
        s = filtered.set_index('timestamp').resample('1H').mean().interpolate()
        s['short_we_rolling'] = s['shortfall_goodwe_kw'].rolling(window=window, min_periods=1).sum()
        s['short_fr_rolling'] = s['shortfall_fronius_kw'].rolling(window=window, min_periods=1).sum()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s.index, y=s['short_we_rolling'], name='GoodWe 24h shortfall', line=dict(color='#E74C3C')))
        fig.add_trace(go.Scatter(x=s.index, y=s['short_fr_rolling'], name='Fronius 24h shortfall', line=dict(color='#3498DB')))
        fig.update_layout(title="Rolling Shortfall (24-hour sum)", hovermode='x unified', height=520)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Top anomaly events")
        # show top N highest % shortfalls
        df = filtered.copy()
        # percent shortfall relative to expected (avoid divide by zero)
        df['pct_short_we'] = np.where(df['expected_goodwe_kw'] > 0, (df['shortfall_goodwe_kw'] / df['expected_goodwe_kw']) * 100, 0)
        df['pct_short_fr'] = np.where(df['expected_fronius_kw'] > 0, (df['shortfall_fronius_kw'] / df['expected_fronius_kw']) * 100, 0)
        top = df.sort_values('pct_short_we', ascending=False).head(8)[['timestamp','actual_goodwe_kw','expected_goodwe_kw','pct_short_we']].rename(columns={'pct_short_we':'% shortfall'})
        st.table(top)

elif page == "Generator Costs":
    st.header("Generator Economics & Fuel Costs")
    # check generator column
    if 'sensor.generator_fuel_consumed' not in merged.columns:
        st.info("No generator data available in the merged dataset.")
    else:
        # robust cost handling - attempt to map monthly diesel prices if 'diesel_price' present in data (if user provides)
        # otherwise simply compute differential litres × provided cost_per_unit (sidebar)
        diesel_price = st.sidebar.number_input("Fallback diesel price (R/L)", min_value=0.0, value=2.98, step=0.01)
        # compute diff litres
        merged['sensor.generator_fuel_consumed'] = pd.to_numeric(merged['sensor.generator_fuel_consumed'], errors='coerce').fillna(method='ffill').fillna(0)
        merged = merged.sort_values('timestamp')
        merged['fuel_l_diff'] = merged['sensor.generator_fuel_consumed'].diff().clip(lower=0).fillna(0)
        # if diesel prices exist in merged (column 'diesel_price' or column with region name), use them; else fallback
        price_col = None
        for col in merged.columns:
            if 'diesel' in col.lower() or 'price' in col.lower():
                price_col = col
                break
        if price_col is None:
            merged['diesel_price_used'] = diesel_price
        else:
            merged['diesel_price_used'] = merged[price_col].fillna(diesel_price)

        merged['interval_cost'] = merged['fuel_l_diff'] * merged['diesel_price_used']
        # filter for date range
        gv = merged[(merged['timestamp'] >= pd.to_datetime(start_date)) & (merged['timestamp'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))]
        total_cost = gv['interval_cost'].sum()
        total_litres = gv['fuel_l_diff'].sum()
        st.metric("Total generator cost (selected range)", f"R {total_cost:,.2f}")
        st.metric("Total fuel consumed (L)", f"{total_litres:,.1f} L")

        # daily cost bar
        daily = gv.resample('D', on='timestamp')['interval_cost'].sum().reset_index()
        fig = go.Figure(go.Bar(x=daily['timestamp'], y=daily['interval_cost'], marker_color='#F39C12'))
        fig.update_layout(title="Daily generator cost (R)", height=450)
        st.plotly_chart(fig, use_container_width=True)

elif page == "Factory":
    st.header("Factory Power Consumption")
    if factory_df.empty or 'sensor.bottling_factory_monthkwhtotal' not in factory_df.columns:
        st.info("Factory data not available")
    else:
        df = factory_df.copy()
        # repair types and compute daily usage
        df['sensor.bottling_factory_monthkwhtotal'] = pd.to_numeric(df['sensor.bottling_factory_monthkwhtotal'], errors='coerce')
        df = df.sort_values('last_changed')
        df['daily_kwh'] = df['sensor.bottling_factory_monthkwhtotal'].diff().fillna(0)
        # filter range
        maskf = (df['last_changed'] >= pd.to_datetime(start_date)) & (df['last_changed'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
        df_filtered = df.loc[maskf]
        if df_filtered.empty:
            st.info("No factory data in selected range")
        else:
            st.area_chart(df_filtered.set_index('last_changed')['daily_kwh'], use_container_width=True)
            st.metric("Total kWh in period", f"{df_filtered['daily_kwh'].sum():,.1f} kWh")

elif page == "Billing":
    st.header("Billing Editor — September 2025 (Excel edit via openpyxl)")
    st.markdown("You can edit a few fields and download the updated Excel file.")
    try:
        resp = requests.get(BILLING_URL, timeout=10)
        resp.raise_for_status()
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active

        # Pre-fill UI from sheet
        b2 = ws['B2'].value or "30/09/25"
        b3 = ws['B3'].value or "05/11/25"
        c7_init = float(ws['C7'].value or 0)
        c9_init = float(ws['C9'].value or 0)

        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("Invoice From (B2)", value=datetime.strptime(b2, "%d/%m/%y").date())
            c7_val = st.number_input("Freedom Village Units (C7)", value=c7_init)
        with col2:
            to_date = st.date_input("Invoice To (B3)", value=datetime.strptime(b3, "%d/%m/%y").date())
            c9_val = st.number_input("Boerdery Units (C9)", value=c9_init)

        extra_c10 = st.number_input("Johan & Stoor (C10)", value=float(ws['C10'].value or 0))
        extra_c11 = st.number_input("Pomp, Willie (C11)", value=float(ws['C11'].value or 0))
        extra_c12 = st.number_input("Werkers (C12)", value=float(ws['C12'].value or 0))

        if st.button("Apply & Preview Excel"):
            # write back values to workbook
            ws['B2'].value = from_date.strftime("%d/%m/%y")
            ws['B3'].value = to_date.strftime("%d/%m/%y")
            ws['B4'].value = (to_date - from_date).days
            ws['C7'].value = c7_val
            ws['C9'].value = c9_val
            ws['C10'].value = extra_c10
            ws['C11'].value = extra_c11
            ws['C12'].value = extra_c12
            ws['E7'] = '=C7*D7'  # formula preserved
            # save to buffer and offer preview table
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.session_state.edited_invoice = buf.getvalue()
            # show preview as dataframe
            try:
                preview = pd.read_excel(io.BytesIO(st.session_state.edited_invoice), header=None)
                st.dataframe(preview, use_container_width=True)
            except Exception as e:
                st.error(f"Preview failed: {e}")

        if 'edited_invoice' in st.session_state:
            st.download_button("Download Edited Invoice.xlsx", st.session_state.edited_invoice, file_name="September_2025_Edited.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as exc:
        st.error("Could not load billing file: " + str(exc))

# ------------------ FOOTER ------------------
st.markdown("---")
st.caption("Built by Hussein Akim • Durr Bottling • December 2025")
