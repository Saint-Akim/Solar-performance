# app.py — Southern Paarl Energy Dashboard (Sequoia + Light HA Style)
# Final, working version • Updated Dec 2025
# Notes: preserves your data sources & billing editor; adds Sequoia-inspired UI touches,
# individual inverter PR sliders, expected-power lines for total and inverter capacity.

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta
from typing import List

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="Durr Bottling Power",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ CONSTANTS ------------------
TOTAL_CAPACITY_KW = 221.43
GOODWE_KW = 110.0
FRONIUS_KW = 60.0
INVERTER_TOTAL_KW = GOODWE_KW + FRONIUS_KW
TZ = "Africa/Johannesburg"

# ------------------ STYLES (Sequoia-inspired + Light HA) ------------------
st.markdown(
    """
    <style>
    :root{
       --bg:#f5f6f8;
       --card:#ffffff;
       --muted:#6b7280;
       --accent-1: linear-gradient(90deg,#007AFF,#00C853);
       --radius:16px;
    }
    /* Page background */
    [data-testid="stAppViewContainer"] > .main {
        background: radial-gradient(800px 400px at 10% 10%, rgba(0,122,255,0.03), transparent),
                    radial-gradient(700px 300px at 90% 90%, rgba(0,200,83,0.02), transparent),
                    var(--bg);
        padding: 16px 20px 48px 20px;
    }
    /* HA-style sequoia card */
    .ha-card {
        background: var(--card);
        border-radius: var(--radius);
        padding: 20px;
        margin: 12px 0;
        box-shadow: 0 8px 24px rgba(9,30,66,0.06);
        border: 1px solid rgba(9,30,66,0.04);
    }
    .ha-header {
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255,255,255,0.94));
        padding: 28px 22px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 12px 36px rgba(9,30,66,0.06);
        margin-bottom: 18px;
        border: 1px solid rgba(9,30,66,0.04);
    }
    .ha-title {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
        font-size: 34px;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(90deg, #007AFF, #00C853);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .ha-subtitle { color: var(--muted); font-size: 14px; margin-top:6px; }
    .profile-avatar {
        width:56px;height:56px;border-radius:50%;
        background: linear-gradient(135deg,#007AFF,#00C853);
        display:flex;align-items:center;justify-content:center;color:white;font-weight:700;
        margin: 0 auto 12px auto;
    }
    /* Buttons & inputs */
    .stButton>button { background: linear-gradient(90deg,#007AFF,#0066CC) !important; color: white !important; border-radius:10px !important; height:44px !important; font-weight:700 !important; }
    .stButton>button:hover { opacity:0.95 }
    /* Table fix */
    .dataframe td, .dataframe th { background: transparent !important; }
    /* Plotly white bg */
    .js-plotly-plot .plotly { background: white !important; border-radius: 10px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------ HEADER ------------------
st.markdown(
    """
    <div class="ha-header">
      <div class="ha-title">Southern Paarl Energy</div>
      <div class="ha-subtitle">Solar • Generator • Factory • Billing — Hussein Akim</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.markdown("<div style='text-align:center;padding:10px 0;'>", unsafe_allow_html=True)
    st.markdown("<div class='profile-avatar'>HA</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-weight:700;font-size:16px;text-align:center'>Hussein Akim</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;color:#6b7280;font-size:12px'>Southern Paarl • Electrical</div>", unsafe_allow_html=True)
    st.markdown("</div>")

    st.markdown("---")
    st.markdown("### Configuration")

    # GTI & PR controls (global + per-inverter)
    st.markdown("**Global GTI factor**")
    gti_factor = st.slider("", 0.50, 1.50, 1.00, 0.01, help="Multiply the GTI values from weather feed")

    st.markdown("**Performance Ratio (global)**")
    pr_ratio = st.slider("", 0.50, 1.00, 0.80, 0.01, help="Global PR applied to TOTAL_CAPACITY")

    st.markdown("**PR — GoodWe (110 kW)**")
    pr_goodwe = st.slider("", 0.50, 1.00, 0.90, 0.01)

    st.markdown("**PR — Fronius (60 kW)**")
    pr_fronius = st.slider("", 0.50, 1.00, 0.86, 0.01)

    st.markdown("**Cost per kWh (ZAR)**")
    cost_per_unit = st.number_input("", min_value=0.0, value=2.98, step=0.01, format="%.2f")

    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**From**")
        start_date = st.date_input("", datetime.today() - timedelta(days=30))
    with col2:
        st.markdown("**To**")
        end_date = st.date_input("", datetime.today())

    st.markdown("---")
    st.markdown("### Navigation")
    page = st.radio(
        "Go to",
        ["Solar Performance", "Generator", "Factory", "Kehua", "Billing"],
        index=0,
        label_visibility="collapsed",
    )

# ------------------ DATA SOURCES ------------------
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

# ------------------ DATA LOADING UTILITIES ------------------
st.caption("Loading data from GitHub (cached)...")
progress = st.progress(0)


@st.cache_data(show_spinner=False)
def safe_read_csv(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url)
        return df
    except Exception:
        return pd.DataFrame()


def normalize_sensor_csv(df: pd.DataFrame) -> pd.DataFrame:
    """If this CSV looks like HA state's history, pivot to time index and sensor columns."""
    if df.empty:
        return pd.DataFrame()
    cols = set(df.columns.str.lower())
    # check common Home Assistant export shape
    if {"last_changed", "state", "entity_id"}.issubset(cols):
        df = df.rename(columns={c: c.lower() for c in df.columns})
        # parse times
        df["last_changed"] = pd.to_datetime(df["last_changed"], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        # numeric states
        df["state"] = pd.to_numeric(df["state"], errors="coerce").abs()
        df["entity_id"] = df["entity_id"].str.lower().str.strip()
        piv = df.pivot_table(index="last_changed", columns="entity_id", values="state", aggfunc="mean")
        piv = piv.reset_index().rename(columns={"last_changed": "last_changed"})
        return piv
    # otherwise try to parse common timestamp names
    time_cols = [c for c in df.columns if "time" in c.lower() or "date" in c.lower() or "period" in c.lower()]
    if time_cols:
        tcol = time_cols[0]
        try:
            df[tcol] = pd.to_datetime(df[tcol], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
            df = df.rename(columns={tcol: "last_changed"}).reset_index(drop=True)
            return df
        except Exception:
            pass
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_csvs(urls: List[str]) -> pd.DataFrame:
    dfs = []
    for url in urls:
        tmp = safe_read_csv(url)
        norm = normalize_sensor_csv(tmp)
        if not norm.empty:
            dfs.append(norm)
    if dfs:
        # concat and sort by timestamp
        big = pd.concat(dfs, ignore_index=True, sort=False)
        big = big.sort_values("last_changed").reset_index(drop=True)
        return big
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_weather(gti_factor_local: float, pr_local: float) -> pd.DataFrame:
    df = safe_read_csv(WEATHER_URL)
    if df.empty:
        return pd.DataFrame()
    # try to find GTI column name variants
    possible_cols = [c for c in df.columns if "gti" in c.lower() or "irradi" in c.lower() or "ghi" in c.lower()]
    time_col = None
    for c in df.columns:
        if "period_end" in c.lower() or "time" in c.lower() or "date" in c.lower():
            time_col = c
            break
    if time_col is None:
        # fallback to first column
        time_col = df.columns[0]
    try:
        df[time_col] = pd.to_datetime(df[time_col], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
    except Exception:
        pass
    # pick GTI column or construct a synthetic one if missing
    if possible_cols:
        gti_col = possible_cols[0]
        df = df.rename(columns={time_col: "period_end", gti_col: "gti"})
    else:
        df = df.rename(columns={time_col: "period_end"})
        # if no GTI, attempt to use 'value' or create synthetic
        if "value" in df.columns:
            df = df.rename(columns={"value": "gti"})
        else:
            # fallback synthetic small oscillation
            df["gti"] = 0.9 + 0.1 * (pd.Series(range(len(df))) % 24) / 24.0

    # Expected power in kW (using factors & PR). Note: GTI units must match your expectations.
    # Many GTI feeds are W/m² — if your feed is 1000 W/m² at peak, you may not want the /1000 here.
    # I'll follow your earlier formula but keep it easy to change.
    try:
        df["period_end"] = pd.to_datetime(df["period_end"])
        df["gti"] = pd.to_numeric(df["gti"], errors="coerce").fillna(0)
        # expected power per row in kW
        df["expected_total_kw"] = df["gti"] * gti_factor_local * TOTAL_CAPACITY_KW * pr_local
        # inverter based expected kW
        df["expected_inverter_kw"] = df["gti"] * gti_factor_local * INVERTER_TOTAL_KW * pr_local
        df["expected_goodwe_kw"] = df["gti"] * gti_factor_local * GOODWE_KW * pr_goodwe
        df["expected_fronius_kw"] = df["gti"] * gti_factor_local * FRONIUS_KW * pr_fronius
        return df[["period_end", "gti", "expected_total_kw", "expected_inverter_kw", "expected_goodwe_kw", "expected_fronius_kw"]]
    except Exception:
        return df


# ------------------ LOAD DATA ------------------
progress.progress(5)
solar_df = load_csvs(SOLAR_URLS)
progress.progress(25)
weather_df = load_weather(gti_factor, pr_ratio)
progress.progress(50)
gen_df = load_csvs([GEN_URL])
progress.progress(65)
factory_df = load_csvs([FACTORY_URL])
progress.progress(80)
kehua_df = load_csvs([KEHUA_URL])
progress.progress(95)

# ------------------ MERGE DATASETS (time-aligned) ------------------
def merge_time_series(primary: pd.DataFrame, others: List[pd.DataFrame], time_col_primary="last_changed"):
    if primary is None or primary.empty:
        # pick the first available
        for o in others:
            if o is not None and not o.empty:
                primary = o.copy()
                break
        else:
            return pd.DataFrame()
    merged = primary.copy().sort_values(time_col_primary).reset_index(drop=True)
    for o in others:
        if o is None or o.empty:
            continue
        # find time column
        tcol = "last_changed" if "last_changed" in o.columns else ("period_end" if "period_end" in o.columns else o.columns[0])
        merged = pd.merge_asof(
            merged.sort_values(time_col_primary),
            o.sort_values(tcol),
            left_on=time_col_primary,
            right_on=tcol,
            direction="nearest",
            tolerance=pd.Timedelta("1H")  # adjust tolerance as needed
        )
    return merged

all_sources = [solar_df, gen_df, factory_df, kehua_df, weather_df]
# prefer solar_df as primary if present
primary = solar_df if not solar_df.empty else (weather_df if not weather_df.empty else None)
merged = merge_time_series(primary, [df for df in all_sources if df is not primary])

# normalize kilowatt columns if present (your sensors used W sometimes)
if not merged.empty:
    def safe_divide(col):
        if col in merged.columns:
            try:
                merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0) / 1000.0
            except Exception:
                merged[col] = merged[col]
    safe_divide("sensor.fronius_grid_power")
    safe_divide("sensor.goodwe_grid_power")
    # combined actual kW (fallback to available)
    merged["sum_grid_power"] = merged.get("sensor.fronius_grid_power", 0).fillna(0) + merged.get("sensor.goodwe_grid_power", 0).fillna(0)

# ------------------ FILTER BY DATES ------------------
if not merged.empty and "last_changed" in merged.columns:
    # ensure last_changed is datetime
    merged["last_changed"] = pd.to_datetime(merged["last_changed"], errors="coerce")
    mask = (merged["last_changed"] >= pd.to_datetime(start_date)) & (merged["last_changed"] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
    filtered = merged[mask].copy()
else:
    filtered = pd.DataFrame()

# add expected columns from weather if available (merge by nearest timestamp)
if not filtered.empty and not weather_df.empty:
    if "period_end" in weather_df.columns:
        # merge_asof expecting sorted
        left = filtered.sort_values("last_changed").reset_index(drop=True)
        right = weather_df.sort_values("period_end").reset_index(drop=True)
        left = pd.merge_asof(left, right, left_on="last_changed", right_on="period_end", direction="nearest", tolerance=pd.Timedelta("3H"))
        filtered = left

# ------------------ CHART UTILITIES ------------------
SEQUOIA_COLORS = {
    "actual": "#00C853",           # green
    "expected_total": "#007AFF",   # blue
    "expected_inverter": "#8B5CF6",# purple-ish for inverter expected
    "goodwe": "#0EA5E9",
    "fronius": "#06B6D4",
}

def make_plotly_timeseries(df: pd.DataFrame, traces: List[dict], title: str, height=520):
    fig = go.Figure()
    for t in traces:
        fig.add_trace(go.Scatter(x=df[t["x"]], y=df[t["y"]], name=t.get("name", t["y"]), line=t.get("line", {}), mode=t.get("mode", "lines")))
    fig.update_layout(
        title=title,
        xaxis=dict(rangeslider=dict(visible=True)),
        hovermode="x unified",
        template="simple_white",
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01)
    )
    return fig

# ------------------ PAGE CONTENT ------------------
if page == "Solar Performance":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Actual vs Expected Power")
    if filtered.empty:
        st.info("No merged data available for the selected date range. Check data sources or extend the range.")
    else:
        traces = []
        # Actual power
        if "sum_grid_power" in filtered.columns:
            traces.append({"x": "last_changed", "y": "sum_grid_power", "name": "Actual (kW)", "line": {"color": SEQUOIA_COLORS["actual"], "width": 3}})
        # Expected (total)
        if "expected_total_kw" in filtered.columns:
            traces.append({"x": "last_changed", "y": "expected_total_kw", "name": f"Expected (Total {TOTAL_CAPACITY_KW} kW)", "line": {"color": SEQUOIA_COLORS["expected_total"], "dash": "dot", "width": 2}})
        # Expected (inverter total)
        if "expected_inverter_kw" in filtered.columns:
            traces.append({"x": "last_changed", "y": "expected_inverter_kw", "name": f"Expected (Inverters {INVERTER_TOTAL_KW} kW)", "line": {"color": SEQUOIA_COLORS["expected_inverter"], "dash": "dash", "width": 2}})
        # GoodWe / Fronius expectations
        if "expected_goodwe_kw" in filtered.columns:
            traces.append({"x": "last_changed", "y": "expected_goodwe_kw", "name": "Expected GoodWe", "line": {"color": SEQUOIA_COLORS["goodwe"], "dash": "dot", "width": 1.5}})
        if "expected_fronius_kw" in filtered.columns:
            traces.append({"x": "last_changed", "y": "expected_fronius_kw", "name": "Expected Fronius", "line": {"color": SEQUOIA_COLORS["fronius"], "dash": "dot", "width": 1.5}})

        fig = make_plotly_timeseries(filtered, traces, "Actual vs Expected Power (kW)")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Generator Performance")
    if filtered.empty:
        st.info("No generator data available for selected date range.")
    else:
        if "sensor.generator_fuel_consumed" in filtered.columns:
            st.plotly_chart(make_plotly_timeseries(filtered, [{"x": "last_changed", "y": "sensor.generator_fuel_consumed", "name": "Fuel Consumed (L)", "line": {"color": "#DC2626"}}], "Fuel Consumed (L)"), use_container_width=True)
        if "sensor.generator_runtime_duration" in filtered.columns:
            st.plotly_chart(make_plotly_timeseries(filtered, [{"x": "last_changed", "y": "sensor.generator_runtime_duration", "name": "Runtime (hours)", "line": {"color": "#7C3AED"}}], "Runtime (hours)"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Daily Factory Consumption")
    if "sensor.bottling_factory_monthkwhtotal" in filtered.columns:
        # compute daily (diff) if necessary
        s = filtered[["last_changed", "sensor.bottling_factory_monthkwhtotal"]].copy()
        s = s.sort_values("last_changed")
        s["daily_factory_kwh"] = pd.to_numeric(s["sensor.bottling_factory_monthkwhtotal"], errors="coerce").fillna(method="ffill").diff().fillna(0)
        st.plotly_chart(make_plotly_timeseries(s, [{"x": "last_changed", "y": "daily_factory_kwh", "name": "Daily kWh", "line": {"color": "#0EA5E9"}}], "Daily Factory kWh"), use_container_width=True)
    else:
        st.info("Factory consumption sensor not found in filtered data.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Kehua Internal Power")
    if "sensor.kehua_internal_power" in filtered.columns:
        st.plotly_chart(make_plotly_timeseries(filtered, [{"x": "last_changed", "y": "sensor.kehua_internal_power", "name": "Kehua Power (kW)", "line": {"color": "#06B6D4"}}], "Kehua Internal Power (kW)"), use_container_width=True)
    else:
        st.info("Kehua internal power sensor not found.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.subheader("Billing Editor – September 2025")

    try:
        resp = requests.get(BILLING_URL, timeout=15)
        resp.raise_for_status()
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=False)
        ws = wb.active
    except Exception as e:
        st.error(f"Could not load billing workbook: {e}")
        ws = None

    if ws:
        col1, col2 = st.columns(2)
        with col1:
            b2_val = ws["B2"].value or "30/09/25"
            try:
                from_date = st.date_input("Date From", value=datetime.strptime(b2_val, "%d/%m/%y").date())
            except Exception:
                from_date = st.date_input("Date From", value=datetime.today() - timedelta(days=30))
            try:
                to_default_val = ws["B3"].value or "05/11/25"
                to_date = st.date_input("Date To", value=datetime.strptime(to_default_val, "%d/%m/%y").date())
            except Exception:
                to_date = st.date_input("Date To", value=datetime.today())

            days = (to_date - from_date).days

        with col2:
            def safe_cell_float(cellref, default=0.0):
                try:
                    return float(ws[cellref].value or default)
                except Exception:
                    return default

            c7 = st.number_input("Freedom Village Units (C7)", value=safe_cell_float("C7"))
            c9 = st.number_input("Boerdery Units (C9)", value=safe_cell_float("C9"))
            e9 = st.number_input("Boerdery Cost (E9)", value=safe_cell_float("E9"))
            g21 = st.number_input("Drakenstein Account (G21)", value=safe_cell_float("G21"))

        st.markdown("### Boerdery Subunits")
        c10 = st.number_input("Johan & Stoor (C10)", value=safe_cell_float("C10"))
        c11 = st.number_input("Pomp, Willie, Gaste, Comp (C11)", value=safe_cell_float("C11"))
        c12 = st.number_input("Werkers (C12)", value=safe_cell_float("C12"))

        if st.button("Apply Changes & Preview", type="primary"):
            # write back values
            try:
                ws["A1"].value = from_date.strftime("%b'%y")
                ws["B2"].value = from_date.strftime("%d/%m/%y")
                ws["B3"].value = to_date.strftime("%d/%m/%y")
                ws["B4"].value = days
                ws["C7"].value = c7
                ws["C9"].value = c9
                ws["C10"].value = c10
                ws["C11"].value = c11
                ws["C12"].value = c12
                ws["E7"] = f"=C7*D7"
                ws["E9"].value = e9
                ws["G21"].value = g21

                buf = io.BytesIO()
                wb.save(buf)
                buf.seek(0)
                st.session_state["edited_billing"] = buf.getvalue()
                st.success("Preview generated — you can download the edited workbook below.")
                # show preview (first sheet)
                preview_df = pd.read_excel(io.BytesIO(st.session_state["edited_billing"]), header=None)
                st.dataframe(preview_df, use_container_width=True)
            except Exception as ex:
                st.error(f"Failed to apply changes: {ex}")

        if "edited_billing" in st.session_state:
            st.download_button(
                "Download Edited September 2025.xlsx",
                st.session_state["edited_billing"],
                file_name=f"September 2025 - {from_date.strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#777;font-size:0.9rem;'>Durr Bottling @ 2025</p>",
    unsafe_allow_html=True,
)
