
# app.py — Southern Paarl Energy Dashboard (Home Assistant Frontend Style)
# Final version • December 2025

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ HOME ASSISTANT FRONTEND STYLE ------------------
st.set_page_config(page_title="Durr Bottling Electrical Analysis", layout="wide", initial_sidebar_state="expanded")

HA_CSS = """
<style>
    :root {
        --ha-card-background: #ffffff;
        --ha-card-border-radius: 12px;
        --ha-card-box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        --primary-color: #03a9f4;
        --secondary-text-color: #727272;
        --text-primary-color: #212121;
        --paper-item-icon-color: #44739e;
        --state-icon-color: #44739e;
        --divider-color: rgba(0,0,0,.12);
        --mdc-theme-primary: #03a9f4;
        --mdc-theme-on-primary: white;
    }
    [data-testid="stAppViewContainer"] > .main {background: #f0f2f6; font-family: Roboto, sans-serif;}
    [data-testid="stSidebar"] {background: #fafafa; border-right: 1px solid var(--divider-color);}
    
    /* HA Card Style */
    .ha-card {
        background: var(--ha-card-background);
        border-radius: var(--ha-card-border-radius);
        box-shadow: var(--ha-card-box-shadow);
        padding: 16px;
        margin: 16px 0;
        border: 1px solid var(--divider-color);
    }
    .ha-card h1, .ha-card h2, .ha-card h3 {
        font-family: 'Roboto', sans-serif !important;
        margin: 0 0 8px 0;
        color: var(--text-primary-color);
    }
    .ha-card h2 {font-size: 1.4rem; font-weight: 500;}
    
    /* Header */
    .ha-header {
        background: white;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 24px;
        border: 1px solid var(--divider-color);
    }
    .ha-title {
        font-size: 28px;
        font-weight: 500;
        color: var(--text-primary-color);
        margin: 0;
    }
    .ha-subtitle {
        color: var(--secondary-text-color);
        font-size: 15px;
        margin-top: 4px;
    }
    
    /* Sidebar */
    .sidebar-ha {padding: 20px;}
    .sidebar-title {font-size: 1.4rem; font-weight: 500; margin-bottom: 16px; color: #03a9f4;}
    .profile-ha {
        display: flex; align-items: center; gap: 12px; margin-bottom: 20px;
    }
    .profile-avatar {
        width: 48px; height: 48px; border-radius: 50%;
        background: linear-gradient(135deg, #03a9f4, #0299d9);
        display: flex; align-items: center; justify-content: center;
        color: white; font-weight: bold; font-size: 18px;
    }
    
    /* Buttons */
    .stButton > button {
        background: var(--mdc-theme-primary) !important;
        color: white !important;
        border-radius: 8px !important;
        height: 40px !important;
        font-weight: 500 !important;
        border: none !important;
    }
    .stButton > button:hover {background: #0299d9 !important;}
    
    /* Metrics */
    .metric-ha {
        background: white;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        text-align: center;
    }
</style>
"""
st.markdown(HA_CSS, unsafe_allow_html=True)

# ------------------ HEADER — HA STYLE ------------------
st.markdown(f"""
<div class="ha-header">
  <div class="ha-title">Southern Paarl Energy</div>
  <div class="ha-subtitle">Solar • Generator • Factory • Billing Dashboard</div>
</div>
""", unsafe_allow_html=True)

# ------------------ SIDEBAR — HA STYLE ------------------
with st.sidebar:
    st.markdown("<div class='sidebar-ha'>", unsafe_allow_html=True)
    st.markdown("<div class='profile-ha'><div class='profile-avatar'>HA</div><div><strong>Hussein Akim</strong></div></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div class='sidebar-title'>Configuration</div>", unsafe_allow_html=True)
    
    st.markdown("**GTI Factor**")
    gti_factor = st.slider("", 0.50, 1.50, 1.00, 0.01, key="gti")
    
    st.markdown("**Performance Ratio**")
    pr_ratio = st.slider("", 0.50, 1.00, 0.80, 0.01, key="pr")
    
    st.markdown("**Cost per kWh (ZAR)**")
    cost_per_unit = st.number_input("", min_value=0.0, value=2.98, step=0.01, format="%.2f", key="cost")
    
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**From**")
        start_date = st.date_input("", datetime.today() - timedelta(days=30), key="from")
    with col2:
        st.markdown("**To**")
        end_date = st.date_input("", datetime.today(), key="to")
    
    st.markdown("---")
    st.markdown("<div class='sidebar-title'>Navigation</div>", unsafe_allow_html=True)
    page = st.radio("Go to", [
        "Solar Performance", "Generator", "Factory", "Kehua", "Billing"
    ], label_visibility="collapsed")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ DATA LOADING (unchanged) ------------------
# ... [all your existing data loading code] ...

# ------------------ PAGE CONTENT — HA CARD STYLE ------------------
if page == "Solar Performance":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.markdown("<h2>Solar Performance</h2>", unsafe_allow_html=True)
    fig = chart(filtered, 'last_changed', 'sum_grid_power', "Actual vs Expected Power", "#03a9f4")
    if 'expected_power_kw' in filtered.columns:
        fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'],
                                 name="Expected", line=dict(color="#ff9800", dash="dot")))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.markdown("<h2>Generator Performance</h2>", unsafe_allow_html=True)
    if 'sensor.generator_fuel_consumed' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel Consumed (L)", "#f44336"), use_container_width=True)
    if 'sensor.generator_runtime_duration' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (hours)", "#9c27b0"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.markdown("<h2>Daily Factory Consumption</h2>", unsafe_allow_html=True)
    if 'daily_factory_kwh' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'daily_factory_kwh', "Daily kWh", "#2196f3"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.markdown("<h2>Kehua Internal Power</h2>", unsafe_allow_html=True)
    if 'sensor.kehua_internal_power' in filtered.columns:
        st.plotly_chart(chart(filtered, 'last_changed', 'sensor.kehua_internal_power', "Power (kW)", "#00bcd4"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing":
    st.markdown("<div class='ha-card'>", unsafe_allow_html=True)
    st.markdown("<h2>Billing Editor – September 2025</h2>", unsafe_allow_html=True)
    # ... [your existing billing editor code] ...
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#727272; font-size:0.9rem;'>Built by Electrical@durrbottling• Durr Bottling • December 2025</p>", unsafe_allow_html=True)
