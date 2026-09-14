"""
Energy-Charts.info API Connector - Public, Free, No Key Required
https://api.energy-charts.info/
Fraunhofer ISE open data
"""
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EnergyChartsConnector:
    """
    Connector for Energy-Charts.info - 100% public and free
    Provides day-ahead prices, generation, etc.
    """
    BASE_URL = "https://api.energy-charts.info"

    # Mapping countries to bidding zones used by Energy-Charts
    COUNTRY_TO_ZONE = {
        "FR": "FR",
        "DE": "DE-LU",
        "BE": "BE",
        "NL": "NL",
        "ES": "ES",
        "IT": "IT-North",
        "GB": "GB",
        "PL": "PL",
        "AT": "AT",
        "CH": "CH"
    }

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def get_day_ahead_prices(self, country: str = "FR", year: int = 2024) -> List[Dict[str, Any]]:
        """
        Fetch day-ahead prices
        Endpoint: /price?bzn=FR&year=2024
        """
        try:
            zone = self.COUNTRY_TO_ZONE.get(country.upper(), country.upper())
            # Energy-Charts price endpoint
            url = f"{self.BASE_URL}/price"
            params = {"bzn": zone, "year": year}
            logger.info(f"Fetching Energy-Charts prices: {url} {params}")
            resp = self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            # Parse: data has unix_seconds, price, etc.
            unix_seconds = data.get("unix_seconds", [])
            prices = data.get("price", [])
            result = []
            for ts, price in zip(unix_seconds, prices):
                if price is None:
                    continue
                dt = datetime.utcfromtimestamp(ts)
                result.append({
                    "timestamp": dt.isoformat(),
                    "price": float(price),
                    "country": country,
                    "unit": "EUR/MWh"
                })
            logger.info(f"Fetched {len(result)} price points for {country}")
            return result
        except Exception as e:
            logger.warning(f"Energy-Charts price fetch failed: {e}, using fallback mock")
            return self._mock_prices(country)

    def get_renewable_generation(self, country: str = "FR") -> Dict[str, Any]:
        """
        Fetch public renewable stats
        """
        try:
            # Try public API for installed power
            url = f"{self.BASE_URL}/installed_power"
            params = {"country": country.lower(), "time_step": "yearly"}
            resp = self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            return {"mock": True, "country": country}
        except Exception as e:
            logger.warning(f"Energy-Charts generation fetch failed: {e}")
            return {"mock": True, "country": country}

    def get_spot_prices_last_days(self, country: str = "FR", days: int = 30) -> List[Dict[str, Any]]:
        """
        For recent data, we may need to aggregate yearly and filter
        """
        year = datetime.utcnow().year
        all_data = self.get_day_ahead_prices(country, year)
        # Filter last N days
        cutoff = datetime.utcnow() - timedelta(days=days)
        filtered = [d for d in all_data if datetime.fromisoformat(d["timestamp"]) >= cutoff]
        if not filtered:
            return all_data[-days*24:] if len(all_data) > days*24 else all_data
        return filtered

    def _mock_prices(self, country: str) -> List[Dict[str, Any]]:
        """Fallback mock generation if API unavailable"""
        from .mock_generator import MockDataGenerator
        gen = MockDataGenerator()
        return gen.generate_prices(country=country, days=30)

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.BASE_URL}/price", params={"bzn": "FR", "year": 2024}, timeout=5)
            return resp.status_code == 200
        except:
            return False
