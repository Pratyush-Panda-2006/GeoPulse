import datetime as dt
import logging
import functools
import requests
from typing import Optional

from src.api.schemas import WeatherContext

logger = logging.getLogger(__name__)

# Cache the HTTP requests deterministically
@functools.lru_cache(maxsize=128)
def _fetch_open_meteo(
    lat: float, 
    lon: float, 
    start_date: str, 
    end_date: str
) -> dict:
    """
    Fetch daily precipitation and soil moisture from Open-Meteo.
    Automatically chooses between the archive API and the forecast API
    based on the recency of the end_date.
    """
    # Open-Meteo archive API has a ~5-10 day lag. 
    # If the end_date is within 10 days of today, we use the forecast API with past_days.
    end_dt = dt.date.fromisoformat(end_date)
    today = dt.date.today()
    days_ago = (today - end_dt).days

    if days_ago > 10:
        endpoint_used = "archive"
        base_url = "https://archive-api.open-meteo.com/v1/archive"
    else:
        endpoint_used = "forecast"
        base_url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,soil_moisture_0_to_10cm_mean",
        "timezone": "UTC"
    }

    resp = requests.get(base_url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    data["_endpoint_used"] = endpoint_used
    return data

def get_weather_context(
    bbox: list[float], 
    start_date: str, 
    end_date: str, 
    event_date: Optional[str] = None
) -> Optional[WeatherContext]:
    """
    Retrieves weather context (precipitation, soil moisture) for the given BBox and period.
    Fails gracefully and returns None if the API fails.
    """
    try:
        # Use centroid for weather data
        lon = (bbox[0] + bbox[2]) / 2.0
        lat = (bbox[1] + bbox[3]) / 2.0

        data = _fetch_open_meteo(lat=lat, lon=lon, start_date=start_date, end_date=end_date)
        daily = data.get("daily", {})
        times = daily.get("time", [])
        precip = daily.get("precipitation_sum", [])
        soil_moisture = daily.get("soil_moisture_0_to_10cm_mean", [])

        if not precip or not times:
            return None

        # Handle nulls in precipitation array (can happen in Open-Meteo)
        precip = [p if p is not None else 0.0 for p in precip]

        total_precip = sum(precip)
        peak_idx = precip.index(max(precip))
        peak_precip = precip[peak_idx]
        peak_day = times[peak_idx]

        # Configurable thresholds for LOW/MODERATE/HIGH
        if total_precip < 10.0:
            rainfall_class = "LOW"
        elif total_precip < 50.0:
            rainfall_class = "MODERATE"
        else:
            rainfall_class = "HIGH"

        antecedent_rainfall = None
        if event_date:
            event_dt = dt.date.fromisoformat(event_date)
            ant_sum = 0.0
            for i, t_str in enumerate(times):
                t_dt = dt.date.fromisoformat(t_str)
                if t_dt < event_dt:
                    ant_sum += precip[i]
            antecedent_rainfall = ant_sum

        valid_soil = [s for s in soil_moisture if s is not None]
        mean_soil = sum(valid_soil) / len(valid_soil) if valid_soil else None

        return WeatherContext(
            endpoint_used=data["_endpoint_used"],
            total_precipitation_mm=round(total_precip, 2),
            peak_daily_precipitation_mm=round(peak_precip, 2),
            peak_day=peak_day,
            rainfall_class=rainfall_class,
            antecedent_rainfall_mm=round(antecedent_rainfall, 2) if antecedent_rainfall is not None else None,
            mean_soil_moisture_pct=round(mean_soil, 3) if mean_soil is not None else None
        )
    except Exception as e:
        logger.warning(f"Failed to fetch weather context: {e}")
        return None

def detect_event_date(bbox: list[float], start_date: str, end_date: str) -> Optional[str]:
    """
    Detects the likely 'event date' (e.g., peak rainfall day) for event-anchored missions.
    """
    context = get_weather_context(bbox, start_date, end_date)
    if context:
        return context.peak_day
    return None
