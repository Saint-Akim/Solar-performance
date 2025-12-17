"""
Advanced Customization Features for Solar Performance Dashboard
==============================================================
Theme management, branding, and personalization options
"""

import streamlit as st
import json
from typing import Dict, List, Any
from datetime import datetime

class ThemeManager:
    """Manage dashboard themes and styling"""
    
    THEMES = {
        "default": {
            "name": "Default Dark",
            "colors": {
                "primary": "#3182ce",
                "secondary": "#38a169", 
                "background": "#0f1419",
                "card": "#1a1f2e",
                "text": "#f7fafc",
                "accent": "#0bc5ea"
            }
        },
        "corporate_blue": {
            "name": "Corporate Blue",
            "colors": {
                "primary": "#1e40af",
                "secondary": "#3b82f6",
                "background": "#0f172a",
                "card": "#1e293b",
                "text": "#f1f5f9",
                "accent": "#38bdf8"
            }
        },
        "energy_green": {
            "name": "Energy Green",
            "colors": {
                "primary": "#166534",
                "secondary": "#22c55e",
                "background": "#0c1410",
                "card": "#1a2e1a",
                "text": "#f0fdf4",
                "accent": "#4ade80"
            }
        },
        "industrial_orange": {
            "name": "Industrial Orange",
            "colors": {
                "primary": "#ea580c",
                "secondary": "#fb923c",
                "background": "#1c1917",
                "card": "#292524",
                "text": "#fafaf9",
                "accent": "#f97316"
            }
        },
        "royal_purple": {
            "name": "Royal Purple", 
            "colors": {
                "primary": "#7c3aed",
                "secondary": "#a855f7",
                "background": "#1e1b3a",
                "card": "#2d2a4a",
                "text": "#f3f4f6",
                "accent": "#c084fc"
            }
        }
    }
    
    @classmethod
    def get_theme_css(cls, theme_name: str) -> str:
        """Generate CSS for selected theme"""
        theme = cls.THEMES.get(theme_name, cls.THEMES["default"])
        colors = theme["colors"]
        
        return f"""
        <style>
            :root {{
                --primary-color: {colors['primary']};
                --secondary-color: {colors['secondary']};
                --background-color: {colors['background']};
                --card-color: {colors['card']};
                --text-color: {colors['text']};
                --accent-color: {colors['accent']};
            }}
            
            .stApp {{
                background: var(--background-color);
                color: var(--text-color);
            }}
            
            .theme-preview {{
                background: var(--card-color);
                border: 2px solid var(--primary-color);
                border-radius: 12px;
                padding: 1rem;
                margin: 0.5rem 0;
                transition: all 0.3s ease;
            }}
            
            .theme-preview:hover {{
                transform: scale(1.02);
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }}
            
            .color-swatch {{
                width: 30px;
                height: 30px;
                border-radius: 50%;
                display: inline-block;
                margin: 0 5px;
                border: 2px solid var(--text-color);
            }}
        </style>
        """
    
    @classmethod
    def create_theme_selector(cls):
        """Create theme selection interface"""
        st.markdown("### 🎨 Theme Selection")
        
        current_theme = st.session_state.get('selected_theme', 'default')
        
        # Theme preview grid
        cols = st.columns(2)
        
        for i, (theme_key, theme_data) in enumerate(cls.THEMES.items()):
            col = cols[i % 2]
            
            with col:
                colors = theme_data["colors"]
                
                # Create theme preview
                preview_html = f"""
                <div class="theme-preview" style="
                    background: {colors['card']};
                    border: 2px solid {colors['primary']};
                    color: {colors['text']};
                ">
                    <h4 style="margin: 0 0 0.5rem 0;">{theme_data['name']}</h4>
                    <div style="margin-bottom: 0.5rem;">
                        <span class="color-swatch" style="background: {colors['primary']};"></span>
                        <span class="color-swatch" style="background: {colors['secondary']};"></span>
                        <span class="color-swatch" style="background: {colors['accent']};"></span>
                    </div>
                    <small>Primary • Secondary • Accent</small>
                </div>
                """
                
                st.markdown(preview_html, unsafe_allow_html=True)
                
                if st.button(f"Apply {theme_data['name']}", key=f"theme_{theme_key}"):
                    st.session_state.selected_theme = theme_key
                    st.success(f"✅ Applied {theme_data['name']} theme!")
                    st.experimental_rerun()
        
        # Apply selected theme
        selected_theme = st.session_state.get('selected_theme', 'default')
        st.markdown(cls.get_theme_css(selected_theme), unsafe_allow_html=True)
        
        return selected_theme

