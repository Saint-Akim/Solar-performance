# 🎨 Customization Guide - Solar Performance Dashboard

## 🎯 Overview

This guide shows you how to customize the Durr Bottling Energy Dashboard to match your specific needs, branding, and requirements.

## 🎨 Visual Customization

### Color Themes

#### Custom Color Palette
```python
# In app_fixed.py, modify the CSS variables:
CUSTOM_THEME = """
:root {
    --bg-primary: #your_bg_color;
    --text-primary: #your_text_color;
    --accent-blue: #your_brand_color;
    --accent-green: #your_success_color;
}
"""
```

#### Pre-built Themes
```python
THEMES = {
    "corporate_blue": {
        "primary": "#1e40af", "secondary": "#3b82f6",
        "bg": "#0f172a", "text": "#f1f5f9"
    },
    "energy_green": {
        "primary": "#166534", "secondary": "#22c55e", 
        "bg": "#0c1410", "text": "#f0fdf4"
    },
    "industrial_orange": {
        "primary": "#ea580c", "secondary": "#fb923c",
        "bg": "#1c1917", "text": "#fafaf9"
    }
}
```

### Logo and Branding

#### Add Company Logo
```python
# Add to sidebar
with st.sidebar:
    st.image("assets/your_logo.png", width=200)
    st.markdown("# Your Company Name")
```

#### Custom Header
```python
def render_custom_header():
    st.markdown("""
    <div style="background: linear-gradient(90deg, #your_color1, #your_color2); 
                padding: 2rem; border-radius: 16px; margin-bottom: 2rem;">
        <h1 style="color: white; text-align: center;">
            🏭 Your Company Energy Intelligence
        </h1>
        <p style="color: rgba(255,255,255,0.8); text-align: center;">
            Custom tagline here
        </p>
    </div>
    """, unsafe_allow_html=True)
```

## 📊 Data Source Customization

### Adding New Energy Sources

#### Solar Inverter Integration
```python
# Add new solar data source
CUSTOM_SOLAR_SOURCES = [
    ("Inverter_A", "https://your-api.com/inverter_a_data.csv"),
    ("Inverter_B", "https://your-api.com/inverter_b_data.csv")
]

def load_custom_solar_data():
    """Load from your specific solar sources"""
    solar_dfs = []
    for name, url in CUSTOM_SOLAR_SOURCES:
        df = load_csv_data(url)
        if not df.empty:
            df['source'] = name
            solar_dfs.append(df)
    return pd.concat(solar_dfs, ignore_index=True)
```

#### Generator Monitoring
```python
# Custom generator sensors
GENERATOR_SENSORS = {
    "fuel_level": "sensor.custom_fuel_level",
    "runtime_hours": "sensor.custom_runtime", 
    "maintenance_due": "sensor.custom_maintenance"
}

def load_custom_generator_data():
    """Load from your Home Assistant or custom API"""
    # Implementation for your specific sensors
    pass
```

#### Factory Equipment
```python
# Individual equipment monitoring
EQUIPMENT_SENSORS = {
    "compressor_1": "sensor.compressor_1_power",
    "conveyor_belt": "sensor.conveyor_power",
    "cooling_system": "sensor.cooling_power",
    "lighting": "sensor.lighting_power"
}
```

### Database Integration

#### SQL Database Connection
```python
import sqlite3
import psycopg2

def load_from_database():
    """Load data from your existing database"""
    conn = sqlite3.connect('energy_data.db')
    
    queries = {
        'solar': "SELECT * FROM solar_production WHERE date >= ?",
        'consumption': "SELECT * FROM factory_consumption WHERE date >= ?"
    }
    
    data = {}
    for table, query in queries.items():
        data[table] = pd.read_sql(query, conn, params=[start_date])
    
    return data
```

#### Real-time API Integration
```python
def fetch_realtime_data():
    """Connect to your real-time monitoring system"""
    api_endpoints = {
        'current_power': 'https://your-api.com/current',
        'daily_totals': 'https://your-api.com/daily'
    }
    
    data = {}
    for key, url in api_endpoints.items():
        response = requests.get(url, headers={'Authorization': f'Bearer {API_TOKEN}'})
        data[key] = response.json()
    
    return data
```

## 📈 Chart Customization

### Custom Chart Types

#### Energy Flow Diagram
```python
def create_sankey_diagram(data):
    """Create energy flow visualization"""
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=["Solar", "Grid", "Generator", "Factory", "Excess"],
            color="blue"
        ),
        link=dict(
            source=[0, 1, 2, 0],
            target=[3, 3, 3, 4],
            value=data['flows']
        )
    )])
    return fig
```

