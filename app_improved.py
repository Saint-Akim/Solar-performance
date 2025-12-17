import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import io
import openpyxl
from datetime import datetime, timedelta
import numpy as np
import logging
from typing import Tuple, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. IMPROVED VISUAL DESIGN SYSTEM
# ==============================================================================
st.set_page_config(
    page_title="Durr Bottling Energy Intelligence", 
    page_icon="⚡", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

def apply_enhanced_design_system():
    """Enhanced design system with better responsiveness and accessibility"""
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
            
            :root {
                --bg-color: #0f172a;
                --card-bg: #1e293b;
                --card-hover: #2d3748;
                --text-color: #e2e8f0;
                --text-muted: #94a3b8;
                --text-light: #f8fafc;
                --accent-cyan: #38bdf8;
                --accent-green: #4ade80;
                --accent-red: #f87171;
                --accent-yellow: #facc15;
                --border-color: #334155;
                --border-light: rgba(255,255,255,0.05);
                --shadow-dark: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                --gradient-primary: linear-gradient(145deg, rgba(30,41,59,0.8), rgba(15,23,42,0.7));
                --gradient-accent: linear-gradient(135deg, #38bdf8, #4ade80);
            }
            
            .stApp {
                background: var(--bg-color);
                color: var(--text-color);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }
            
            #MainMenu, footer, header {visibility: hidden;}
            .stDeployButton {display: none;}
            
            /* Enhanced Sidebar */
            section[data-testid="stSidebar"] {
                background: var(--card-bg);
                border-right: 2px solid var(--border-color);
                box-shadow: 2px 0 10px rgba(0,0,0,0.1);
            }
            
            /* Typography improvements */
            h1, h2, h3, h4, h5, h6 {
                color: var(--text-light);
                font-weight: 600;
                letter-spacing: -0.025em;
                line-height: 1.2;
            }
            
            h1 { font-size: 2.5rem; margin-bottom: 1rem; }
            h2 { font-size: 2rem; margin-bottom: 0.75rem; }
            h3 { font-size: 1.5rem; margin-bottom: 0.5rem; }
            
            /* Enhanced Tabs */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                margin-bottom: 2rem;
            }
            
            .stTabs [data-baseweb="tab"] {
                background: rgba(255,255,255,0.03);
                border: 1px solid var(--border-light);
                border-radius: 12px;
                color: var(--text-muted);
                padding: 12px 24px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            
            .stTabs [data-baseweb="tab"]:hover {
                background: rgba(255,255,255,0.08);
                transform: translateY(-2px);
            }
            
            .stTabs [data-baseweb="tab"][aria-selected="true"] {
                background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(74, 222, 128, 0.1));
                border: 1px solid rgba(56, 189, 248, 0.4);
                color: var(--accent-cyan);
                box-shadow: 0 4px 20px rgba(56, 189, 248, 0.15);
            }
            
            /* Enhanced Metrics Cards */
            .metric-card {
                background: var(--gradient-primary);
                border: 1px solid var(--border-light);
                border-radius: 16px;
                padding: 24px;
                backdrop-filter: blur(20px);
                margin-bottom: 24px;
                box-shadow: var(--shadow-dark);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .metric-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
                border-color: rgba(255,255,255,0.1);
            }
            
            .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: var(--gradient-accent);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .metric-card:hover::before {
                opacity: 1;
            }
            
            /* Enhanced Buttons */
            .stButton > button {
                background: var(--gradient-accent);
                border: none;
                border-radius: 12px;
                color: white;
                font-weight: 600;
                padding: 12px 32px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(56, 189, 248, 0.2);
            }
            
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(56, 189, 248, 0.3);
            }
            
            /* Form Controls */
            .stSelectbox > div > div, .stDateInput > div > div {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
            }
            
            /* Loading States */
            .stSpinner > div {
                border-top-color: var(--accent-cyan) !important;
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .stTabs [data-baseweb="tab"] {
                    padding: 8px 16px;
                    font-size: 0.875rem;
                }
                
                .metric-card {
                    padding: 16px;
                }
                
                h1 { font-size: 2rem; }
                h2 { font-size: 1.5rem; }
                h3 { font-size: 1.25rem; }
            }
        </style>
    """, unsafe_allow_html=True)

def render_enhanced_metric(
    label: str, 
    value: str, 
    delta: Optional[str] = None, 
    color: str = "neutral",
    icon: Optional[str] = None
) -> None:
    """Enhanced metric cards with icons and improved styling"""
    colors = {
        "positive": "#4ade80", 
        "negative": "#f87171", 
        "cyan": "#38bdf8", 
        "neutral": "#94a3b8",
        "yellow": "#facc15"
    }
    
    c = colors.get(color, colors["neutral"])
    delta_html = f"<div style='color:{c}; font-size:0.9rem; margin-top:8px; font-weight:500; display:flex; align-items:center;'>{delta}</div>" if delta else ""
    icon_html = f"<div style='font-size:1.5rem; margin-bottom:8px;'>{icon}</div>" if icon else ""
    
    st.markdown(f"""
    <div class="metric-card">
        {icon_html}
        <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">
            {label}
        </div>
        <div style="font-size: 2rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px;">
            {value}
        </div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)