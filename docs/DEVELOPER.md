# 🛠️ Developer Guide - Solar Performance Dashboard

## 🏗️ Architecture Overview

The Durr Bottling Energy Dashboard follows a **modular, data-driven architecture** optimized for real-time energy monitoring and analysis.

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Processing     │───▶│   Visualization │
│                 │    │   Pipeline      │    │                 │
│ • GitHub Files  │    │ • Validation    │    │ • Streamlit UI  │
│ • Excel/CSV     │    │ • Cleaning      │    │ • Plotly Charts │
│ • REST APIs     │    │ • Aggregation   │    │ • Custom CSS    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Setup & Installation

### Development Environment

```bash
# Clone and setup
git clone https://github.com/Saint-Akim/Solar-performance.git
cd Solar-performance

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run in development mode
streamlit run app_fixed.py --server.runOnSave=true
```

### Dependencies Overview

```python
# Core Framework
streamlit>=1.28.0           # Web framework
pandas>=2.0.0              # Data manipulation
plotly>=5.15.0             # Interactive charts

# Data Processing
numpy>=1.24.0              # Numerical computing
openpyxl>=3.1.0           # Excel file handling
requests>=2.28.0          # HTTP requests

# Optional ML/AI
scikit-learn>=1.3.0       # Machine learning
openai>=0.27.0            # AI integration
transformers>=4.30.0      # NLP models
```

## 📊 Data Pipeline

### Data Sources Architecture

```python
# Data source configuration
DATA_SOURCES = {
    "generator": "Excel file with fuel consumption",
    "fuel_level": "Time series sensor data", 
    "factory": "Energy consumption CSV",
    "solar": "Multiple monthly CSV files",
    "billing": "Invoice template Excel"
}
```

### Data Flow

1. **🔄 Ingestion**: `load_all_data()` fetches from GitHub
2. **🧹 Cleaning**: `process_*_data()` functions validate and clean
3. **⏰ Timezone**: `process_timezone_data()` handles SA timezone
4. **📊 Aggregation**: Daily/weekly/monthly summaries
5. **🎨 Visualization**: Plotly charts with custom styling

### Error Handling Strategy

```python
def safe_data_operation(func, fallback=None):
    """Robust error handling pattern"""
    try:
        return func()
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        st.warning(f"Data unavailable: {str(e)}")
        return fallback or pd.DataFrame()
```

## 🎨 UI/UX Architecture

### Design System

```css
/* Color Palette */
:root {
    --bg-primary: #0f1419;      /* Dark background */
    --bg-secondary: #1a1f2e;    /* Card background */
    --text-primary: #f7fafc;    /* Primary text */
    --accent-blue: #3182ce;     /* Action color */
    --accent-green: #38a169;    /* Success color */
}
```

### Component Structure

```python
# Reusable UI components
def render_enhanced_metric(label, value, delta, color, icon):
    """Enhanced metric cards with animations"""
    
def create_enhanced_chart(df, x_col, y_col, title, **kwargs):
    """Standardized chart creation"""
    
def apply_enhanced_design_system():
    """Global CSS injection"""
```

### Responsive Breakpoints

```css
/* Mobile-first responsive design */
@media (max-width: 768px)  { /* Mobile */ }
@media (max-width: 1024px) { /* Tablet */ }
@media (min-width: 1025px) { /* Desktop */ }
```

## 📈 Performance Optimization

### Caching Strategy

```python
# Streamlit caching patterns
@st.cache_data(ttl=3600)  # 1 hour cache
def load_static_data():
    """Cache stable data sources"""

@st.cache_data(ttl=900)   # 15 minute cache  
def load_dynamic_data():
    """Cache frequently updated data"""
```

### Memory Management

- **Lazy Loading**: Load data only when needed
- **Efficient DataFrames**: Use appropriate dtypes
- **Garbage Collection**: Clean up large objects
- **Streaming**: Process large files in chunks

### Network Optimization

```python
# Concurrent data loading
import asyncio
import aiohttp

async def fetch_all_sources():
    """Parallel data fetching"""
    tasks = [fetch_source(url) for url in sources]
    return await asyncio.gather(*tasks)
```

