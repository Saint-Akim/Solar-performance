
# Streamlit Cloud Deployment Guide

## Steps:

1. **Fork the repository** to your GitHub account
2. **Go to** [share.streamlit.io](https://share.streamlit.io)
3. **Connect your GitHub** account
4. **Deploy new app** with these settings:
   - Repository: `your-username/Solar-performance`
   - Branch: `main`
   - Main file path: `app_fixed.py`
5. **Add secrets** (if needed) from `streamlit_secrets_template.toml`

## URL Structure:
Your app will be available at:
`https://your-username-solar-performance-app-fixed-xyz123.streamlit.app`

## Environment Variables:
All data sources use public GitHub URLs - no secrets required!
    