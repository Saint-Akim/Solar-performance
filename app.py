# app.py — Southern Paarl Energy (Option A - Full Featured)
# Final • December 2025
# Author: generated for Hussein Akim

import os
import io
from datetime import datetime, timedelta

import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import openpyxl
import streamlit as st
import concurrent.futures

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="Durr bottling electrical analysis", layout="wide", initial_sidebar_state="expanded")

# Capacities (kW)
GOODWE_KW = 110.0
FRONIUS_KW = 60.0
INVERTER_TOTAL_KW = GOODWE_KW + FRONIUS_KW
PANEL_TOTAL_KW = 221.43
TZ = 'Africa/Johannesburg'

# External resources (GitHub CSVs / Excel)
SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goddwe%26Fronius_March.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_April.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe%26Fronius_may.csv",
]
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"
GEN_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/GEN.csv"
FACTORY_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv"
KEHUA_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/KEHUA%20INTERNAL.csv"
BILLING_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"

# FuelSA key (use env var in production)
FUEL_SA_API_KEY = os.getenv('FUEL_SA_API_KEY', '3577238b0ad746ae986ee550a75154b6')

# ---------------------- UTILITIES ----------------------
@st.cache_data(show_spinner=False)
def _read_csv(url):
    try:
        return pd.read_csv(url)
    except Exception:
        return pd.DataFrame()


