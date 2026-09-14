"""
Open-Meteo API Connector - Public, Free, No Key Required
https://open-meteo.com/
Weather data for renewable generation proxies
"""
import httpx
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class OpenMeteoConnector:
    """
    Open-Meteo is 100% free and requires no API key
    Perfect for solar irradiance, wind speed, temperature
    """
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    # Capital coordinates for European countries
    COUNTRY_COORDS = {
        "FR": {"latitude": 48.8566, "longitude": 2.3522, "name": "Paris"},  # Paris
        "DE": {"latitude": 52.52, "longitude": 13.405, "name": "Berlin"},
        "ES": {"latitude": 40.4168, "longitude": -3.7038, "name": "Madrid"},
        "IT": {"latitude": 41.9028, "longitude": 12.4964, "name": "Rome"},
        "GB": {"latitude": 51.5072, "longitude": -0.1276, "name": "London"},
        "BE": {"latitude": 50.8503, "longitude": 4.3517, "name": "Brussels"},
        "NL": {"latitude": 52.3676, "longitude": 4.9041, "name": "Amsterdam"},
        "PL": {"latitude": 52.2297, "longitude": 21.0122, "name": "Warsaw"},
        "AT": {"latitude": 48.2082, "longitude": 16.3738, "name": "Vienna"},
        "CH": {"latitude": 46.9481, "longitude": 7.4474, "name": "Bern"},
    }

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def get_weather_forecast(self, country: str = "FR", days: int = 7) -> Dict[str, Any]:
        """Get weather forecast for renewable proxies"""
        try:
            coords = self.COUNTRY_COORDS.get(country.upper(), self.COUNTRY_COORDS["FR"])
            params = {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "hourly": "temperature_2m,wind_speed_10m,shortwave_radiation,cloud_cover",
                "forecast_days": days,
                "timezone": "Europe/Berlin"
            }
            logger.info(f"Fetching Open-Meteo forecast for {country}")
            resp = self.client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Open-Meteo forecast failed: {e}")
            return {"error": str(e), "mock": True}

    def get_historical_weather(self, country: str = "FR", start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get historical weather for backtesting renewable models"""
        try:
            if not start_date:
                start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.utcnow().strftime("%Y-%m-%d")

            coords = self.COUNTRY_COORDS.get(country.upper(), self.COUNTRY_COORDS["FR"])
            params = {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "start_date": start_date,
                "end_date": end_date,
                "hourly": "temperature_2m,wind_speed_10m,shortwave_radiation,direct_radiation",
                "timezone": "Europe/Berlin"
            }
            logger.info(f"Fetching Open-Meteo archive for {country} {start_date} to {end_date}")
            resp = self.client.get(self.ARCHIVE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            # Transform to more usable format
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            radiation = hourly.get("shortwave_radiation", [])
            wind = hourly.get("wind_speed_10m", [])

            # Simple solar and wind capacity factor proxies
            result = []
            for t, rad, w in zip(times, radiation, wind):
                # Solar CF proxy: radiation / 1000 (simplified)
                solar_cf = min(max((rad or 0) / 1000.0, 0), 1.0)
                # Wind CF proxy: cubic relation (simplified)
                wind_cf = min(((w or 0) / 12.0) ** 3, 1.0) if w else 0
                result.append({
                    "timestamp": t,
                    "solar_cf_proxy": round(solar_cf, 3),
                    "wind_cf_proxy": round(wind_cf, 3),
                    "radiation": rad,
                    "wind_speed": w
                })
            return {"country": country, "data": result, "source": "open-meteo"}
        except Exception as e:
            logger.warning(f"Open-Meteo archive failed: {e}")
            return {"country": country, "data": [], "error": str(e)}

    def health_check(self) -> bool:
        try:
            resp = self.client.get(self.BASE_URL, params={
                "latitude": 48.85, "longitude": 2.35,
                "hourly": "temperature_2m",
                "forecast_days": 1
            }, timeout=5)
            return resp.status_code == 200
        except:
            return False