class BrandingManager:
    """Manage company branding and customization"""
    
    @staticmethod
    def create_branding_config():
        """Create branding configuration interface"""
        st.markdown("### 🏢 Company Branding")
        
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input(
                "Company Name", 
                value=st.session_state.get('company_name', 'Durr Bottling'),
                help="Your company name for the dashboard header"
            )
            
            tagline = st.text_input(
                "Tagline",
                value=st.session_state.get('tagline', 'Energy Intelligence Dashboard'),
                help="Subtitle displayed under company name"
            )
            
            contact_email = st.text_input(
                "Contact Email",
                value=st.session_state.get('contact_email', 'info@durrbottling.com'),
                help="Contact email for support"
            )
        
        with col2:
            logo_option = st.selectbox(
                "Logo Option",
                ["Text Only", "Upload Image", "Use Icon"],
                help="Choose how to display your company logo"
            )
            
            if logo_option == "Upload Image":
                logo_file = st.file_uploader("Upload Logo", type=['png', 'jpg', 'svg'])
                if logo_file:
                    st.image(logo_file, width=200)
            elif logo_option == "Use Icon":
                selected_icon = st.selectbox(
                    "Select Icon",
                    ["⚡", "🏭", "🔋", "☀️", "🌱", "🔧", "📊"]
                )
                st.markdown(f"Preview: {selected_icon}")
        
        # Save branding settings
        if st.button("Save Branding Settings"):
            st.session_state.company_name = company_name
            st.session_state.tagline = tagline
            st.session_state.contact_email = contact_email
            st.session_state.logo_option = logo_option
            if logo_option == "Use Icon":
                st.session_state.selected_icon = selected_icon
            
            st.success("✅ Branding settings saved!")
    
    @staticmethod
    def apply_branding():
        """Apply saved branding to the dashboard"""
        company_name = st.session_state.get('company_name', 'Durr Bottling')
        tagline = st.session_state.get('tagline', 'Energy Intelligence Dashboard')
        logo_option = st.session_state.get('logo_option', 'Text Only')
        
        if logo_option == "Use Icon":
            icon = st.session_state.get('selected_icon', '⚡')
            header_html = f"""
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">
                    {icon} {company_name}
                </h1>
                <p style="color: #94a3b8; font-size: 1.2rem;">{tagline}</p>
            </div>
            """
        else:
            header_html = f"""
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">{company_name}</h1>
                <p style="color: #94a3b8; font-size: 1.2rem;">{tagline}</p>
            </div>
            """
        
        st.markdown(header_html, unsafe_allow_html=True)