def _safe_to_datetime(s, col=None):
    try:
        return pd.to_datetime(s, utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
    except Exception:
        return pd.to_datetime(s, errors='coerce')


# ---------------------- DATA LOADERS ----------------------
@st.cache_data(show_spinner=True)
def load_and_normalize_solar(urls):
    dfs = []
    for u in urls:
        df = _read_csv(u)
        if df.empty:
            continue
        df.columns = df.columns.str.lower().str.strip()
        if {'last_changed', 'state', 'entity_id'}.issubset(df.columns):
            df['last_changed'] = _safe_to_datetime(df['last_changed'])
            df['state'] = pd.to_numeric(df['state'], errors='coerce')
            df['entity_id'] = df['entity_id'].astype(str).str.lower().str.strip()
            piv = df.pivot_table(index='last_changed', columns='entity_id', values='state', aggfunc='mean').reset_index()
            dfs.append(piv)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


@st.cache_data(show_spinner=True)
def load_weather():
    df = _read_csv(WEATHER_URL)
    if df.empty:
        return df
    df.columns = df.columns.str.lower().str.strip()
    if 'period_end' in df.columns:
        df['period_end'] = _safe_to_datetime(df['period_end'])
    return df


@st.cache_data(show_spinner=True)
def load_generic(url):
    df = _read_csv(url)
    if df.empty:
        return df
    df.columns = df.columns.str.lower().str.strip()
    if 'last_changed' in df.columns:
        df['last_changed'] = _safe_to_datetime(df['last_changed'])
    return df


# ---------------------- FUEL PRICES ----------------------
@st.cache_data(ttl=3600)
def fetch_fuel_prices():
    # Try FuelSA official API; fallback to simple monthly table
    if not FUEL_SA_API_KEY:
        return None
    try:
        headers = {'key': FUEL_SA_API_KEY}
        r = requests.get('https://api.fuelsa.co.za/api/fuel/historic', headers=headers, timeout=10)
        r.raise_for_status()
        payload = r.json()
        prices = []
        for p in payload.get('prices', []):
            d = p.get('date')
            if not d:
                continue
            prices.append({
                'date': pd.to_datetime(d),
                'Coast': float(p.get('diesel_0.05_coastal') or p.get('diesel_coastal') or 0),
                'Reef': float(p.get('diesel_0.05_reef') or p.get('diesel_reef') or 0)
            })
        df = pd.DataFrame(prices).sort_values('date')
        return df
    except Exception:
        # fallback synthetic monthly prices
        dates = pd.date_range(start='2025-01-01', periods=12, freq='MS')
        coast = [20.10,20.50,21.00,20.80,20.20,19.80,20.50,21.00,20.80,20.50,21.20,21.50]
        reef = [x+0.8 for x in coast]
        return pd.DataFrame({'date': dates, 'Coast': coast, 'Reef': reef})


# ---------------------- LOAD EVERYTHING ----------------------
with st.spinner('Loading datasets...'):
    solar_df = load_and_normalize_solar(SOLAR_URLS)
    weather_df = load_weather()
    gen_df = load_generic(GEN_URL)
    factory_df = load_generic(FACTORY_URL)
    kehua_df = load_generic(KEHUA_URL)
    fuel_price_df = fetch_fuel_prices()

# ---------------------- SIDEBAR / CONTROLS ----------------------
with st.sidebar:
    st.header('Configuration')
    gti_factor = st.slider('GTI factor (multiplier)', 0.5, 1.5, 1.0, 0.01)
    pr_total = st.slider('Site PR (total)', 0.5, 1.0, 0.80, 0.01)
    pr_goodwe = st.slider('GoodWe PR', 0.5, 1.0, 0.80, 0.01)
    pr_fronius = st.slider('Fronius PR', 0.5, 1.0, 0.80, 0.01)
    cost_per_kwh = st.number_input('Default cost per kWh (ZAR)', 0.0, 20.0, 2.98, 0.01)
    start_date = st.date_input('Start date', datetime.today().date() - timedelta(days=30))
    end_date = st.date_input('End date', datetime.today().date())
    fuel_region = st.selectbox('Fuel region for cost', ['Coast', 'Reef'], index=0)

# ---------------------- MERGE & DERIVE ----------------------
# Merge the available time-series using asof merge on sorted timestamps
all_dfs = []
if not solar_df.empty:
    all_dfs.append(solar_df)
if not gen_df.empty:
    all_dfs.append(gen_df)
if not factory_df.empty:
    all_dfs.append(factory_df)
if not kehua_df.empty:
    all_dfs.append(kehua_df)
if not weather_df.empty:
    all_dfs.append(weather_df)

merged = pd.DataFrame()
if all_dfs:
    # ensure every df has a time column named 'ts' for merging
    prepared = []
    for d in all_dfs:
        df = d.copy()
        if 'last_changed' in df.columns:
            df = df.sort_values('last_changed').rename(columns={'last_changed': 'ts'})
        elif 'period_end' in df.columns:
            df = df.sort_values('period_end').rename(columns={'period_end': 'ts'})
        else:
            continue
        prepared.append(df)

    merged = prepared[0].copy()
    for right in prepared[1:]:
        # merge_asof requires sorted data
        merged = pd.merge_asof(merged.sort_values('ts'), right.sort_values('ts'), on='ts', direction='nearest')

# Short-circuit empty merged
if merged.empty:
    st.warning('No merged data available (check your data sources). You can still use the Billing tab.')

# Normalize solar power to kW
if not merged.empty:
    if 'sensor.fronius_grid_power' in merged.columns:
        merged['sensor.fronius_grid_power'] = pd.to_numeric(merged['sensor.fronius_grid_power'], errors='coerce') / 1000.0
    if 'sensor.goodwe_grid_power' in merged.columns:
        merged['sensor.goodwe_grid_power'] = pd.to_numeric(merged['sensor.goodwe_grid_power'], errors='coerce') / 1000.0
    merged['total_solar_kw'] = merged.get('sensor.fronius_grid_power', 0).fillna(0) + merged.get('sensor.goodwe_grid_power', 0).fillna(0)

# Expected power calculations using weather.gti if present, otherwise approximate
if not merged.empty:
    if 'gti' in merged.columns:
        merged['gti'] = pd.to_numeric(merged['gti'], errors='coerce').fillna(0)
        # expected based on panel area (221.43 kW) and inverter capacities
        merged['expected_total_kw'] = merged['gti'] * gti_factor * PANEL_TOTAL_KW * pr_total / 1000.0
        merged['expected_inverter_kw'] = merged['gti'] * gti_factor * INVERTER_TOTAL_KW * pr_total / 1000.0
        merged['expected_goodwe_kw'] = merged['gti'] * gti_factor * GOODWE_KW * pr_goodwe / 1000.0
        merged['expected_fronius_kw'] = merged['gti'] * gti_factor * FRONIUS_KW * pr_fronius / 1000.0
    else:
        # use simple heuristic: scale of installed capacity × PR
        merged['expected_total_kw'] = PANEL_TOTAL_KW * pr_total * 0.75  # approximate
        merged['expected_inverter_kw'] = INVERTER_TOTAL_KW * pr_total * 0.75
        merged['expected_goodwe_kw'] = GOODWE_KW * pr_goodwe * 0.75
        merged['expected_fronius_kw'] = FRONIUS_KW * pr_fronius * 0.75

# Shortfall analysis
if not merged.empty:
    merged['shortfall_total_kw'] = merged['expected_total_kw'] - merged['total_solar_kw']
    merged['shortfall_goodwe_kw'] = merged['expected_goodwe_kw'] - merged.get('sensor.goodwe_grid_power', 0).fillna(0)
    merged['shortfall_fronius_kw'] = merged['expected_fronius_kw'] - merged.get('sensor.fronius_grid_power', 0).fillna(0)

# Anomaly detection on total_solar_kw (simple z-score over window)
if not merged.empty:
    merged['solar_z'] = (merged['total_solar_kw'] - merged['total_solar_kw'].rolling(72, min_periods=1).mean()) / (merged['total_solar_kw'].rolling(72, min_periods=1).std() + 1e-9)
    merged['anomaly'] = merged['solar_z'].abs() > 4.0

# Fuel / generator economics
if not merged.empty and 'sensor.generator_fuel_consumed' in merged.columns and fuel_price_df is not None:
    merged['sensor.generator_fuel_consumed'] = pd.to_numeric(merged['sensor.generator_fuel_consumed'], errors='coerce').fillna(method='ffill')
    merged = merged.sort_values('ts')
    merged['fuel_l_delta'] = merged['sensor.generator_fuel_consumed'].diff().clip(lower=0).fillna(0)
    # map month->price
    fuel_price_df['month'] = pd.to_datetime(fuel_price_df['date']).dt.to_period('M').dt.to_timestamp()
    merged['month'] = merged['ts'].dt.to_period('M').dt.to_timestamp()
    merged = merged.merge(fuel_price_df[['month', fuel_region]].rename(columns={fuel_region: 'diesel_price'}), on='month', how='left')
    merged['diesel_price'] = merged['diesel_price'].fillna(method='ffill').fillna(20.50)
    merged['fuel_interval_cost_zar'] = merged['fuel_l_delta'] * merged['diesel_price']

# Filter by date
if not merged.empty:
    mask = (merged['ts'] >= pd.to_datetime(start_date)) & (merged['ts'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged.loc[mask].copy()
else:
    filtered = pd.DataFrame()

# ---------------------- UI / Charts ----------------------
st.title('Southern Paarl Energy — Full Dashboard')

# helper plotly function
def make_line(df, x, y, name, color, dash=None):
    return go.Scatter(x=df[x], y=df[y], name=name, line=dict(color=color, width=3, dash=dash), mode='lines')

# Top KPIs
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
if not filtered.empty:
    peak = filtered['total_solar_kw'].max()
    avg_pr = (filtered['total_solar_kw'].sum() / (PANEL_TOTAL_KW * len(filtered))) if len(filtered) > 0 else 0
    total_gen_cost = filtered['fuel_interval_cost_zar'].sum() if 'fuel_interval_cost_zar' in filtered.columns else 0
    kpi1.metric('Peak Solar (kW)', f"{peak:.1f}")
    kpi2.metric('Avg PR (approx)', f"{avg_pr:.2f}")
    kpi3.metric('Generator Cost (ZAR)', f"R {total_gen_cost:,.2f}")
    kpi4.metric('Anomalies', int(filtered['anomaly'].sum()) if 'anomaly' in filtered.columns else 0)
else:
    kpi1.metric('Peak Solar (kW)', '—')
    kpi2.metric('Avg PR (approx)', '—')
    kpi3.metric('Generator Cost (ZAR)', '—')
    kpi4.metric('Anomalies', '—')

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(['Solar Performance', 'Shortfall & Inverter Analysis', 'Generator & Costs', 'Billing Editor'])

with tab1:
    st.subheader('Actual vs Expected — Site & Inverters')
    if filtered.empty:
        st.info('No data for selected date range.')
    else:
        fig = go.Figure()
        fig.add_trace(make_line(filtered, 'ts', 'total_solar_kw', 'Actual Total (kW)', '#00C853'))
        if 'expected_total_kw' in filtered.columns:
            fig.add_trace(make_line(filtered, 'ts', 'expected_total_kw', 'Expected (panels) (kW)', '#007AFF', dash='dot'))
        # inverter expected lines
        if 'expected_goodwe_kw' in filtered.columns:
            fig.add_trace(make_line(filtered, 'ts', 'expected_goodwe_kw', 'Expected GoodWe (kW)', '#FFA500', dash='dot'))
        if 'expected_fronius_kw' in filtered.columns:
            fig.add_trace(make_line(filtered, 'ts', 'expected_fronius_kw', 'Expected Fronius (kW)', '#8A2BE2', dash='dot'))
        # anomalies
        if 'anomaly' in filtered.columns:
            anomalies = filtered[filtered['anomaly']]
            if not anomalies.empty:
                fig.add_trace(go.Scatter(x=anomalies['ts'], y=anomalies['total_solar_kw'], mode='markers', name='Anomalies', marker=dict(color='red', size=8, symbol='x')))
        fig.update_layout(height=520, hovermode='x unified', xaxis_title='Time', yaxis_title='kW')
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader('Shortfall per Inverter')
    if filtered.empty:
        st.info('No data')
    else:
        fig2 = go.Figure()
        fig2.add_trace(make_line(filtered, 'ts', 'shortfall_total_kw', 'Shortfall — Total (kW)', '#FF4D4D'))
        fig2.add_trace(make_line(filtered, 'ts', 'shortfall_goodwe_kw', 'Shortfall — GoodWe (kW)', '#FF9900'))
        fig2.add_trace(make_line(filtered, 'ts', 'shortfall_fronius_kw', 'Shortfall — Fronius (kW)', '#A832FF'))
        fig2.update_layout(height=480, hovermode='x unified')
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('### Short summary')
    if not filtered.empty:
        avg_short_total = filtered['shortfall_total_kw'].mean()
        avg_short_goodwe = filtered['shortfall_goodwe_kw'].mean()
        avg_short_fronius = filtered['shortfall_fronius_kw'].mean()
        st.write(f"Average shortfall — total: {avg_short_total:.2f} kW; GoodWe: {avg_short_goodwe:.2f} kW; Fronius: {avg_short_fronius:.2f} kW")

with tab3:
    st.subheader('Generator fuel & costs')
    if filtered.empty or 'fuel_interval_cost_zar' not in filtered.columns:
        st.info('No generator or fuel price data for selected period.')
    else:
        total_cost = filtered['fuel_interval_cost_zar'].sum()
        total_litres = filtered['fuel_l_delta'].sum()
        st.metric('Total Gen Cost (ZAR)', f"R {total_cost:,.2f}")
        st.metric('Total Litres', f"{total_litres:.1f} L")
        # daily cost
        daily = filtered.resample('D', on='ts')['fuel_interval_cost_zar'].sum().reset_index()
        bar = go.Figure(go.Bar(x=daily['ts'], y=daily['fuel_interval_cost_zar'], marker_color='#FF6B6B'))
        bar.update_layout(title='Daily Generator Cost (ZAR)', height=420)
        st.plotly_chart(bar, use_container_width=True)

with tab4:
    st.subheader('Billing / Invoice Editor')
    st.write('You can preview and download the September 2025 template and edit a few fields locally.')
    try:
        resp = requests.get(BILLING_URL, timeout=10)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active

        col1, col2 = st.columns(2)
        with col1:
            b2_raw = ws['B2'].value if ws['B2'].value else '30/09/25'
            try:
                b2_dt = datetime.strptime(b2_raw, '%d/%m/%y').date()
            except Exception:
                b2_dt = datetime.today().date()
            from_date = st.date_input('Invoice from', value=b2_dt)
            c7_val = st.number_input('Freedom Village (C7)', value=float(ws['C7'].value or 0.0))
        with col2:
            b3_raw = ws['B3'].value if ws['B3'].value else '05/11/25'
            try:
                b3_dt = datetime.strptime(b3_raw, '%d/%m/%y').date()
            except Exception:
                b3_dt = datetime.today().date()
            to_date = st.date_input('Invoice to', value=b3_dt)
            c9_val = st.number_input('Boerdery (C9)', value=float(ws['C9'].value or 0.0))

        if st.button('Apply & Preview'):
            ws['B2'].value = from_date.strftime('%d/%m/%y')
            ws['B3'].value = to_date.strftime('%d/%m/%y')
            ws['C7'].value = c7_val
            ws['C9'].value = c9_val
            ws['B4'].value = (to_date - from_date).days
            buf = io.BytesIO(); wb.save(buf); buf.seek(0)
            st.download_button('Download edited invoice (.xlsx)', buf, file_name=f'September_2025_Invoice_{from_date}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            # also show a small preview
            preview = pd.read_excel(io.BytesIO(buf.getvalue()), header=None)
            st.dataframe(preview.iloc[:20, :10])
    except Exception as e:
        st.error('Could not load billing template: ' + str(e))

# FOOTER
st.markdown('---')
st.caption('            • Durr Bottling • December 2025 — Full-featured')
