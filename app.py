import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---- Configuration Constants ----
UPLOAD_ROOT = "Uploads"
SOLAR_DIR = os.path.join(UPLOAD_ROOT, "solar")
WEATHER_DIR = os.path.join(UPLOAD_ROOT, "weather")
TOTAL_CAPACITY_KW = 221.43
PERFORMANCE_RATIO = 0.8
TZ = 'Africa/Johannesburg'
MAX_FILE_SIZE_MB = 10

# ---- Solar Parameter Labels ----
SOLAR_LABELS = {
    'sensor.fronius_grid_power': 'Fronius Grid Power',
    'sensor.goodwe_grid_power': 'GoodWe Grid Power',
    'sensor.fronius_power_l1': 'Fronius Power L1',
    'sensor.fronius_power_l2': 'Fronius Power L2',
    'sensor.fronius_power_l3': 'Fronius Power L3',
    'sensor.goodwe_power_l1': 'GoodWe Power L1',
    'sensor.goodwe_power_l2': 'GoodWe Power L2',
    'sensor.goodwe_power_l3': 'GoodWe Power L3',
    'sensor.fronius_voltage_l1': 'Fronius Voltage L1',
    'sensor.fronius_voltage_l2': 'Fronius Voltage L2',
    'sensor.fronius_voltage_l3': 'Fronius Voltage L3',
    'sensor.goodwe_voltage_l1': 'GoodWe Voltage L1',
    'sensor.goodwe_voltage_l2': 'GoodWe Voltage L2',
    'sensor.goodwe_voltage_l3': 'GoodWe Voltage L3',
    'sensor.fronius_current_l1': 'Fronius Current L1',
    'sensor.fronius_current_l2': 'Fronius Current L2',
    'sensor.fronius_current_l3': 'Fronius Current L3',
    'sensor.goodwe_current_l1': 'GoodWe Current L1',
    'sensor.goodwe_current_l2': 'GoodWe Current L2',
    'sensor.goodwe_current_l3': 'GoodWe Current L3'
}

# ---- Weather Parameter Explainers ----
WEATHER_PARAM_EXPLAINERS = {
    "air_temp": "🌡️ **Air Temperature:** Affects panel efficiency; too high reduces output.",
    "albedo": "🪞 **Albedo:** Reflectivity of ground—higher values mean more reflected sunlight to panels.",
    "azimuth": "🧭 **Azimuth:** Direction of the sun, affecting angle of incidence on panels.",
    "clearsky_dhi": "🌤️ **Clear-sky Diffuse Horizontal Irradiance:** Sky-scattered light under ideal conditions.",
    "clearsky_dni": "🌞 **Clear-sky Direct Normal Irradiance:** Direct beam sunlight in ideal sky.",
    "clearsky_ghi": "🔆 **Clear-sky Global Horizontal Irradiance:** Total sunlight on flat surface in clear sky.",
    "clearsky_gti": "📈 **Clear-sky Global Tilted Irradiance:** Irradiance on tilted plane under clear sky.",
    "cloud_opacity": "☁️ **Cloud Opacity:** Scale from 0–10. Higher = more light blocked by clouds.",
    "dhi": "☀️ **Diffuse Horizontal Irradiance:** Scattered light from sky, not direct sun.",
    "dni": "🌅 **Direct Normal Irradiance:** Sunlight coming straight from the sun.",
    "ghi": "📉 **Global Horizontal Irradiance:** Sum of direct and diffuse light on flat plane.",
    "gti": "📊 **Global Tilted Irradiance:** Real solar input on actual panel tilt.",
    "precipitation_rate": "🌧️ **Precipitation Rate:** Heavy rain reduces sunlight, may indicate inverter faults.",
    "zenith": "🧮 **Zenith Angle:** Higher angle = sun lower in sky = less efficient light capture.",
    "weather_type": "🌦️ **Weather Type:** Descriptive condition: SUNNY, CLEAR, MOSTLY CLOUDY etc.",
    "period_end": "🕓 **Time Period End:** Timestamp of observation hour.",
    "period": "⏱️ **Period Duration:** Observation duration (e.g., PT60M for 1 hour)."
}

WEATHER_TYPE_DISPLAY = {
    "CLEAR": "☀️ Clear",
    "MOSTLY CLEAR": "🌤️ Mostly Clear",
    "MOSTLY SUNNY": "⛅ Mostly Sunny",
    "SUNNY": "🌞 Sunny"
}
