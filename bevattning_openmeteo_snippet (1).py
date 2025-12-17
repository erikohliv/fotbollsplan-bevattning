"""
Kräver:
  pip install openmeteo-requests requests-cache retry-requests numpy pandas

Logik:
- Hämtar 7 dygn (168h) hourly: rain, temperature_2m, relative_humidity_2m, wind_speed_10m
- Beräknar:
    veckoregnet = sum rain 0–168h
    regn_24h = sum rain 0–24h
    medeltemp_24h
    maxvind_24h
- Beslutar bevattningstid (minuter) för nattfönster (01:00–05:00):
    base_min = 20
    om veckoregnet < 25 mm: + (25 - veckoregnet) * k (k=0.5), max 60
    om regn_24h > 5 mm: sätt till 0 (hoppa pga väntat regn)
    om maxvind_24h > 8 m/s: sätt till 0 (hoppa pga vind)
    temp-justering: +10 om medeltemp_24h > 22°C, -10 om < 8°C (golv 0)
- Om tid > 0 och klockan inom nattfönster → kör bevattning.
"""

import datetime as dt
from typing import Tuple

import numpy as np
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry

# --- Konfig ---
LAT = 56.1
LON = 14.5333
TZ = "Europe/Stockholm"

WEEKLY_RAIN_TARGET_MM = 25.0
RAIN_LOOKAHEAD_24H_MM = 5.0
WIND_MAX_24H_MS = 8.0
BASE_MINUTES = 20
K_MM_TO_MIN = 0.5
MAX_MINUTES = 60
TEMP_HOT = 22.0
TEMP_COLD = 8.0
TEMP_ADJ_HOT = 10
TEMP_ADJ_COLD = -10

NIGHT_START = dt.time(1, 0)   # 01:00
NIGHT_END = dt.time(5, 0)     # 05:00

# --- Open-Meteo klient ---
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
om_client = openmeteo_requests.Client(session=retry_session)

def fetch_forecast_dataframe() -> pd.DataFrame:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": [
            "temperature_2m",
            "rain",
            "relative_humidity_2m",
            "wind_speed_10m",
        ],
        "wind_speed_unit": "ms",
        "timezone": TZ,
        "forecast_days": 7,  # 7 dygn = 168h
        "models": "dmi_harmonie_arome_europe",
    }
    responses = om_client.weather_api(url, params=params)
    resp = responses[0]
    hourly = resp.Hourly()

    # Ordningen måste följa params["hourly"]
    t_arr = hourly.Variables(0).ValuesAsNumpy()
    rain_arr = hourly.Variables(1).ValuesAsNumpy()
    rh_arr = hourly.Variables(2).ValuesAsNumpy()
    wind_arr = hourly.Variables(3).ValuesAsNumpy()

    idx = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True).tz_convert(TZ),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True).tz_convert(TZ),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )

    df = pd.DataFrame(
        {
            "temperature_2m": t_arr,
            "rain": rain_arr,
            "relative_humidity_2m": rh_arr,
            "wind_speed_10m": wind_arr,
        },
        index=idx,
    )
    return df

def compute_irrigation_minutes(df: pd.DataFrame) -> Tuple[int, dict]:
    # Begränsa till 168h (säkerhetsbälte)
    df = df.iloc[:168]

    # Aggregeringar
    rain_week = float(df["rain"].sum())
    rain_24h = float(df["rain"].iloc[:24].sum())
    temp_mean_24h = float(df["temperature_2m"].iloc[:24].mean())
    wind_max_24h = float(df["wind_speed_10m"].iloc[:24].max())

    minutes = BASE_MINUTES

    if rain_week < WEEKLY_RAIN_TARGET_MM:
        minutes += (WEEKLY_RAIN_TARGET_MM - rain_week) * K_MM_TO_MIN
    minutes = min(minutes, MAX_MINUTES)

    # Vädra ut om regn snart eller hård vind
    if rain_24h > RAIN_LOOKAHEAD_24H_MM:
        minutes = 0
    if wind_max_24h > WIND_MAX_24H_MS:
        minutes = 0

    # Temp-justeringar
    if temp_mean_24h > TEMP_HOT:
        minutes += TEMP_ADJ_HOT
    elif temp_mean_24h < TEMP_COLD:
        minutes += TEMP_ADJ_COLD

    minutes = max(0, min(int(round(minutes)), MAX_MINUTES))

    metrics = {
        "rain_week_mm": rain_week,
        "rain_24h_mm": rain_24h,
        "temp_mean_24h_c": temp_mean_24h,
        "wind_max_24h_ms": wind_max_24h,
        "minutes": minutes,
    }
    return minutes, metrics

def is_night_window(now: dt.datetime) -> bool:
    t = now.timetz() if now.tzinfo else now.time()
    return (t >= NIGHT_START) and (t <= NIGHT_END)

# Placeholder: ersätt med ditt faktiska styr-API
def start_irrigation(minutes: int):
    print(f"[IRRIGATION] Startar bevattning i {minutes} minuter")

def run_autowater():
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=0))).astimezone(dt.timezone.utc).astimezone(
        dt.timezone(dt.timedelta(hours=1))
    )
    if not is_night_window(now):
        print(f"[{now}] Utanför nattfönster, ingen bevattning.")
        return

    try:
        df = fetch_forecast_dataframe()
    except Exception as e:
        print(f"[{now}] Kunde inte hämta prognos: {e}")
        return

    minutes, metrics = compute_irrigation_minutes(df)
    print(f"[{now}] Prognos: {metrics}")

    if minutes > 0:
        start_irrigation(minutes)
    else:
        print(f"[{now}] Ingen bevattning behövs.")

if __name__ == "__main__":
    run_autowater()