## 🔌 API Integration

### Data Source APIs

```python
# GitHub API integration
def fetch_github_file(repo, path, branch="main"):
    """Fetch files from GitHub with authentication"""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    return requests.get(url, headers=headers)

# Home Assistant API
def fetch_sensor_data(entity_id, hours=24):
    """Fetch sensor data from Home Assistant"""
    url = f"{HA_URL}/api/history/period"
    params = {"filter_entity_id": entity_id}
    return requests.get(url, headers=HA_HEADERS, params=params)
```

### External Service Integration

```python
# Weather API for solar correlation
def get_weather_data(lat, lon, date):
    """Fetch weather data for solar analysis"""
    
# Energy pricing API
def get_electricity_rates(region="gauteng"):
    """Current electricity tariffs"""
```

## 🧪 Testing Framework

### Unit Tests

```python
# test_data_processing.py
import pytest
import pandas as pd
from app_fixed import process_generator_data

def test_fuel_consumption_calculation():
    """Test fuel consumption logic"""
    sample_data = pd.DataFrame({
        'state': [100, 95, 90, 85],
        'last_changed': pd.date_range('2024-01-01', periods=4, freq='H')
    })
    
    result = process_generator_data(sample_data, pd.DataFrame(), pd.DataFrame())
    assert not result[0].empty
    assert result[1]['liters'] > 0
```

### Integration Tests

```python
# test_dashboard_integration.py
def test_full_dashboard_load():
    """Test complete dashboard functionality"""
    # Simulate Streamlit session
    # Verify all tabs load without errors
    # Check chart rendering
```

### Performance Tests

```python
# test_performance.py
import time

def test_load_time():
    """Ensure dashboard loads within 3 seconds"""
    start = time.time()
    load_all_data()
    duration = time.time() - start
    assert duration < 3.0
```

## 🔐 Security Best Practices

### Data Validation

```python
def validate_sensor_data(df):
    """Comprehensive data validation"""
    checks = [
        df['value'].between(-1000, 10000),  # Reasonable ranges
        df['timestamp'].dt.year >= 2020,    # Valid dates
        ~df['value'].isna(),                # No null values
    ]
    return df[pd.concat(checks, axis=1).all(axis=1)]
```

### Input Sanitization

```python
def sanitize_user_input(value, data_type=float, min_val=0, max_val=1000):
    """Sanitize user inputs"""
    try:
        clean_value = data_type(value)
        return max(min_val, min(clean_value, max_val))
    except (ValueError, TypeError):
        return min_val
```

### Secrets Management

```toml
# .streamlit/secrets.toml
[database]
host = "localhost"
username = "admin"

[api_keys]
weather_api = "your_key_here"
```

## 🚀 Deployment Strategies

### Environment Configuration

```python
# config.py
import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    cache_ttl: int = int(os.getenv('CACHE_TTL', '3600'))
    timezone: str = os.getenv('TZ', 'Africa/Johannesburg')
    
config = AppConfig()
```

### Docker Optimization

```dockerfile
# Multi-stage build for smaller images
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
WORKDIR /app
COPY . .
CMD ["streamlit", "run", "app_fixed.py"]
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy Dashboard
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest tests/
      
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Streamlit Cloud
        run: curl -X POST ${{ secrets.DEPLOY_WEBHOOK }}
```

## 📊 Monitoring & Analytics

### Application Metrics

```python
# metrics.py
import time
import logging

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def track_load_time(self, operation):
        start = time.time()
        yield
        self.metrics[operation] = time.time() - start
```

### User Analytics

```python
# Track dashboard usage
def track_user_interaction(action, section, duration=None):
    """Anonymous usage analytics"""
    analytics_data = {
        'timestamp': datetime.now(),
        'action': action,
        'section': section,
        'duration': duration
    }
    # Send to analytics service
```

### Error Monitoring

```python
# sentry_config.py
import sentry_sdk
from sentry_sdk.integrations.streamlit import StreamlitIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[StreamlitIntegration()],
    traces_sample_rate=0.1
)
```

## 🔧 Customization Guide

### Adding New Data Sources

