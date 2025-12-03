# app.py — FINAL VERSION (Streamlit + Netlify/Home Assistant Custom Card UI)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import io
import openpyxl
from datetime import datetime, timedelta

# ------------------ NETLIFY / HOME ASSISTANT CUSTOM CARD UI ------------------
st.set_page_config(page_title="Southern Paarl Energy", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Netlify + Mushroom Cards + Home Assistant Custom Card Design */
    .stApp {background: #0f0f0f !important;}
    [data-testid="stAppViewContainer"] > .main {background: transparent !important;}
    [data-testid="stSidebar"] {background: rgba(15,15,15,0.95) !important; backdrop-filter: blur(20px);}
    
    /* Cards - Mushroom Card style */
    .energy-card {
        background: rgba(30,30,30,0.85) !important;
        border-radius: 24px !important;
        padding: 28px !important;
        margin: 20px 0 !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(20px);
        transition: all 0.3s ease !important;
    }
    .energy-card:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 12px 40px rgba(0,0,0,0.7) !important;
    }
    
    /* Header */
    .header-title {
        font-size: 52px !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #00D4FF, #00FF88) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-align: center !important;
        margin: 40px 0 10px 0 !important;
        text-shadow: 0 4px 20px rgba(0,212,255,0.3) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #00D4FF, #00FF88) !important;
        color: black !important;
        border-radius: 16px !important;
        height: 56px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        border: none !important;
        box-shadow: 0 4px 20px rgba(0,212,255,0.4) !important;
        transition: all 0.3s !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 30px rgba(0,255,136,0.5) !important;
    }
    
    /* Text */
    h1, h2, h3, p, div, span, label {color: white !important;}
    .stMarkdown {color: #e0e0e0 !important;}
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown("<h1 class='header-title'>Southern Paarl Energy</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#aaa; font-size:20px; margin-bottom:40px;'>Solar • Generator • Factory • Billing Dashboard</p>", unsafe_allow_html=True)

# ------------------ SIDEBAR (MATCHING NETLIFY UI) ------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:30px 0;">
        <div style="width:80px; height:80px; background:linear-gradient(135deg,#00D4FF,#00FF88); border-radius:50%; margin:0 auto 20px; display:flex; align-items:center; justify-content:center; color:black; font-weight:bold; font-size:32px; box-shadow:0 8px 30px rgba(0,212,255,0.4);">
            HA
        </div>
        <div style="font-weight:700; font-size:24px; color:white;">Hussein Akim</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Configuration")
    st.markdown("**GTI Factor**"); gti_factor = st.slider("", 0.50, 1.50, 1.00, 0.01)
    st.markdown("**Performance Ratio**"); pr_ratio = st.slider("", 0.50, 1.00, 0.80, 0.01)
    st.markdown("**Cost per kWh (ZAR)**"); cost_per_unit = st.number_input("", 0.0, 10.0, 2.98, 0.01)
    
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1: st.markdown("**From**"); start_date = st.date_input("", datetime(2025, 5, 1))
    with col2: st.markdown("**To**"); end_date = st.date_input("", datetime(2025, 5, 31))
    
    st.markdown("---")
    page = st.radio("Navigate", ["Solar", "Generator", "Factory", "Kehua", "Billing"], label_visibility="collapsed")

# ------------------ YOUR FULL DATA + CHARTS CODE HERE ------------------
# [Paste your entire working data loading + plotting code from before]

# Example card (replace all your st.plotly_chart with this style)
if page == "Solar":
    st.markdown("<div class='energy-card'>", unsafe_allow_html=True)
    st.subheader("Solar Output")
    # your chart code
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ... repeat for all pages ...

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("<p style='text-align:center; color:#888; font-size:16px; margin:40px 0;'>Built with love by Hussein Akim • Durr Bottling • December 2025</p>", unsafe_allow_html=True)
