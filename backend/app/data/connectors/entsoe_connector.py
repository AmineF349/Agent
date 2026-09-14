"""
ENTSO-E Transparency Platform Connector
Requires free API key from https://transparency.entsoe.eu/
Optional - fallback to mock if not configured
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class EntsoeConnector:
    """
    ENTSO-E connector - optional, requires free API key
    If no key, falls back to mock data
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ENTSOE_API_KEY")
        self.enabled = bool(self.api_key)
        if self.enabled:
            try:
                from entsoe import EntsoePandasClient
                import pandas as pd
                self.client = EntsoePandasClient(api_key=self.api_key)
                self.pd = pd
                logger.info("ENTSO-E client initialized")
            except ImportError:
                logger.warning("entsoe-py not installed, ENTSO-E disabled")
                self.enabled = False
                self.client = None
        else:
            self.client = None
            logger.info("ENTSO-E API key not configured, using mock fallback")

    def get_day_ahead_prices(self, country: str = "FR", start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if not self.enabled:
            from .mock_generator import MockDataGenerator
            gen = MockDataGenerator()
            return gen.generate_prices(country=country, days=30)

        try:
            from entsoe.mappings import Area
            import pandas as pd

            if not start_date:
                start_date = pd.Timestamp(datetime.utcnow() - pd.Timedelta(days=7), tz="Europe/Brussels")
            if not end_date:
                end_date = pd.Timestamp(datetime.utcnow(), tz="Europe/Brussels")

            country_code = getattr(Area, country.upper(), Area.FR)
            prices = self.client.query_day_ahead_prices(country_code, start=start_date, end=end_date)

            result = []
            for ts, price in prices.items():
                result.append({
                    "timestamp": ts.isoformat(),
                    "price": float(price),
                    "country": country,
                    "unit": "EUR/MWh",
                    "source": "entsoe"
                })
            return result
        except Exception as e:
            logger.warning(f"ENTSO-E fetch failed: {e}, fallback to mock")
            from .mock_generator import MockDataGenerator
            gen = MockDataGenerator()
            return gen.generate_prices(country=country, days=30)

    def get_generation(self, country: str = "FR") -> Dict[str, Any]:
        if not self.enabled:
            return {"mock": True, "country": country}
        try:
            import pandas as pd
            from entsoe.mappings import Area
            start = pd.Timestamp(datetime.utcnow() - pd.Timedelta(days=1), tz="Europe/Brussels")
            end = pd.Timestamp(datetime.utcnow(), tz="Europe/Brussels")
            country_code = getattr(Area, country.upper(), Area.FR)
            gen = self.client.query_generation(country_code, start=start, end=end)
            return {"data": gen.to_dict(), "country": country, "source": "entsoe"}
        except Exception as e:
            logger.warning(f"ENTSO-E generation failed: {e}")
            return {"mock": True, "country": country, "error": str(e)}

    def health_check(self) -> bool:
        return self.enabled