```python
# 1. Define new data source
NEW_SOURCE_URL = "https://api.example.com/data"

# 2. Create loader function
def load_new_source():
    """Load data from new source"""
    return fetch_csv_safe(NEW_SOURCE_URL)

# 3. Add to main pipeline
@st.cache_data(ttl=1800)
def load_all_data():
    # ... existing sources
    new_data = load_new_source()
    return solar_df, gen_df, fuel_df, factory_df, new_data
```

### Custom Visualizations

```python
def create_custom_chart(df, chart_type="treemap"):
    """Add new chart types"""
    if chart_type == "treemap":
        fig = px.treemap(df, path=['category'], values='value')
    elif chart_type == "sunburst":
        fig = px.sunburst(df, path=['level1', 'level2'], values='value')
    
    return fig
```

### Theme Customization

```python
# themes.py
THEMES = {
    "default": {"primary": "#3182ce", "bg": "#0f1419"},
    "light": {"primary": "#2d3748", "bg": "#ffffff"},
    "custom": {"primary": "#your_color", "bg": "#your_bg"}
}

def apply_theme(theme_name="default"):
    theme = THEMES.get(theme_name, THEMES["default"])
    # Apply CSS variables
```

## 🐛 Debugging Guide

### Common Issues

1. **Data Loading Failures**
   ```python
   # Debug data sources
   for source, url in DATA_SOURCES.items():
       response = requests.head(url)
       print(f"{source}: {response.status_code}")
   ```

2. **Chart Rendering Issues**
   ```python
   # Validate chart data
   def debug_chart_data(df, x_col, y_col):
       print(f"DataFrame shape: {df.shape}")
       print(f"Columns: {list(df.columns)}")
       print(f"X column ({x_col}) exists: {x_col in df.columns}")
       print(f"Y column ({y_col}) exists: {y_col in df.columns}")
   ```

3. **Performance Issues**
   ```python
   # Profile performance
   import cProfile
   
   def profile_function():
       cProfile.run('load_all_data()', 'profile_output.stats')
   ```

### Debug Mode

```python
# Enable debug logging
if config.debug:
    logging.basicConfig(level=logging.DEBUG)
    st.set_option('deprecation.showPyplotGlobalUse', False)
    
    # Show debug information
    st.sidebar.markdown("### 🐛 Debug Info")
    st.sidebar.json({
        "session_state": dict(st.session_state),
        "data_shapes": {k: v.shape for k, v in data.items()},
        "memory_usage": get_memory_usage()
    })
```

## 📝 Contributing

### Code Style

```python
# Follow PEP 8 with these additions:
# - Type hints for all functions
# - Docstrings for public methods  
# - Meaningful variable names
# - Error handling for all external calls

def process_data(df: pd.DataFrame, 
                columns: List[str]) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Process energy data with validation and cleaning.
    
    Args:
        df: Raw data DataFrame
        columns: Required column names
        
    Returns:
        Tuple of (cleaned_df, summary_stats)
        
    Raises:
        ValueError: If required columns missing
    """
```

### Git Workflow

```bash
# Feature development
git checkout -b feature/new-analytics
git commit -m "feat: add hourly consumption analysis"
git push origin feature/new-analytics

# Create pull request with:
# - Clear description
# - Test results
# - Screenshots (for UI changes)
```

---

## 🎯 Quick Development Reference

| Task | Command | Location |
|------|---------|----------|
| Run dev server | `streamlit run app_fixed.py` | Root |
| Run tests | `pytest tests/` | Root |
| Build docs | `mkdocs build` | docs/ |
| Docker build | `docker build -t dashboard .` | Root |
| Profile app | `python -m cProfile app_fixed.py` | Root |

## 📚 Additional Resources

- **[Streamlit Docs](https://docs.streamlit.io)** - Framework documentation
- **[Plotly Python](https://plotly.com/python/)** - Visualization library
- **[Pandas Guide](https://pandas.pydata.org/docs/)** - Data manipulation
- **[Docker Best Practices](https://docs.docker.com/develop/best-practices/)** - Container optimization

---

*Ready to contribute? Check out our [Contributing Guidelines](../CONTRIBUTING.md)*