#### Heatmap Calendar
```python
def create_energy_heatmap(df):
    """Daily energy consumption heatmap"""
    # Pivot data for heatmap
    pivot_data = df.pivot_table(
        values='consumption', 
        index=df['date'].dt.hour,
        columns=df['date'].dt.date
    )
    
    fig = px.imshow(
        pivot_data, 
        title="Daily Energy Consumption Pattern",
        color_continuous_scale="Viridis"
    )
    return fig
```

### KPI Widgets

#### Custom Metrics
```python
def render_custom_kpis():
    """Your specific KPI requirements"""
    kpis = calculate_custom_kpis()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_enhanced_metric(
            "Energy Efficiency", 
            f"{kpis['efficiency']:.1f}%",
            f"↗️ +{kpis['efficiency_change']:.1f}%",
            "positive"
        )
    
    with col2:
        render_enhanced_metric(
            "Cost per kWh",
            f"R {kpis['cost_per_kwh']:.2f}",
            f"Target: R {kpis['target_cost']:.2f}",
            "neutral"
        )
```

## 🔧 Feature Extensions

### Predictive Analytics

#### Energy Forecasting
```python
from sklearn.linear_model import LinearRegression
import numpy as np

def predict_energy_usage(historical_data, days_ahead=7):
    """Simple energy usage prediction"""
    # Prepare features (day of week, hour, weather, etc.)
    X = prepare_features(historical_data)
    y = historical_data['consumption']
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Generate future predictions
    future_X = generate_future_features(days_ahead)
    predictions = model.predict(future_X)
    
    return predictions
```

#### Maintenance Alerts
```python
def check_maintenance_alerts():
    """Equipment maintenance scheduling"""
    alerts = []
    
    # Generator maintenance
    if generator_hours > 500:
        alerts.append({
            'type': 'warning',
            'equipment': 'Generator',
            'message': 'Service due in 50 hours'
        })
    
    # Solar panel cleaning
    if days_since_cleaning > 30:
        alerts.append({
            'type': 'info', 
            'equipment': 'Solar Panels',
            'message': 'Cleaning recommended'
        })
    
    return alerts
```

### Cost Optimization

#### Demand Charge Optimization
```python
def analyze_demand_charges():
    """Optimize peak demand to reduce costs"""
    peak_times = identify_peak_usage()
    
    recommendations = []
    for peak in peak_times:
        if peak['demand'] > peak['threshold']:
            recommendations.append({
                'time': peak['time'],
                'current_demand': peak['demand'],
                'suggested_reduction': peak['demand'] * 0.15,
                'potential_savings': calculate_savings(peak['demand'] * 0.15)
            })
    
    return recommendations
```

#### Time-of-Use Optimization
```python
def optimize_time_of_use():
    """Shift loads to cheaper rate periods"""
    rate_schedule = get_utility_rates()
    current_usage = get_hourly_usage()
    
    # Identify shiftable loads
    shiftable_loads = identify_shiftable_equipment()
    
    optimized_schedule = {}
    for equipment in shiftable_loads:
        optimal_times = find_cheapest_hours(
            rate_schedule, 
            equipment['duration']
        )
        optimized_schedule[equipment['name']] = optimal_times
    
    return optimized_schedule
```

## 🚨 Alerts and Notifications

### Custom Alert System

#### Email Notifications
```python
import smtplib
from email.mime.text import MIMEText

def send_alert_email(alert_data):
    """Send email alerts for critical events"""
    msg = MIMEText(f"""
    Alert: {alert_data['type']}
    Equipment: {alert_data['equipment']} 
    Message: {alert_data['message']}
    Time: {alert_data['timestamp']}
    """)
    
    msg['Subject'] = f"Energy Alert: {alert_data['type']}"
    msg['From'] = 'alerts@yourcompany.com'
    msg['To'] = 'manager@yourcompany.com'
    
    # Send email
    server = smtplib.SMTP('your-smtp-server.com')
    server.send_message(msg)
```

#### Slack Integration
```python
import requests

def send_slack_notification(message, channel="#energy-alerts"):
    """Send notifications to Slack"""
    webhook_url = "https://hooks.slack.com/your-webhook"
    
    payload = {
        'channel': channel,
        'text': message,
        'icon_emoji': ':zap:'
    }
    
    requests.post(webhook_url, json=payload)
```

#### Dashboard Alerts
```python
def display_dashboard_alerts():
    """Show alerts in the dashboard"""
    alerts = get_current_alerts()
    
    if alerts:
        for alert in alerts:
            if alert['severity'] == 'critical':
                st.error(f"🚨 {alert['message']}")
            elif alert['severity'] == 'warning':
                st.warning(f"⚠️ {alert['message']}")
            else:
                st.info(f"ℹ️ {alert['message']}")
```

