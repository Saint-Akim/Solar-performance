# 🏭 Durr Bottling Energy Intelligence Dashboard

> **Advanced energy monitoring and analysis platform for industrial operations**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Overview

The **Durr Bottling Energy Intelligence Dashboard** is a comprehensive real-time energy monitoring solution that provides deep insights into:

- 🔋 **Generator Performance** - Fuel consumption tracking and cost analysis
- ☀️ **Solar Energy Production** - Multi-inverter monitoring and efficiency metrics
- 🏭 **Factory Energy Consumption** - Industrial load analysis and patterns
- 📄 **Automated Invoice Management** - Streamlined billing and reporting

## ✨ Key Features

### 🎯 **Real-time Monitoring**
- Live data from multiple energy sources
- Automatic timezone handling (South African time)
- Cross-validated fuel consumption tracking

### 📊 **Advanced Analytics**
- Daily, weekly, and monthly trends
- Peak demand analysis
- Cost optimization insights
- Energy efficiency metrics

### 🎨 **Modern Interface**
- Dark theme optimized for 24/7 monitoring
- Responsive design (mobile, tablet, desktop)
- Interactive charts with export capabilities
- Intuitive navigation and controls

### 🚀 **Production Ready**
- Robust error handling
- Performance optimized
- Scalable architecture
- Comprehensive logging

## 🚀 Quick Start

### Option 1: Local Development
```bash
# Clone the repository
git clone https://github.com/Saint-Akim/Solar-performance.git
cd Solar-performance

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app_fixed.py
```

### Option 2: Docker
```bash
# Quick start with Docker
docker run -p 8501:8501 durr-energy-dashboard:latest

# Or with docker-compose
docker-compose up -d
```

### Option 3: One-Click Deploy
[![Deploy to Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

## 📊 Dashboard Sections

### 🔋 Generator Analysis
- **Fuel Consumption Tracking**: Real-time monitoring from multiple sensors
- **Cost Analysis**: Dynamic pricing with purchase history integration
- **Efficiency Metrics**: Performance indicators and optimization suggestions
- **Trend Analysis**: Daily, weekly patterns and forecasting

### ☀️ Solar Performance
- **Multi-Inverter Monitoring**: Goodwe & Fronius inverter data
- **Production Analytics**: Peak output, efficiency curves
- **Weather Correlation**: Performance vs. environmental conditions
- **ROI Calculations**: Energy savings and payback analysis

### 🏭 Factory Consumption
- **Load Profiling**: Industrial energy usage patterns
- **Peak Demand Management**: Cost optimization strategies
- **Equipment Monitoring**: Individual system tracking
- **Efficiency Benchmarking**: Performance comparisons

### 📄 Invoice Management
- **Automated Generation**: Smart billing document creation
- **Multi-Location Support**: Freedom Village & Boerdery tracking
- **Historical Analysis**: Billing trend analysis
- **Export Options**: PDF, Excel, CSV formats

## 🔧 Configuration

### Environment Variables
```bash
# Optional configuration (defaults provided)
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
DEFAULT_FUEL_PRICE=22.50
TIMEZONE=Africa/Johannesburg
```

### Data Sources
The dashboard automatically fetches data from:
- Generator sensors (Home Assistant)
- Solar inverters (CSV exports)
- Factory meters (energy monitoring)
- Fuel purchase records (Excel tracking)

## 📱 Mobile Support

Fully optimized for mobile devices:
- 📱 **Responsive Design**: Adapts to any screen size
- 👆 **Touch Optimized**: Swipe gestures and tap interactions
- ⚡ **Fast Loading**: Optimized for mobile networks
- 🔋 **Battery Friendly**: Efficient resource usage

## 🛠️ Development

### Project Structure
```
Solar-performance/
├── app_fixed.py           # Main application (enhanced version)
├── app.py                 # Original application (backup)
├── requirements.txt       # Python dependencies
├── .streamlit/           # Streamlit configuration
├── docs/                 # Documentation
├── tests/                # Test files
└── deploy/               # Deployment scripts
```

### Key Technologies
- **Frontend**: Streamlit with custom CSS
- **Charts**: Plotly.js for interactive visualizations
- **Data**: Pandas for processing and analysis
- **Backend**: Python with async data loading
- **Deployment**: Docker, Heroku, AWS, Streamlit Cloud

### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📈 Performance

### Benchmarks
- **Load Time**: < 3 seconds
- **Data Refresh**: Every 15 minutes
- **Memory Usage**: ~100MB typical
- **CPU Usage**: < 5% during normal operation

### Optimization Features
- Intelligent caching with TTL
- Lazy loading for large datasets
- Efficient data structures
- Background data fetching

## 🔒 Security

- **No Sensitive Data**: All sources are public or encrypted
- **HTTPS Enforced**: Secure data transmission
- **Input Validation**: Prevents injection attacks
- **Error Handling**: Secure error messages

## 📞 Support

### Documentation
- 📖 **User Guide**: `docs/USER_GUIDE.md`
- 🔧 **Developer Docs**: `docs/DEVELOPER.md`
- 🚀 **Deployment**: `DEPLOYMENT_GUIDE.md`
- 🎨 **Customization**: `CUSTOMIZATION_GUIDE.md`

### Getting Help
- 📧 **Email**: support@durrbottling.com
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/Saint-Akim/Solar-performance/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/Saint-Akim/Solar-performance/discussions)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎉 Acknowledgments

- **Streamlit Team**: For the amazing framework
- **Plotly**: For interactive visualizations
- **Durr Bottling**: For the opportunity to innovate
- **Open Source Community**: For inspiration and tools

---

<div align="center">

**[🚀 Deploy Now](https://share.streamlit.io)** • **[📖 Documentation](docs/)** • **[🐛 Report Bug](issues)** • **[💡 Request Feature](issues)**

Made with ❤️ for energy efficiency

</div>