class DashboardCustomizer:
    """Manage dashboard layout and feature customization"""
    
    DEFAULT_CONFIG = {
        "show_sidebar_stats": True,
        "enable_auto_refresh": False,
        "refresh_interval": 15,
        "default_date_range": "Last 30 Days",
        "show_performance_score": True,
        "enable_email_alerts": False,
        "alert_thresholds": {
            "high_consumption": 100,
            "low_efficiency": 70,
            "maintenance_due": 500
        }
    }
    
    @classmethod
    def create_customization_interface(cls):
        """Create dashboard customization interface"""
        st.markdown("### ⚙️ Dashboard Configuration")
        
        # Load current config
        config = st.session_state.get('dashboard_config', cls.DEFAULT_CONFIG.copy())
        
        # Layout options
        st.markdown("#### 📱 Layout Options")
        col1, col2 = st.columns(2)
        
        with col1:
            config['show_sidebar_stats'] = st.checkbox(
                "Show Sidebar Statistics",
                value=config.get('show_sidebar_stats', True),
                help="Display quick stats in sidebar"
            )
            
            config['show_performance_score'] = st.checkbox(
                "Show Performance Score",
                value=config.get('show_performance_score', True),
                help="Display overall performance metrics"
            )
        
        with col2:
            config['default_date_range'] = st.selectbox(
                "Default Date Range",
                ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date"],
                index=["Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date"].index(
                    config.get('default_date_range', 'Last 30 Days')
                ),
                help="Default time period for analysis"
            )
        
        # Auto-refresh settings
        st.markdown("#### 🔄 Auto-Refresh Settings")
        col1, col2 = st.columns(2)
        
        with col1:
            config['enable_auto_refresh'] = st.checkbox(
                "Enable Auto-Refresh",
                value=config.get('enable_auto_refresh', False),
                help="Automatically refresh data"
            )
        
        with col2:
            config['refresh_interval'] = st.slider(
                "Refresh Interval (minutes)",
                min_value=5,
                max_value=60,
                value=config.get('refresh_interval', 15),
                help="How often to refresh data"
            )
        
        # Alert settings
        st.markdown("#### 🚨 Alert Configuration")
        config['enable_email_alerts'] = st.checkbox(
            "Enable Email Alerts",
            value=config.get('enable_email_alerts', False),
            help="Send email notifications for alerts"
        )
        
        if config['enable_email_alerts']:
            email_address = st.text_input(
                "Alert Email Address",
                value=st.session_state.get('alert_email', ''),
                help="Email address for alert notifications"
            )
            st.session_state.alert_email = email_address
        
        # Alert thresholds
        st.markdown("##### Alert Thresholds")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            config['alert_thresholds']['high_consumption'] = st.number_input(
                "High Consumption (L/day)",
                value=config.get('alert_thresholds', {}).get('high_consumption', 100),
                min_value=10,
                max_value=500,
                help="Alert when daily consumption exceeds this"
            )
        
        with col2:
            config['alert_thresholds']['low_efficiency'] = st.number_input(
                "Low Efficiency (%)",
                value=config.get('alert_thresholds', {}).get('low_efficiency', 70),
                min_value=30,
                max_value=95,
                help="Alert when efficiency falls below this"
            )
        
        with col3:
            config['alert_thresholds']['maintenance_due'] = st.number_input(
                "Maintenance Hours",
                value=config.get('alert_thresholds', {}).get('maintenance_due', 500),
                min_value=100,
                max_value=1000,
                help="Alert when maintenance is due"
            )
        
        # Save configuration
        if st.button("Save Configuration"):
            st.session_state.dashboard_config = config
            st.success("✅ Dashboard configuration saved!")
            st.experimental_rerun()
        
        # Export/Import configuration
        st.markdown("#### 📁 Configuration Management")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export Configuration"):
                config_json = json.dumps(config, indent=2)
                st.download_button(
                    label="📥 Download Config",
                    data=config_json,
                    file_name=f"dashboard_config_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
        
        with col2:
            uploaded_config = st.file_uploader("Import Configuration", type=['json'])
            if uploaded_config:
                try:
                    imported_config = json.load(uploaded_config)
                    st.session_state.dashboard_config = imported_config
                    st.success("✅ Configuration imported successfully!")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Error importing configuration: {e}")

def create_customization_dashboard():
    """Create the main customization dashboard"""
    
    st.markdown("# 🎨 Dashboard Customization")
    st.markdown("Personalize your energy intelligence dashboard")
    st.markdown("---")
    
    # Customization tabs
    tab1, tab2, tab3 = st.tabs(["🎨 Themes", "🏢 Branding", "⚙️ Settings"])
    
    with tab1:
        ThemeManager.create_theme_selector()
    
    with tab2:
        BrandingManager.create_branding_config()
    
    with tab3:
        DashboardCustomizer.create_customization_interface()
    
    # Preview section
    st.markdown("---")
    st.markdown("## 👁️ Live Preview")
    
    # Apply current branding
    BrandingManager.apply_branding()
    
    # Show sample metrics with current theme
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Sample Metric", "1,250 kWh", "+12%")
    
    with col2:
        st.metric("Efficiency", "78.5%", "+2.3%")
    
    with col3:
        st.metric("Cost Savings", "R 5,420", "+15%")
    
    # Reset to defaults
    st.markdown("---")
    if st.button("🔄 Reset to Defaults"):
        # Clear all customization settings
        keys_to_clear = [
            'selected_theme', 'company_name', 'tagline', 'contact_email',
            'logo_option', 'selected_icon', 'dashboard_config', 'alert_email'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        st.success("✅ Reset to default settings!")
        st.experimental_rerun()

if __name__ == "__main__":
    create_customization_dashboard()