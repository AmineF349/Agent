"""
Mock Data Generator - For development and fallback when public APIs unavailable
Generates realistic European power market data
"""
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np

class MockDataGenerator:
    def __init__(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)

    def generate_prices(self, country: str = "FR", days: int = 30, base_price: float = None) -> List[Dict[str, Any]]:
        """Generate realistic hourly day-ahead prices with daily/weekly patterns"""
        base_prices = {
            "FR": 65, "DE": 78, "BE": 72, "NL": 75, "ES": 55, "IT": 85, "GB": 90, "PL": 95
        }
        base = base_price or base_prices.get(country.upper(), 70)

        now = datetime.utcnow()
        start = now - timedelta(days=days)
        data = []

        for i in range(days * 24):
            ts = start + timedelta(hours=i)
            hour = ts.hour
            weekday = ts.weekday()
            month = ts.month

            # Daily pattern: peak 8-20, off-peak night
            daily_factor = 1.0
            if 8 <= hour <= 20:
                daily_factor = 1.15 + 0.1 * math.sin((hour - 8) / 12 * math.pi)
            else:
                daily_factor = 0.75 + 0.1 * random.random()

            # Weekly pattern: lower weekend
            weekly_factor = 0.85 if weekday >= 5 else 1.0

            # Seasonal
            seasonal_factor = 1.0 + 0.2 * math.sin((month - 1) / 12 * 2 * math.pi - math.pi/2)

            # Random volatility + occasional negative prices (renewable cannibalization)
            noise = random.gauss(0, base * 0.15)
            price = base * daily_factor * weekly_factor * seasonal_factor + noise

            # 3% chance of negative prices in high renewable periods (spring/summer midday)
            if random.random() < 0.03 and 10 <= hour <= 16 and month in [3,4,5,6,7]:
                price = random.uniform(-20, 5)

            # Occasional price spikes
            if random.random() < 0.01:
                price = random.uniform(base * 2, base * 4)

            data.append({
                "timestamp": ts.isoformat(),
                "price": round(float(price), 2),
                "country": country,
                "unit": "EUR/MWh",
                "source": "mock"
            })
        return data

    def generate_renewable_profile(self, technology: str = "solar", days: int = 30, capacity_mw: float = 100) -> List[Dict[str, Any]]:
        """Generate renewable generation profile"""
        now = datetime.utcnow()
        start = now - timedelta(days=days)
        data = []

        for i in range(days * 24):
            ts = start + timedelta(hours=i)
            hour = ts.hour
            month = ts.month

            if technology == "solar":
                # Solar: only daylight, peak at noon, seasonal variation
                if 6 <= hour <= 19:
                    # Parabolic daylight curve
                    hour_factor = math.sin((hour - 6) / 13 * math.pi)
                    seasonal = 0.5 + 0.5 * math.sin((month - 3) / 12 * 2 * math.pi)
                    cf = max(0, hour_factor * seasonal * random.uniform(0.7, 1.0))
                else:
                    cf = 0
            elif "wind" in technology:
                # Wind: more random, higher in winter
                seasonal = 0.7 + 0.3 * math.sin((month - 1) / 12 * 2 * math.pi + math.pi)
                cf = max(0, min(1, random.gauss(0.35 * seasonal, 0.2)))
            else:
                cf = random.uniform(0.3, 0.9)

            generation = cf * capacity_mw

            data.append({
                "timestamp": ts.isoformat(),
                "technology": technology,
                "capacity_factor": round(cf, 3),
                "generation_mw": round(generation, 2),
                "capacity_mw": capacity_mw
            })
        return data

    def generate_load(self, country: str = "FR", days: int = 30) -> List[Dict[str, Any]]:
        """Generate load profile"""
        base_load = {"FR": 55000, "DE": 60000, "BE": 10000, "NL": 13000, "ES": 30000}
        base = base_load.get(country.upper(), 50000)
        now = datetime.utcnow()
        start = now - timedelta(days=days)
        data = []
        for i in range(days * 24):
            ts = start + timedelta(hours=i)
            hour = ts.hour
            weekday = ts.weekday()
            # Daily load shape
            if 8 <= hour <= 20:
                factor = 1.1
            elif 0 <= hour <= 5:
                factor = 0.75
            else:
                factor = 0.9
            if weekday >= 5:
                factor *= 0.85
            load = base * factor * random.uniform(0.9, 1.1)
            data.append({
                "timestamp": ts.isoformat(),
                "load_mw": round(load, 0),
                "country": country
            })
        return data

    def generate_scenario(self, model_type: str = "AFRY", country: str = "FR", year: int = 2030) -> Dict[str, Any]:
        """Generate mock scenario assumptions"""
        if model_type == "AFRY":
            return {
                "scenario_name": f"AFRY Central {year}",
                "model_type": "AFRY",
                "country": country,
                "horizon": year,
                "assumptions": [
                    {"name": "gas_price", "value": random.uniform(30, 45), "unit": "EUR/MWh", "year": year},
                    {"name": "co2_price", "value": random.uniform(100, 140), "unit": "EUR/t", "year": year},
                    {"name": "demand", "value": random.uniform(550, 620), "unit": "TWh", "year": year},
                    {"name": "solar_capacity", "value": random.uniform(35, 55), "unit": "GW", "year": year},
                    {"name": "wind_onshore_capacity", "value": random.uniform(30, 50), "unit": "GW", "year": year},
                    {"name": "wind_offshore_capacity", "value": random.uniform(8, 18), "unit": "GW", "year": year},
                    {"name": "nuclear_availability", "value": random.uniform(0.70, 0.80), "unit": "factor", "year": year},
                ]
            }
        else:
            return {
                "scenario_name": f"Aurora Central {year}",
                "model_type": "Aurora",
                "country": country,
                "horizon": year,
                "assumptions": [
                    {"name": "gas_price", "value": random.uniform(28, 42), "unit": "EUR/MWh", "year": year},
                    {"name": "co2_price", "value": random.uniform(90, 130), "unit": "EUR/t", "year": year},
                    {"name": "solar_capture_rate", "value": random.uniform(0.65, 0.85), "unit": "factor", "year": year},
                    {"name": "wind_capture_rate", "value": random.uniform(0.80, 1.0), "unit": "factor", "year": year},
                    {"name": "negative_hours", "value": random.uniform(100, 600), "unit": "hours", "year": year},
                ]
            }