## 🔌 API and Webhook Integration

### Custom API Endpoints

#### Data Export API
```python
from flask import Flask, jsonify
import threading

app = Flask(__name__)

@app.route('/api/energy-data')
def get_energy_data():
    """Provide energy data via API"""
    data = {
        'solar': get_solar_data().to_dict('records'),
        'consumption': get_consumption_data().to_dict('records'),
        'generator': get_generator_data().to_dict('records')
    }
    return jsonify(data)

# Run API in background thread
def start_api():
    app.run(host='0.0.0.0', port=5000)

api_thread = threading.Thread(target=start_api, daemon=True)
api_thread.start()
```

#### Webhook Receivers
```python
@app.route('/webhook/meter-reading', methods=['POST'])
def receive_meter_data():
    """Receive data from smart meters"""
    data = request.json
    
    # Process and store meter reading
    process_meter_reading(data)
    
    return jsonify({'status': 'received'})
```

## 📱 Mobile App Integration

### PWA Configuration
```python
# Add to .streamlit/config.toml
[ui]
hideTopBar = true
hideSidebarNav = false

# Mobile-specific CSS
def apply_mobile_optimizations():
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        .main-header { font-size: 1.5rem; }
        .metric-card { padding: 1rem; }
        .chart-container { height: 300px; }
    }
    </style>
    """, unsafe_allow_html=True)
```

## 🔐 Security Customization

### User Authentication
```python
import streamlit_authenticator as stauth

# Configure authentication
config = {
    'credentials': {
        'usernames': {
            'admin': {'name': 'Administrator', 'password': 'hashed_password'},
            'operator': {'name': 'Operator', 'password': 'hashed_password'}
        }
    },
    'cookie': {'name': 'energy_dashboard', 'key': 'secret_key', 'expiry_days': 30}
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'], 
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, authentication_status, username = authenticator.login('Login', 'main')
```

### Role-Based Access
```python
def check_user_permissions(username, required_role):
    """Check user permissions for features"""
    user_roles = {
        'admin': ['view', 'edit', 'export', 'configure'],
        'manager': ['view', 'export'],
        'operator': ['view']
    }
    
    user_permissions = user_roles.get(username, [])
    return required_role in user_permissions
```

## 📊 Reporting Customization

### Custom Report Templates
```python
def generate_monthly_report():
    """Generate customized monthly energy report"""
    template = {
        'title': 'Monthly Energy Performance Report',
        'period': f"{start_date} to {end_date}",
        'sections': [
            'executive_summary',
            'solar_performance', 
            'generator_costs',
            'factory_consumption',
            'recommendations'
        ]
    }
    
    report_data = compile_report_data()
    return render_report_template(template, report_data)
```

### Automated Reports
```python
from apscheduler.schedulers.background import BackgroundScheduler

def setup_automated_reports():
    """Schedule automatic report generation"""
    scheduler = BackgroundScheduler()
    
    # Weekly reports every Monday at 8 AM
    scheduler.add_job(
        generate_weekly_report,
        'cron', 
        day_of_week='mon',
        hour=8
    )
    
    # Monthly reports on 1st of each month
    scheduler.add_job(
        generate_monthly_report,
        'cron',
        day=1,
        hour=9
    )
    
    scheduler.start()
```

## 🎯 Performance Tuning

### Custom Caching
```python
@st.cache_data(ttl=600, max_entries=100)
def cache_heavy_calculation(params):
    """Cache expensive computations"""
    # Your heavy calculation here
    return result

# Cache management
def clear_selective_cache():
    """Clear specific cache entries"""
    st.cache_data.clear()
```

### Data Optimization
```python
def optimize_dataframes():
    """Optimize DataFrame memory usage"""
    for df_name, df in dataframes.items():
        # Optimize numeric columns
        numeric_cols = df.select_dtypes(include=['float64']).columns
        df[numeric_cols] = df[numeric_cols].astype('float32')
        
        # Optimize categorical columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if df[col].nunique() < 50:
                df[col] = df[col].astype('category')
```

---

## 🎯 Quick Customization Checklist

- [ ] 🎨 Update color theme and branding
- [ ] 📊 Add your specific data sources
- [ ] 📈 Configure custom charts and KPIs  
- [ ] 🚨 Set up alerts and notifications
- [ ] 🔐 Implement authentication if needed
- [ ] 📱 Test mobile responsiveness
- [ ] 📊 Configure automated reporting
- [ ] ⚡ Optimize for your data volume

Ready to customize? Start with the color theme and gradually add your specific requirements!