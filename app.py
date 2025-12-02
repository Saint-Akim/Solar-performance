# app.py — Southern Paarl Energy Dashboard (Perfect Consistent Design)
# Final • December 2025

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ PERFECT CONSISTENT LIGHT UI ------------------
st.set_page_config(page_title="Southern Paarl Energy", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Global light background */
    .stApp, [data-testid="stAppViewContainer"] > .main {background: #f8f9fb !important;}
    [data-testid="stSidebar"] {background: white !important; border-right: 1px solid #e5e5e5 !important;}
    
    /* Typography */
    h1, h2, h3, h4, h5, h6, p, div, span, label, .stMarkdown {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        color: #1d1d1f !important;
    }
    
    /* Unified card style */
    .energy-card {
        background: white !important;
        border-radius: 20px !important;
        padding: 28px !important;
        margin: 20px 0 !important;
        box-shadow: 0 8px 30px rgba(0,0,0,0.08) !important;
        border: 1px solid #e8e8e8 !important;
        backdrop-filter: blur(10px);
    }
    
    /* Header */
    .header-title {
        font-size: 44px !important;
        font-weight: 700 !important;
        background: linear-gradient(90deg, #007AFF, #00C853) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-align: center !important;
        margin: 40px 0 10px 0 !important;
    }
    
    /* Buttons - consistent blue */
    .stButton > button {
        background: #007AFF !important;
        color: white !important;
        border-radius: 16px !important;
        height: 56px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,122,255,0.3) !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: #0066CC !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(0,102,204,0.4) !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stDateInput > div > div > input {
        border-radius: 12px !important;
        border: 1px solid #d0d0d0 !important;
        padding: 12px !important;
    }
    
    /* Plotly */
    .js-plotly-plot .plotly {background: white !important;}
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown("<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#555; font-size:18px; margin-bottom:40px;'>Solar • Generator • Factory • Billing Dashboard</p>", unsafe_allow_html=True)

# ------------------ SIDEBAR — PERFECTLY MATCHED ------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:30px 0;">
        <div style="width:80px; height:80px; background:linear-gradient(135deg,#007AFF,#00C853); border-radius:50%; margin:0 auto 20px; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:32px; box-shadow:0 8px 25px rgba(0,122,255,0.3);">
            HA
        </div>
        <div style="font-weight:700; font-size:24px; color:#1d1d1f;">Hussein Akim</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Configuration")
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
        start_date = st.date_input("", datetime(2025, 5, 1), key="from")
    with col2:
        st.markdown("**To**")
        end_date = st.date_input("", datetime(2025, 5, 31), key="to")
    
    st.markdown("---")
    st.markdown("### Navigation")
    page = st.radio("Go to", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")

# ------------------ DATA LOADING (unchanged) ------------------
# [Your working data loading code here — unchanged]

# ------------------ CONSISTENT CHARTS ------------------
def plot(df, x, y, title, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name=title, line=dict(color=color, width=3)))
    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=True,
        hovermode='x unified',
        template="simple_white",
        height=520,
        margin=dict(l=40, r=40, t=80, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
    return fig

# ------------------ PAGES — PERFECT MATCHING CARDS ------------------
card_style = "class='energy-card'"

if page == "Solar":
    st.markdown(f"<div {card_style}>", unsafe_allow_html=True)
    st.subheader("Solar Output")
    if filtered.empty:
        st.info("No data in selected range — try May 2025")
    else:
        fig = plot(filtered, 'last_changed', 'sum_grid_power', "Actual Power (kW)", "#00C853")
        if 'expected_power_kw' in filtered.columns:
            fig.add_trace(go.Scatter(x=filtered['last_changed'], y=filtered['expected_power_kw'],
                                     name="Expected", line=dict(color="#007AFF", width=3, dash="dot")))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Generator":
    st.markdown(f"<div {card_style}>", unsafe_allow_html=True)
    st.subheader("Generator Performance")
    if 'sensor.generator_fuel_consumed' in filtered.columns:
        st.plotly_chart(plot(filtered, 'last_changed', 'sensor.generator_fuel_consumed', "Fuel Consumed (L)", "#DC2626"), use_container_width=True)
    if 'sensor.generator_runtime_duration' in filtered.columns:
        st.plotly_chart(plot(filtered, 'last_changed', 'sensor.generator_runtime_duration', "Runtime (hours)", "#7C3AED"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Factory":
    st.markdown(f"<div {card_style}>", unsafe_allow_html=True)
    st.subheader("Daily Factory Consumption")
    if 'daily_factory_kwh' in filtered.columns:
        st.plotly_chart(plot(filtered, 'last_changed', 'daily_factory_kwh', "Daily kWh", "#0EA5E9"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Kehua":
    st.markdown(f"<div {card_style}>", unsafe_allow_html=True)
    st.subheader("Kehua Internal Power")
    if 'sensor.kehua_internal_power' in filtered.columns:
        st.plotly_chart(plot(filtered, 'last_changed', 'sensor.kehua_internal_power', "Power (kW)", "#06B6D4"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Billing":
    st.markdown(f"<div {card_style}>", unsafe_allow_html=True)
    st.subheader("Billing Editor – September 2025")
    # [Your billing editor code — unchanged]
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#666; font-size:16px; margin:40px 0;'>Built with love by Hussein Akim • Durr Bottling • December 2025</p>", unsafe_allow_html=True)
