from fastapi import APIRouter
from typing import List, Optional
import logging

from ...services.market_analysis_engine import MarketAnalysisEngine
from ...models.schemas import MarketAnalysisRequest, MarketAnalysisResponse

router = APIRouter()
engine = MarketAnalysisEngine()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=MarketAnalysisResponse)
async def analyze_market(request: MarketAnalysisRequest):
    """
    Calcule KPI marché:
    - Baseload, Peakload, Offpeak
    - Negative Hours, P10/P50/P90, Volatility
    - Capture Price, Capture Rate, MVF, Cannibalisation (si génération fournie)
    """
    logger.info(f"Market analysis: {len(request.prices)} prices, tech={request.technology}, country={request.country}")
    result = engine.analyze(
        prices=request.prices,
        generation=request.generation,
        timestamps=request.timestamps,
        country=request.country,
        technology=request.technology
    )
    return result

@router.post("/bess-revenue")
async def bess_revenue(
    prices: List[float],
    capacity_mw: float = 10,
    duration_h: float = 2,
    efficiency: float = 0.85
):
    """
    Estime revenu arbitrage BESS (perfect foresight simplifié)
    """
    result = engine.calculate_bess_revenue(prices, capacity_mw, duration_h, efficiency)
    return result

@router.get("/kpi-definitions")
async def kpi_definitions():
    return {
        "baseload": "Moyenne prix toutes heures",
        "peakload": "Moyenne Mon-Fri 8-20h (définition EU)",
        "offpeak": "Moyenne nuits + weekends",
        "negative_hours": "Nombre heures prix <0",
        "capture_price": "Σ(prix*gen)/Σ(gen) - prix capté par techno",
        "capture_rate": "Capture Price / Baseload - indique cannibalisation",
        "market_value_factor": "Synonyme capture rate (Aurora)",
        "cannibalisation_factor": "1 - capture_rate - perte valeur vs baseload",
        "volatility": "std/mean - mesure risque",
        "p10_p50_p90": "Percentiles distribution prix"
    }
