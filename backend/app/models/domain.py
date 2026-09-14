"""
Domain models and constants for European Power Markets
"""
from enum import Enum

class Country(str, Enum):
    FR = "FR"
    DE = "DE"
    BE = "BE"
    NL = "NL"
    ES = "ES"
    IT = "IT"
    GB = "GB"
    PL = "PL"
    CH = "CH"
    AT = "AT"

class Technology(str, Enum):
    SOLAR = "solar"
    WIND_ONSHORE = "wind_onshore"
    WIND_OFFSHORE = "wind_offshore"
    HYDRO = "hydro"
    NUCLEAR = "nuclear"
    GAS = "gas"
    COAL = "coal"
    BESS = "bess"

# Reference benchmarks for scenario challenging (European averages 2024)
BENCHMARKS = {
    "FR": {
        "baseload_2024": 65.0,  # EUR/MWh
        "gas_price": {"min": 20, "max": 60, "typical": 35},
        "co2_price": {"min": 50, "max": 150, "typical": 80},
        "demand_growth": {"min": -0.02, "max": 0.03, "typical": 0.01},
        "solar_cf": {"min": 0.12, "max": 0.16, "typical": 0.14},
        "wind_onshore_cf": {"min": 0.22, "max": 0.30, "typical": 0.26},
        "nuclear_availability": {"min": 0.65, "max": 0.85, "typical": 0.75},
    },
    "DE": {
        "baseload_2024": 78.0,
        "gas_price": {"min": 20, "max": 60, "typical": 35},
        "co2_price": {"min": 50, "max": 150, "typical": 80},
        "demand_growth": {"min": -0.01, "max": 0.02, "typical": 0.005},
        "solar_cf": {"min": 0.10, "max": 0.13, "typical": 0.115},
        "wind_onshore_cf": {"min": 0.20, "max": 0.28, "typical": 0.24},
        "nuclear_availability": {"min": 0.0, "max": 0.1, "typical": 0.0},
    }
}

# AFRY BID3 typical assumptions ranges
AFRY_RANGES = {
    "gas_price_2030": (25, 55),
    "co2_price_2030": (90, 180),
    "demand_2030_TWh": {"FR": (500, 650), "DE": (550, 700)},
    "solar_capacity_2030_GW": {"FR": (30, 60), "DE": (150, 250)},
    "wind_capacity_2030_GW": {"FR": (40, 70), "DE": (100, 160)},
    "interconnector_FR_DE": (4, 8),  # GW
}

# Aurora typical
AURORA_RANGES = {
    "gas_price_2030": (22, 50),
    "co2_price_2030": (80, 160),
    "capture_rate_solar_2030": (0.6, 0.95),
    "capture_rate_wind_2030": (0.75, 1.05),
    "negative_hours_2030": (50, 800),
}
