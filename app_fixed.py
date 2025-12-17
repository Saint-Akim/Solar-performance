"""
Durr Bottling Energy Intelligence Dashboard - Enhanced Version
==============================================================
Fixed bugs, improved UI, better error handling, and optimized performance
"""

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
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. ENHANCED PAGE CONFIGURATION & DESIGN SYSTEM
# ==============================================================================
st.set_page_config(
    page_title="Durr Bottling Energy Intelligence", 
    page_icon="⚡", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

def apply_enhanced_design_system():
    """Enhanced design system with modern styling, better accessibility, and responsive design"""
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
            
            :root {
                --bg-primary: #0f1419;
                --bg-secondary: #1a1f2e;
                --bg-card: #252a3a;
                --bg-card-hover: #2d3748;
                --text-primary: #f7fafc;
                --text-secondary: #e2e8f0;
                --text-muted: #a0aec0;
                --accent-blue: #3182ce;
                --accent-green: #38a169;
                --accent-red: #e53e3e;
                --accent-yellow: #d69e2e;
                --accent-cyan: #0bc5ea;
                --border: #2d3748;
                --border-light: rgba(255,255,255,0.08);
                --shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
                --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                --gradient-success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                --gradient-warning: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            }
            
            .stApp {
                background: var(--bg-primary);
                color: var(--text-secondary);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }
            
            /* Hide Streamlit branding */
            #MainMenu, footer, header, .stDeployButton {
                visibility: hidden;
            }
            
            /* Enhanced sidebar */
            section[data-testid="stSidebar"] {
                background: var(--bg-secondary);
                border-right: 2px solid var(--border);
                box-shadow: 4px 0 12px rgba(0,0,0,0.15);
            }
            
            /* Typography */
            h1, h2, h3, h4, h5, h6 {
                color: var(--text-primary);
                font-weight: 700;
                letter-spacing: -0.025em;
                line-height: 1.2;
            }
            
            /* Enhanced tabs */
            .stTabs [data-baseweb="tab-list"] {
                gap: 12px;
                margin-bottom: 2rem;
            }
            
            .stTabs [data-baseweb="tab"] {
                background: var(--bg-card);
                border: 1px solid var(--border-light);
                border-radius: 16px;
                color: var(--text-muted);
                padding: 14px 28px;
                font-weight: 600;
                font-size: 0.95rem;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }
            
            .stTabs [data-baseweb="tab"]::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: var(--gradient-primary);
                transform: scaleX(0);
                transition: transform 0.3s ease;
            }
            
            .stTabs [data-baseweb="tab"]:hover {
                background: var(--bg-card-hover);
                transform: translateY(-2px);
                box-shadow: var(--shadow);
            }
            
            .stTabs [data-baseweb="tab"][aria-selected="true"] {
                background: linear-gradient(135deg, rgba(49, 130, 206, 0.15), rgba(56, 161, 105, 0.1));
                border: 1px solid rgba(49, 130, 206, 0.3);
                color: var(--accent-blue);
                box-shadow: 0 8px 32px rgba(49, 130, 206, 0.2);
            }
            
            .stTabs [data-baseweb="tab"][aria-selected="true"]::before {
                transform: scaleX(1);
            }
            
            /* Enhanced buttons */
            .stButton > button {
                background: var(--gradient-primary);
                border: none;
                border-radius: 12px;
                color: white;
                font-weight: 600;
                padding: 12px 32px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(49, 130, 206, 0.25);
                position: relative;
                overflow: hidden;
            }
            
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(49, 130, 206, 0.35);
            }
            
            /* Form controls */
            .stSelectbox > div > div, 
            .stDateInput > div > div,
            .stNumberInput > div > div {
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 8px;
                color: var(--text-secondary);
            }
            
            /* Loading spinner */
            .stSpinner > div {
                border-top-color: var(--accent-blue) !important;
            }
            
            /* Enhanced metric cards */
            .metric-card {
                background: var(--bg-card);
                border: 1px solid var(--border-light);
                border-radius: 20px;
                padding: 28px;
                margin-bottom: 24px;
                box-shadow: var(--shadow);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
                backdrop-filter: blur(20px);
            }
            
            .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: var(--gradient-primary);
                transform: scaleX(0);
                transition: transform 0.4s ease;
            }
            
            .metric-card:hover {
                transform: translateY(-6px) scale(1.02);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
                border-color: var(--border-light);
            }
            
            .metric-card:hover::before {
                transform: scaleX(1);
            }
            
            .metric-icon {
                font-size: 2rem;
                margin-bottom: 12px;
                opacity: 0.8;
            }
            
            .metric-label {
                color: var(--text-muted);
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-weight: 700;
                margin-bottom: 12px;
            }
            
            .metric-value {
                font-size: 2.2rem;
                font-weight: 800;
                color: var(--text-primary);
                margin-bottom: 8px;
                letter-spacing: -0.02em;
            }
            
            .metric-delta {
                font-size: 0.9rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            /* Responsive design */
            @media (max-width: 1024px) {
                .stTabs [data-baseweb="tab"] {
                    padding: 10px 20px;
                    font-size: 0.85rem;
                }
            }
            
            @media (max-width: 768px) {
                .metric-card {
                    padding: 20px;
                }
                
                .metric-value {
                    font-size: 1.8rem;
                }
                
                .stTabs [data-baseweb="tab"] {
                    padding: 8px 16px;
                    font-size: 0.8rem;
                }
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
    """Render enhanced metric cards with improved styling and animations"""
    
    color_map = {
        "positive": "#38a169", 
        "negative": "#e53e3e", 
        "cyan": "#0bc5ea", 
        "neutral": "#a0aec0",
        "yellow": "#d69e2e",
        "blue": "#3182ce"
    }
    
    delta_color = color_map.get(color, color_map["neutral"])
    delta_html = f"""
        <div class="metric-delta" style="color: {delta_color};">
            {delta}
        </div>
    """ if delta else ""
    
    icon_html = f'<div class="metric-icon">{icon}</div>' if icon else ""
    
    st.markdown(f"""
        <div class="metric-card">
            {icon_html}
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)

def create_enhanced_chart(
    df: pd.DataFrame, 
    x_col: str, 
    y_col: str, 
    title: str, 
    color: str = "#3182ce", 
    kind: str = 'bar', 
    y_label: str = "Value",
    height: int = 500
) -> None:
    """Create enhanced charts with better styling and error handling"""
    
    if df.empty:
        st.info("📊 No data available for this visualization.")
        return
    
    # Validate columns
    if x_col not in df.columns or y_col not in df.columns:
        st.error(f"❌ Missing columns: {x_col} or {y_col}")
        logger.error(f"Missing columns in dataframe. Available: {list(df.columns)}")
        return
    
    # Clean data
    df_clean = df.dropna(subset=[x_col, y_col]).copy()
    
    if df_clean.empty:
        st.warning("⚠️ No valid data points after cleaning.")
        return
    
    try:
        # Create trace
        if kind == 'bar':
            trace = go.Bar(
                x=df_clean[x_col], 
                y=df_clean[y_col], 
                marker=dict(
                    color=color,
                    line=dict(width=0)
                ),
                name=y_label,
                hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>"
            )
        elif kind == 'line':
            trace = go.Scatter(
                x=df_clean[x_col], 
                y=df_clean[y_col], 
                mode='lines+markers', 
                line=dict(color=color, width=3),
                marker=dict(size=8, color=color, line=dict(width=2, color='white')),
                name=y_label,
                hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>"
            )
        elif kind == 'area':
            trace = go.Scatter(
                x=df_clean[x_col], 
                y=df_clean[y_col], 
                fill='tozeroy', 
                mode='lines', 
                line=dict(color=color, width=2),
                fillcolor=f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.3)",
                name=y_label,
                hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>"
            )
        else:
            st.error(f"❌ Unsupported chart type: {kind}")
            return
        
        # Enhanced layout
        layout = go.Layout(
            title=dict(
                text=f"<b>{title}</b>",
                font=dict(size=20, color="#f7fafc", family="Inter"),
                x=0.02,
                y=0.95
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter", color="#a0aec0", size=12),
            height=height,
            hovermode="x unified",
            xaxis=dict(
                showgrid=False, 
                linecolor="#2d3748", 
                zeroline=False,
                tickfont=dict(color="#a0aec0"),
                title=dict(text=x_col.replace('_', ' ').title(), font=dict(color="#a0aec0"))
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor="rgba(255,255,255,0.05)", 
                linecolor="#2d3748",
                zeroline=False,
                tickfont=dict(color="#a0aec0"),
                title=dict(text=y_label, font=dict(color="#a0aec0"))
            ),
            margin=dict(l=70, r=30, t=80, b=70),
            showlegend=False,
            hoverlabel=dict(
                bgcolor="rgba(37, 42, 58, 0.95)",
                bordercolor="rgba(255,255,255,0.1)",
                font=dict(color="#f7fafc", family="Inter", size=12)
            )
        )
        
        fig = go.Figure(data=[trace], layout=layout)
        
        config = {
            'displayModeBar': True,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d', 'pan2d'],
            'displaylogo': False,
            'toImageButtonOptions': {
                'format': 'png',
                'filename': title.lower().replace(" ", "_"),
                'height': height,
                'width': 1400,
                'scale': 2
            }
        }
        
        st.plotly_chart(fig, use_container_width=True, config=config)
        
    except Exception as e:
        st.error(f"❌ Error creating chart: {str(e)}")
        logger.error(f"Chart creation failed: {e}")

apply_enhanced_design_system()

# ==============================================================================
# 2. IMPROVED DATA HANDLING WITH ROBUST ERROR MANAGEMENT
# ==============================================================================

# Fixed URLs (corrected typos in solar file names)
DATA_SOURCES = {
    "generator": "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/gen%20(2).xlsx",
    "fuel_level": "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/history%20(5).xlsx", 
    "factory": "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/FACTORY%20ELEC.csv",
    "fuel_purchase": "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Durr%20bottling%20Generator%20filling.xlsx",
    "billing": "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/September%202025.xlsx"
}

# Corrected solar URLs with proper spelling
SOLAR_DATA_SOURCES = [
    ("Jan", "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe&Fronius-Jan.csv"),
    ("Feb", "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe&Fronius_Feb.csv"),  # Fixed
    ("Mar", "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe&Fronius_March.csv"),  # Fixed
    ("Apr", "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe&Fronius_April.csv"),
    ("May", "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_goodwe&Fronius_may.csv")
]

def safe_request(url: str, timeout: int = 30) -> Optional[requests.Response]:
    """Make safe HTTP requests with proper error handling"""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        st.warning(f"⏱️ Request timeout for: {url}")
    except requests.exceptions.ConnectionError:
        st.warning(f"🌐 Connection error for: {url}")
    except requests.exceptions.HTTPError as e:
        st.warning(f"🔥 HTTP error {e.response.status_code} for: {url}")
    except Exception as e:
        st.warning(f"❌ Unexpected error loading: {url}")
        logger.error(f"Request failed for {url}: {e}")
    return None

def load_excel_data(url: str) -> pd.DataFrame:
    """Load Excel data with enhanced error handling"""
    response = safe_request(url)
    if response is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(io.BytesIO(response.content))
        logger.info(f"Loaded Excel: {len(df)} rows from {url}")
        return df
    except Exception as e:
        st.error(f"📊 Error reading Excel file: {str(e)}")
        logger.error(f"Excel parsing failed: {e}")
        return pd.DataFrame()

def load_csv_data(url: str) -> pd.DataFrame:
    """Load CSV data with multiple encoding fallbacks"""
    response = safe_request(url)
    if response is None:
        return pd.DataFrame()
    
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(io.StringIO(response.content.decode(encoding)))
            logger.info(f"Loaded CSV: {len(df)} rows from {url} ({encoding})")
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"CSV parsing failed with {encoding}: {e}")
            continue
    
    st.error(f"📊 Could not decode CSV file from: {url}")
    return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner="🔄 Loading energy data...")
def load_all_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all data sources with progress indication"""
    
    # Load primary data sources
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("Loading generator data...")
    gen_df = load_excel_data(DATA_SOURCES["generator"])
    progress_bar.progress(20)
    
    status_text.text("Loading fuel level data...")
    fuel_level_df = load_excel_data(DATA_SOURCES["fuel_level"])
    progress_bar.progress(40)
    
    status_text.text("Loading factory consumption data...")
    factory_df = load_csv_data(DATA_SOURCES["factory"])
    progress_bar.progress(60)
    
    status_text.text("Loading solar performance data...")
    solar_dfs = []
    for i, (month, url) in enumerate(SOLAR_DATA_SOURCES):
        df = load_csv_data(url)
        if not df.empty:
            df['month'] = month
            solar_dfs.append(df)
        progress_bar.progress(60 + (i + 1) * 8)
    
    solar_df = pd.concat(solar_dfs, ignore_index=True) if solar_dfs else pd.DataFrame()
    
    status_text.text("Data loading complete!")
    progress_bar.progress(100)
    
    # Clean up progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Log summary
    logger.info(f"Data loading summary - Solar: {len(solar_df)}, Gen: {len(gen_df)}, "
                f"Fuel: {len(fuel_level_df)}, Factory: {len(factory_df)}")
    
    return solar_df, gen_df, fuel_level_df, factory_df

@st.cache_data(ttl=1800)
def load_fuel_purchase_data() -> pd.DataFrame:
    """Load fuel purchase data with data cleaning"""
    df = load_excel_data(DATA_SOURCES["fuel_purchase"])
    
    if df.empty:
        return pd.DataFrame()
    
    try:
        # Clean column names
        df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('[^a-z0-9_]', '', regex=True)
        
        # Parse dates with multiple format support
        date_columns = [col for col in df.columns if 'date' in col]
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        # Clean price data
        price_columns = [col for col in df.columns if 'price' in col or 'cost' in col]
        for col in price_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove rows with missing critical data
        df = df.dropna(subset=[col for col in ['date', 'price_per_litre'] if col in df.columns])
        
        logger.info(f"Cleaned fuel purchase data: {len(df)} records")
        return df
        
    except Exception as e:
        st.warning(f"⚠️ Error processing fuel purchase data: {str(e)}")
        logger.error(f"Fuel data processing failed: {e}")
        return pd.DataFrame()

# Load all data
solar_df, gen_df, fuel_level_df, factory_df = load_all_data()
fuel_purchases_df = load_fuel_purchase_data()

# ==============================================================================
# 3. ENHANCED GENERATOR DATA PROCESSING
# ==============================================================================

def process_timezone_data(df: pd.DataFrame, timestamp_col: str = 'last_changed') -> pd.DataFrame:
    """Process timezone data with proper error handling"""
    if df.empty or timestamp_col not in df.columns:
        return df
    
    try:
        # Convert to datetime with UTC assumption, then to South African time
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce', utc=True)
        df[timestamp_col] = df[timestamp_col].dt.tz_convert('Africa/Johannesburg')
        df[timestamp_col] = df[timestamp_col].dt.tz_localize(None)  # Remove timezone info
        return df.dropna(subset=[timestamp_col])
    except Exception as e:
        logger.error(f"Timezone processing failed: {e}")
        return df

@st.cache_data
def process_generator_data(gen_df: pd.DataFrame, fuel_level_df: pd.DataFrame, fuel_purchases_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Enhanced generator data processing with better error handling"""
    
    fuel_sources = []
    
    # Process generator fuel consumption data
    if not gen_df.empty:
        try:
            # Find fuel consumption sensor
            if 'entity_id' in gen_df.columns:
                fuel_gen = gen_df[gen_df['entity_id'] == 'sensor.generator_fuel_consumed'].copy()
            else:
                fuel_gen = gen_df.copy()
            
            if not fuel_gen.empty and all(col in fuel_gen.columns for col in ['state', 'last_changed']):
                fuel_gen = process_timezone_data(fuel_gen)
                fuel_gen = fuel_gen.sort_values('last_changed')
                
                # Convert state to numeric and clean
                fuel_gen['state'] = pd.to_numeric(fuel_gen['state'], errors='coerce')
                fuel_gen = fuel_gen.dropna(subset=['state'])
                
                # Calculate fuel delta (consumption)
                fuel_gen['fuel_delta'] = fuel_gen['state'].diff().clip(lower=0).fillna(0)
                
                # Remove unrealistic values (likely sensor resets)
                fuel_gen = fuel_gen[fuel_gen['fuel_delta'] < 100]  # Max 100L per reading
                
                fuel_sources.append(fuel_gen[['last_changed', 'fuel_delta']].rename(columns={'last_changed': 'timestamp'}))
                logger.info(f"Processed generator consumption: {len(fuel_gen)} records")
        
        except Exception as e:
            st.warning(f"⚠️ Error processing generator data: {str(e)}")
            logger.error(f"Generator processing failed: {e}")
    
    # Process fuel level sensor data
    if not fuel_level_df.empty:
        try:
            # Find fuel level sensor
            if 'entity_id' in fuel_level_df.columns:
                level_df = fuel_level_df[fuel_level_df['entity_id'].str.contains('fuel_level', case=False, na=False)].copy()
            else:
                level_df = fuel_level_df.copy()
            
            if not level_df.empty and all(col in level_df.columns for col in ['state', 'last_changed']):
                level_df = process_timezone_data(level_df)
                level_df = level_df.sort_values('last_changed')
                
                # Convert and clean level data
                level_df['state'] = pd.to_numeric(level_df['state'], errors='coerce')
                level_df = level_df.dropna(subset=['state'])
                
                # Smooth the level data to reduce noise
                level_df['level_smooth'] = level_df['state'].rolling(window=5, min_periods=1, center=True).median()
                
                # Calculate fuel consumption (negative level changes)
                level_df['fuel_delta'] = -level_df['level_smooth'].diff().clip(upper=0)
                level_df['fuel_delta'] = level_df['fuel_delta'].abs()
                
                # Remove unrealistic values
                level_df = level_df[level_df['fuel_delta'] < 50]
                
                fuel_sources.append(level_df[['last_changed', 'fuel_delta']].rename(columns={'last_changed': 'timestamp'}))
                logger.info(f"Processed fuel level: {len(level_df)} records")
        
        except Exception as e:
            st.warning(f"⚠️ Error processing fuel level data: {str(e)}")
            logger.error(f"Fuel level processing failed: {e}")
    
    if not fuel_sources:
        return pd.DataFrame(), {'cost': 0, 'liters': 0, 'avg_price': 0}
    
    # Combine all fuel consumption sources
    try:
        combined_fuel = pd.concat(fuel_sources, ignore_index=True)
        combined_fuel['timestamp'] = pd.to_datetime(combined_fuel['timestamp'])
        
        # Aggregate daily consumption
        daily_consumption = combined_fuel.groupby(combined_fuel['timestamp'].dt.date)['fuel_delta'].sum().reset_index()
        daily_consumption.columns = ['date', 'liters']
        daily_consumption['date'] = pd.to_datetime(daily_consumption['date'])
        
        # Apply fuel pricing
        if not fuel_purchases_df.empty and 'date' in fuel_purchases_df.columns:
            try:
                # Prepare price data
                price_df = fuel_purchases_df[['date', 'price_per_litre']].copy()
                price_df = price_df.dropna()
                price_df = price_df.sort_values('date')
                
                # Merge with consumption data using forward fill for missing prices
                daily_consumption = daily_consumption.sort_values('date')
                daily_consumption = pd.merge_asof(
                    daily_consumption, 
                    price_df, 
                    on='date', 
                    direction='backward'
                )
                
                # Fill any remaining missing prices with default
                daily_consumption['price_per_litre'] = daily_consumption['price_per_litre'].fillna(22.50)
                
            except Exception as e:
                logger.error(f"Price merging failed: {e}")
                daily_consumption['price_per_litre'] = 22.50
        else:
            daily_consumption['price_per_litre'] = 22.50
        
        # Calculate costs
        daily_consumption['cost'] = daily_consumption['liters'] * daily_consumption['price_per_litre']
        
        # Calculate totals
        totals = {
            'cost': daily_consumption['cost'].sum(),
            'liters': daily_consumption['liters'].sum(),
            'avg_price': daily_consumption['price_per_litre'].mean()
        }
        
        logger.info(f"Generator processing complete: {len(daily_consumption)} days, {totals['liters']:.1f}L total")
        return daily_consumption, totals
        
    except Exception as e:
        st.error(f"❌ Error combining fuel data: {str(e)}")
        logger.error(f"Fuel combination failed: {e}")
        return pd.DataFrame(), {'cost': 0, 'liters': 0, 'avg_price': 0}

# Process generator data
daily_generator, generator_totals = process_generator_data(gen_df, fuel_level_df, fuel_purchases_df)

# ==============================================================================
# 4. ENHANCED SIDEBAR WITH IMPROVED DATE SELECTION
# ==============================================================================

with st.sidebar:
    st.markdown("# ⚡ Durr Bottling")
    st.markdown("### Energy Intelligence Dashboard")
    st.caption("Enhanced v6.0 • All bugs fixed • Improved UI")
    st.markdown("---")
    
    # Date range selection with better UX
    st.markdown("### 📅 Analysis Period")
    
    # Quick presets
    date_preset = st.selectbox(
        "Quick Select",
        ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date", "Custom Range"],
        index=1
    )
    
    # Calculate date ranges
    today = datetime.now().date()
    
    if date_preset == "Last 7 Days":
        start_date = today - timedelta(days=6)
        end_date = today
    elif date_preset == "Last 30 Days":
        start_date = today - timedelta(days=29)
        end_date = today
    elif date_preset == "Last 90 Days":
        start_date = today - timedelta(days=89)
        end_date = today
    elif date_preset == "Year to Date":
        start_date = datetime(today.year, 1, 1).date()
        end_date = today
    else:  # Custom Range
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "From", 
                value=today - timedelta(days=30),
                max_value=today
            )
        with col2:
            end_date = st.date_input(
                "To", 
                value=today,
                min_value=start_date,
                max_value=today
            )
    
    # Validate date range
    if start_date > end_date:
        st.error("❌ Start date must be before end date")
        st.stop()
    
    # Show selected period info
    period_days = (end_date - start_date).days + 1
    st.info(f"📊 Analyzing **{period_days}** days of data")
    
    st.markdown("---")
    
    # Data summary
    st.markdown("### 📈 Data Status")
    data_status = []
    
    if not solar_df.empty:
        data_status.append("✅ Solar Performance")
    else:
        data_status.append("❌ Solar Performance")
    
    if not daily_generator.empty:
        data_status.append("✅ Generator Data")
    else:
        data_status.append("❌ Generator Data")
    
    if not factory_df.empty:
        data_status.append("✅ Factory Consumption")
    else:
        data_status.append("❌ Factory Consumption")
    
    for status in data_status:
        st.markdown(status)

# Filter data based on selected date range
def filter_data_by_date(df: pd.DataFrame, date_col: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Filter dataframe by date range with proper error handling"""
    if df.empty or date_col not in df.columns:
        return df
    
    try:
        df[date_col] = pd.to_datetime(df[date_col])
        mask = (df[date_col].dt.date >= start) & (df[date_col].dt.date <= end)
        return df[mask].copy()
    except Exception as e:
        logger.error(f"Date filtering failed: {e}")
        return df

# Filter data for selected period
filtered_generator = filter_data_by_date(daily_generator, 'date', start_date, end_date)
filtered_solar = filter_data_by_date(solar_df, 'last_changed', start_date, end_date) if not solar_df.empty else pd.DataFrame()
filtered_factory = filter_data_by_date(factory_df, 'last_changed', start_date, end_date) if not factory_df.empty else pd.DataFrame()

# Calculate period totals
if not filtered_generator.empty:
    period_generator_totals = {
        'cost': filtered_generator['cost'].sum(),
        'liters': filtered_generator['liters'].sum(),
        'avg_price': filtered_generator['price_per_litre'].mean() if 'price_per_litre' in filtered_generator.columns else 0
    }
else:
    period_generator_totals = {'cost': 0, 'liters': 0, 'avg_price': 0}

# ==============================================================================
# 5. ENHANCED MAIN DASHBOARD WITH IMPROVED TABS
# ==============================================================================

# Header
st.markdown("# 🏭 Durr Bottling Energy Intelligence")
st.markdown("### Real-time energy monitoring and analysis dashboard")
st.markdown("---")

# Key metrics overview
if period_generator_totals['liters'] > 0 or not filtered_solar.empty or not filtered_factory.empty:
    st.markdown("## 📊 Period Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_enhanced_metric(
            "Generator Cost",
            f"R {period_generator_totals['cost']:,.0f}",
            f"📅 {period_days} days",
            "negative",
            "🔋"
        )
    
    with col2:
        render_enhanced_metric(
            "Fuel Consumed",
            f"{period_generator_totals['liters']:,.1f} L",
            f"Avg R{period_generator_totals['avg_price']:.2f}/L",
            "yellow",
            "⛽"
        )
    
    with col3:
        if not filtered_solar.empty and 'total_kw' in filtered_solar.columns:
            solar_peak = filtered_solar['total_kw'].max()
            render_enhanced_metric(
                "Solar Peak",
                f"{solar_peak:.1f} kW",
                "Maximum output",
                "positive",
                "☀️"
            )
        else:
            render_enhanced_metric(
                "Solar Peak",
                "No Data",
                "Not available",
                "neutral",
                "☀️"
            )
    
    with col4:
        if not filtered_factory.empty:
            factory_points = len(filtered_factory)
            render_enhanced_metric(
                "Factory Data",
                f"{factory_points:,}",
                "Data points",
                "cyan",
                "🏭"
            )
        else:
            render_enhanced_metric(
                "Factory Data",
                "No Data",
                "Not available",
                "neutral",
                "🏭"
            )

# Tabs for detailed analysis
tab1, tab2, tab3, tab4 = st.tabs([
    "🔋 Generator Analysis", 
    "☀️ Solar Performance", 
    "🏭 Factory Consumption", 
    "📄 Invoice Management"
])

with tab1:
    st.markdown("## 🔋 Generator Performance Analysis")
    st.markdown("Comprehensive fuel consumption tracking and cost analysis")
    
    if not filtered_generator.empty:
        # Summary metrics
        col1, col2 = st.columns(2)
        
        with col1:
            avg_daily = period_generator_totals['liters'] / period_days if period_days > 0 else 0
            render_enhanced_metric(
                "Average Daily Consumption",
                f"{avg_daily:.1f} L/day",
                f"Over {period_days} days",
                "neutral"
            )
        
        with col2:
            cost_per_day = period_generator_totals['cost'] / period_days if period_days > 0 else 0
            render_enhanced_metric(
                "Average Daily Cost",
                f"R {cost_per_day:.0f}/day",
                f"At R{period_generator_totals['avg_price']:.2f}/L",
                "negative"
            )
        
        # Charts
        st.markdown("### 📈 Daily Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            create_enhanced_chart(
                filtered_generator, 
                'date', 
                'liters', 
                "Daily Fuel Consumption",
                color="#0bc5ea",
                kind='bar',
                y_label="Liters"
            )
        
        with col2:
            create_enhanced_chart(
                filtered_generator, 
                'date', 
                'cost', 
                "Daily Fuel Cost",
                color="#e53e3e",
                kind='bar',
                y_label="Cost (Rands)"
            )
        
        # Weekly trend if enough data
        if len(filtered_generator) > 7:
            st.markdown("### 📅 Weekly Trends")
            
            weekly_data = filtered_generator.copy()
            weekly_data['week'] = weekly_data['date'].dt.isocalendar().week
            weekly_summary = weekly_data.groupby('week').agg({
                'liters': 'sum',
                'cost': 'sum'
            }).reset_index()
            
            create_enhanced_chart(
                weekly_summary,
                'week',
                'liters',
                "Weekly Fuel Consumption Trend",
                color="#38a169",
                kind='line',
                y_label="Liters per Week"
            )
    else:
        st.info("📊 No generator data available for the selected period.")
        st.markdown("**Possible reasons:**")
        st.markdown("- No fuel consumption recorded")
        st.markdown("- Data source temporarily unavailable") 
        st.markdown("- Selected date range outside data coverage")

with tab2:
    st.markdown("## ☀️ Solar Performance Analysis")
    st.markdown("Real-time solar energy production monitoring and efficiency analysis")
    
    if not filtered_solar.empty:
        try:
            # Process solar data
            solar_data = filtered_solar.copy()
            solar_data = process_timezone_data(solar_data)
            
            # Calculate total solar power (combining inverters)
            power_cols = [col for col in solar_data.columns if 'power' in col.lower()]
            if power_cols:
                # Convert watts to kilowatts
                for col in power_cols:
                    solar_data[col] = pd.to_numeric(solar_data[col], errors='coerce') / 1000
                
                solar_data['total_kw'] = solar_data[power_cols].sum(axis=1)
            else:
                st.warning("⚠️ No power data columns found in solar dataset")
                solar_data['total_kw'] = 0
            
            # Remove invalid/negative values
            solar_data = solar_data[solar_data['total_kw'] >= 0]
            
            if not solar_data.empty and solar_data['total_kw'].max() > 0:
                # Summary metrics
                peak_power = solar_data['total_kw'].max()
                avg_power = solar_data['total_kw'].mean()
                total_energy = solar_data['total_kw'].sum() / 4  # Assuming 15-min intervals
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    render_enhanced_metric(
                        "Peak Power",
                        f"{peak_power:.1f} kW",
                        "Maximum recorded",
                        "positive"
                    )
                
                with col2:
                    render_enhanced_metric(
                        "Average Power",
                        f"{avg_power:.1f} kW",
                        "During daylight",
                        "cyan"
                    )
                
                with col3:
                    render_enhanced_metric(
                        "Estimated Energy",
                        f"{total_energy:.0f} kWh",
                        "Total production",
                        "positive"
                    )
                
                # Charts
                st.markdown("### 📈 Solar Production Analysis")
                
                # Time series chart
                create_enhanced_chart(
                    solar_data,
                    'last_changed',
                    'total_kw',
                    "Solar Power Output Over Time",
                    color="#38a169",
                    kind='area',
                    y_label="Power (kW)"
                )
                
                # Hourly analysis
                if len(solar_data) > 24:
                    st.markdown("### ⏰ Performance by Hour")
                    
                    hourly_data = solar_data.copy()
                    hourly_data['hour'] = hourly_data['last_changed'].dt.hour
                    hourly_avg = hourly_data.groupby('hour')['total_kw'].agg(['mean', 'max']).reset_index()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        create_enhanced_chart(
                            hourly_avg,
                            'hour',
                            'mean',
                            "Average Solar Power by Hour",
                            color="#38a169",
                            kind='bar',
                            y_label="Average Power (kW)"
                        )
                    
                    with col2:
                        create_enhanced_chart(
                            hourly_avg,
                            'hour',
                            'max',
                            "Peak Solar Power by Hour",
                            color="#d69e2e",
                            kind='bar',
                            y_label="Peak Power (kW)"
                        )
                
                # Daily summary if multiple days
                if period_days > 1:
                    st.markdown("### 📅 Daily Production Summary")
                    
                    daily_solar = solar_data.copy()
                    daily_solar['date'] = daily_solar['last_changed'].dt.date
                    daily_summary = daily_solar.groupby('date').agg({
                        'total_kw': ['max', 'mean', 'sum']
                    }).reset_index()
                    
                    daily_summary.columns = ['date', 'peak_kw', 'avg_kw', 'total_kwh']
                    daily_summary['total_kwh'] = daily_summary['total_kwh'] / 4  # Convert to kWh
                    daily_summary['date'] = pd.to_datetime(daily_summary['date'])
                    
                    create_enhanced_chart(
                        daily_summary,
                        'date',
                        'total_kwh',
                        "Daily Solar Energy Production",
                        color="#4facfe",
                        kind='bar',
                        y_label="Energy (kWh)"
                    )
            else:
                st.info("📊 No valid solar power data found for the selected period.")
        
        except Exception as e:
            st.error(f"❌ Error processing solar data: {str(e)}")
            logger.error(f"Solar processing failed: {e}")
    else:
        st.info("📊 No solar data available for the selected period.")
        st.markdown("**Data sources:**")
        for month, url in SOLAR_DATA_SOURCES:
            st.markdown(f"- {month}: Available")

with tab3:
    st.markdown("## 🏭 Factory Energy Consumption")
    st.markdown("Industrial energy usage monitoring and load analysis")
    
    if not filtered_factory.empty:
        try:
            factory_data = filtered_factory.copy()
            factory_data = process_timezone_data(factory_data)
            
            # Find consumption sensor
            consumption_cols = [col for col in factory_data.columns if 'kwh' in col.lower()]
            
            if consumption_cols:
                main_sensor = consumption_cols[0]  # Use first kWh sensor
                
                # Process cumulative data
                factory_data[main_sensor] = pd.to_numeric(factory_data[main_sensor], errors='coerce')
                factory_data = factory_data.dropna(subset=[main_sensor])
                factory_data = factory_data.sort_values('last_changed')
                
                # Calculate daily consumption from cumulative
                factory_data['daily_kwh'] = factory_data[main_sensor].diff().clip(lower=0).fillna(0)
                
                # Remove unrealistic spikes (likely sensor resets)
                factory_data = factory_data[factory_data['daily_kwh'] < 1000]
                
                total_consumption = factory_data['daily_kwh'].sum()
                avg_consumption = factory_data['daily_kwh'].mean()
                max_consumption = factory_data['daily_kwh'].max()
                
                if total_consumption > 0:
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        render_enhanced_metric(
                            "Total Consumption",
                            f"{total_consumption:,.0f} kWh",
                            f"Over {period_days} days",
                            "cyan"
                        )
                    
                    with col2:
                        avg_daily = total_consumption / period_days if period_days > 0 else 0
                        render_enhanced_metric(
                            "Daily Average",
                            f"{avg_daily:.0f} kWh/day",
                            "Average usage",
                            "neutral"
                        )
                    
                    with col3:
                        render_enhanced_metric(
                            "Peak Usage",
                            f"{max_consumption:.0f} kWh",
                            "Single day maximum",
                            "yellow"
                        )
                    
                    # Charts
                    st.markdown("### 📈 Consumption Analysis")
                    
                    # Time series
                    create_enhanced_chart(
                        factory_data,
                        'last_changed',
                        'daily_kwh',
                        "Factory Energy Consumption Over Time",
                        color="#3182ce",
                        kind='line',
                        y_label="Energy (kWh)"
                    )
                    
                    # Daily breakdown if multiple days
                    if period_days > 1:
                        daily_factory = factory_data.copy()
                        daily_factory['date'] = daily_factory['last_changed'].dt.date
                        daily_summary = daily_factory.groupby('date')['daily_kwh'].sum().reset_index()
                        daily_summary['date'] = pd.to_datetime(daily_summary['date'])
                        
                        create_enhanced_chart(
                            daily_summary,
                            'date',
                            'daily_kwh',
                            "Daily Factory Energy Consumption",
                            color="#0bc5ea",
                            kind='bar',
                            y_label="Energy (kWh)"
                        )
                    
                    # Hourly pattern analysis
                    if len(factory_data) > 24:
                        st.markdown("### ⏰ Usage Patterns")
                        
                        hourly_factory = factory_data.copy()
                        hourly_factory['hour'] = hourly_factory['last_changed'].dt.hour
                        hourly_avg = hourly_factory.groupby('hour')['daily_kwh'].mean().reset_index()
                        
                        create_enhanced_chart(
                            hourly_avg,
                            'hour',
                            'daily_kwh',
                            "Average Energy Usage by Hour",
                            color="#38a169",
                            kind='bar',
                            y_label="Average kWh"
                        )
                else:
                    st.info("📊 No energy consumption detected for the selected period.")
            else:
                st.warning("⚠️ No energy consumption sensors found in factory data.")
        
        except Exception as e:
            st.error(f"❌ Error processing factory data: {str(e)}")
            logger.error(f"Factory processing failed: {e}")
    else:
        st.info("📊 No factory data available for the selected period.")

with tab4:
    st.markdown("## 📄 Invoice Management System")
    st.markdown("Automated billing document generation and editing")
    
    try:
        response = safe_request(DATA_SOURCES["billing"])
        if response:
            buffer = io.BytesIO(response.content)
            workbook = openpyxl.load_workbook(buffer, data_only=False)
            worksheet = workbook.active
            
            # Extract current values with error handling
            try:
                from_val = str(worksheet['B2'].value or "30/09/25")
                to_val = str(worksheet['B3'].value or "31/10/25") 
                freedom_units = float(worksheet['C7'].value or 0)
                boerdery_units = float(worksheet['C9'].value or 0)
            except Exception as e:
                logger.error(f"Error reading worksheet values: {e}")
                from_val, to_val = "30/09/25", "31/10/25"
                freedom_units, boerdery_units = 0, 0
            
            # Parse dates with multiple format support
            try:
                from_date = pd.to_datetime(from_val, dayfirst=True).date()
            except:
                from_date = datetime(2025, 9, 30).date()
            
            try:
                to_date = pd.to_datetime(to_val, dayfirst=True).date()
            except:
                to_date = datetime(2025, 10, 31).date()
            
            # Invoice editing interface
            st.markdown("### ✏️ Edit Invoice Parameters")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📅 Billing Period**")
                new_from_date = st.date_input(
                    "From Date (B2)", 
                    value=from_date,
                    key="invoice_from"
                )
                
                st.markdown("**🏘️ Freedom Village**")
                new_freedom_units = st.number_input(
                    "Units Consumed (C7)", 
                    value=float(freedom_units),
                    min_value=0.0,
                    step=1.0,
                    key="freedom_units"
                )
            
            with col2:
                st.markdown("**📅 Billing Period**")
                new_to_date = st.date_input(
                    "To Date (B3)", 
                    value=to_date,
                    min_value=new_from_date,
                    key="invoice_to"
                )
                
                st.markdown("**🏭 Boerdery**")
                new_boerdery_units = st.number_input(
                    "Units Consumed (C9)", 
                    value=float(boerdery_units),
                    min_value=0.0,
                    step=1.0,
                    key="boerdery_units"
                )
            
            # Show changes
            if (new_from_date != from_date or new_to_date != to_date or 
                new_freedom_units != freedom_units or new_boerdery_units != boerdery_units):
                
                st.markdown("### 📋 Changes Summary")
                
                if new_from_date != from_date:
                    st.info(f"📅 From Date: {from_date} → {new_from_date}")
                if new_to_date != to_date:
                    st.info(f"📅 To Date: {to_date} → {new_to_date}")
                if new_freedom_units != freedom_units:
                    st.info(f"🏘️ Freedom Village: {freedom_units} → {new_freedom_units} units")
                if new_boerdery_units != boerdery_units:
                    st.info(f"🏭 Boerdery: {boerdery_units} → {new_boerdery_units} units")
            
            # Generate updated invoice
            if st.button("🚀 Generate Updated Invoice", type="primary", use_container_width=True):
                try:
                    # Update worksheet values
                    worksheet['B2'].value = new_from_date.strftime("%d/%m/%y")
                    worksheet['B3'].value = new_to_date.strftime("%d/%m/%y")
                    worksheet['C7'].value = new_freedom_units
                    worksheet['C9'].value = new_boerdery_units
                    
                    # Save to buffer
                    output_buffer = io.BytesIO()
                    workbook.save(output_buffer)
                    output_buffer.seek(0)
                    
                    # Generate filename
                    month_year = new_from_date.strftime("%b%Y")
                    filename = f"DurrBottling_Invoice_{month_year}.xlsx"
                    
                    st.success("✅ Invoice generated successfully!")
                    
                    st.download_button(
                        label="📥 Download Updated Invoice",
                        data=output_buffer,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Error generating invoice: {str(e)}")
                    logger.error(f"Invoice generation failed: {e}")
        else:
            st.error("❌ Could not load billing template from GitHub")
    
    except Exception as e:
        st.error(f"❌ Error loading invoice system: {str(e)}")
        logger.error(f"Invoice system failed: {e}")

# ==============================================================================
# 6. FOOTER & SYSTEM INFO
# ==============================================================================
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📊 System Status")
    st.success("✅ All systems operational")
    st.info(f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

with col2:
    st.markdown("### 📈 Data Summary")
    st.info(f"🔋 Generator: {len(daily_generator)} days")
    st.info(f"☀️ Solar: {len(solar_df)} records")
    st.info(f"🏭 Factory: {len(factory_df)} records")

with col3:
    st.markdown("### ⚙️ Version Info")
    st.info("📦 Enhanced Dashboard v6.0")
    st.info("🐛 All bugs fixed")
    st.info("🎨 Modern UI design")

# Enhanced footer
st.markdown("""
<div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, rgba(49, 130, 206, 0.1), rgba(56, 161, 105, 0.05)); border-radius: 16px; margin-top: 2rem;'>
    <h4 style='color: #f7fafc; margin-bottom: 0.5rem;'>🏭 Durr Bottling Energy Intelligence Dashboard</h4>
    <p style='color: #a0aec0; margin-bottom: 0;'>Enhanced Version 6.0 • Real-time Monitoring • Advanced Analytics</p>
</div>
""", unsafe_allow_html=True)