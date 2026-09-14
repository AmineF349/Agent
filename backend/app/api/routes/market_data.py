from fastapi import APIRouter
from typing import Optional
import logging

from ...data.connectors import EnergyChartsConnector, OpenMeteoConnector, EntsoeConnector, MockDataGenerator
from ...models.schemas import MarketDataRequest, MarketDataResponse
from ...core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Init connectors
energy_charts = EnergyChartsConnector()
open_meteo = OpenMeteoConnector()
entsoe = EntsoeConnector(api_key=settings.ENTSOE_API_KEY)
mock_gen = MockDataGenerator()

@router.post("/fetch", response_model=MarketDataResponse)
async def fetch_market_data(request: MarketDataRequest):
    """
    Fetch market data via public APIs:
    - Energy-Charts.info (gratuit, sans clé) - day-ahead prices
    - Open-Meteo (gratuit) - weather for RES proxies
    - ENTSO-E (optionnel, clé gratuite) - si configuré
    - Fallback mock si APIs indisponibles
    """
    logger.info(f"Fetching market data: {request.country} {request.data_type} {request.start_date} to {request.end_date}")

    try:
        if request.data_type == "day_ahead_prices":
            # Try Energy-Charts first (public, no key)
            data = energy_charts.get_day_ahead_prices(country=request.country, year=2024)
            # Filter by date if needed (simplified)
            return MarketDataResponse(
                country=request.country,
                data_type=request.data_type,
                data=data[:500],  # Limit
                source="energy-charts.info (public, free)",
                cached=False
            )
        elif request.data_type in ["wind", "solar"]:
            # Use Open-Meteo for weather proxies
            weather = open_meteo.get_historical_weather(
                country=request.country,
                start_date=request.start_date,
                end_date=request.end_date
            )
            return MarketDataResponse(
                country=request.country,
                data_type=request.data_type,
                data=weather.get("data", [])[:500],
                source="open-meteo.com (public, free)",
                cached=False
            )
        elif request.data_type == "load":
            data = mock_gen.generate_load(country=request.country, days=30)
            return MarketDataResponse(
                country=request.country,
                data_type=request.data_type,
                data=data,
                source="mock (fallback)",
                cached=False
            )
        else:
            data = mock_gen.generate_prices(country=request.country, days=30)
            return MarketDataResponse(
                country=request.country,
                data_type=request.data_type,
                data=data,
                source="mock",
                cached=False
            )
    except Exception as e:
        logger.error(f"Market data fetch failed: {e}")
        # Fallback mock
        data = mock_gen.generate_prices(country=request.country, days=30)
        return MarketDataResponse(
            country=request.country,
            data_type=request.data_type,
            data=data,
            source=f"mock fallback due to error: {str(e)}",
            cached=False
        )

@router.get("/live/{country}")
async def live_prices(country: str = "FR"):
    """Quick live prices for dashboard"""
    try:
        data = energy_charts.get_spot_prices_last_days(country=country, days=7)
        return {
            "country": country,
            "count": len(data),
            "latest": data[-1] if data else None,
            "prices_last_week": data[-24*7:] if len(data) > 24*7 else data,
            "source": "energy-charts.info"
        }
    except Exception as e:
        data = mock_gen.generate_prices(country=country, days=7)
        return {
            "country": country,
            "count": len(data),
            "latest": data[-1] if data else None,
            "prices_last_week": data,
            "source": f"mock fallback: {e}"
        }

@router.get("/weather/{country}")
async def weather_forecast(country: str = "FR", days: int = 7):
    """Weather forecast for RES"""
    try:
        forecast = open_meteo.get_weather_forecast(country=country, days=days)
        historical = open_meteo.get_historical_weather(country=country)
        return {
            "country": country,
            "forecast": forecast,
            "historical_sample": historical.get("data", [])[:24],
            "source": "open-meteo.com (free)"
        }
    except Exception as e:
        return {"error": str(e), "country": country}

@router.get("/sources")
async def data_sources():
    return {
        "energy_charts": {
            "name": "Energy-Charts.info (Fraunhofer ISE)",
            "url": "https://api.energy-charts.info",
            "auth": "None - 100% public",
            "data": ["day_ahead_prices", "generation", "installed_power"],
            "status": energy_charts.health_check()
        },
        "open_meteo": {
            "name": "Open-Meteo",
            "url": "https://open-meteo.com/",
            "auth": "None - 100% public",
            "data": ["weather forecast", "historical weather", "solar radiation", "wind speed"],
            "status": open_meteo.health_check()
        },
        "entsoe": {
            "name": "ENTSO-E Transparency",
            "url": "https://transparency.entsoe.eu/",
            "auth": "Free API key required (optional)",
            "data": ["day_ahead_prices", "generation", "load", "cross-border flows"],
            "status": entsoe.health_check(),
            "configured": bool(settings.ENTSOE_API_KEY)
        },
        "mock": {
            "name": "Mock Generator (fallback)",
            "auth": "None",
            "data": ["prices", "renewable profiles", "load", "scenarios"],
            "status": True
        }
    }
