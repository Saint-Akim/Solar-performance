# ------------------ DATA LOADING ------------------
import pytz

TOTAL_CAPACITY_KW = 221.43
GOODWE_KW = 110.0
FRONIUS_KW = 60.0
INVERTER_TOTAL_KW = GOODWE_KW + FRONIUS_KW
TZ = pytz.timezone("Africa/Johannesburg")

SOLAR_URLS = [
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Solar_Goodwe%26Fronius-Jan.csv",
    "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/Sloar_Goodwe%26Fronius_Feb.csv"
]
WEATHER_URL = "https://raw.githubusercontent.com/Saint-Akim/Solar-performance/main/csv_-33.78116654125097_19.00166906876145_horizontal_single_axis_23_30_PT60M.csv"

@st.cache_data
def safe_read(url):
    try:
        return pd.read_csv(url)
    except Exception:
        return pd.DataFrame()

def normalize(df):
    if df.empty:
        return pd.DataFrame()
    for col in df.columns:
        if 'time' in col.lower() or 'date' in col.lower():
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df = df.rename(columns={col: 'last_changed'})
            break
    return df

def load_multiple(urls):
    parts = [normalize(safe_read(u)) for u in urls if not safe_read(u).empty]
    if parts:
        df = pd.concat(parts).sort_values('last_changed').reset_index(drop=True)
        return df
    return pd.DataFrame()

@st.cache_data
def load_weather(gti_factor, pr):
    df = safe_read(WEATHER_URL)
    if df.empty:
        return pd.DataFrame(columns=['period_end','gti','expected_total_kw','expected_inverter_kw','expected_goodwe_kw','expected_fronius_kw'])
    time_col = [c for c in df.columns if 'period_end' in c.lower() or 'time' in c.lower() or 'date' in c.lower()]
    df.rename(columns={time_col[0]: 'period_end'}, inplace=True)
    gti_col = [c for c in df.columns if 'gti' in c.lower() or 'irradi' in c.lower() or 'ghi' in c.lower()]
    if gti_col:
        df.rename(columns={gti_col[0]: 'gti'}, inplace=True)
    else:
        df['gti'] = 0.9
    df['gti'] = pd.to_numeric(df['gti'], errors='coerce').fillna(0)
    df['expected_total_kw'] = df['gti'] * gti_factor * TOTAL_CAPACITY_KW * pr
    df['expected_inverter_kw'] = df['gti'] * gti_factor * INVERTER_TOTAL_KW * pr
    df['expected_goodwe_kw'] = df['gti'] * gti_factor * GOODWE_KW * pr
    df['expected_fronius_kw'] = df['gti'] * gti_factor * FRONIUS_KW * pr
    return df

# Load datasets
solar_df = load_multiple(SOLAR_URLS)
weather_df = load_weather(gti_factor, pr_ratio)

# Merge solar & weather
if not solar_df.empty and not weather_df.empty:
    solar_df['last_changed'] = pd.to_datetime(solar_df['last_changed'], errors='coerce')
    weather_df['period_end'] = pd.to_datetime(weather_df['period_end'], errors='coerce')
    solar_df = pd.merge_asof(solar_df.sort_values('last_changed'),
                             weather_df.sort_values('period_end'),
                             left_on='last_changed', right_on='period_end',
                             direction='nearest', tolerance=pd.Timedelta('3H'))

# Filter by date
if not solar_df.empty:
    mask = (solar_df['last_changed'] >= pd.to_datetime(start_date)) & (solar_df['last_changed'] <= pd.to_datetime(end_date))
    filtered = solar_df.loc[mask].copy()
else:
    filtered = pd.DataFrame()
