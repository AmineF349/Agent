from fastapi import APIRouter
from ...core.config import settings
from ...data.connectors import EnergyChartsConnector, OpenMeteoConnector

router = APIRouter()

@router.get("/health")
def health_check():
    ec = EnergyChartsConnector()
    om = OpenMeteoConnector()
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "llm_available": settings.has_llm,
        "llm_type": "openai" if settings.OPENAI_API_KEY else "anthropic" if settings.ANTHROPIC_API_KEY else "fallback",
        "entsoe_enabled": settings.has_entsoe,
        "public_apis": {
            "energy_charts": ec.health_check(),
            "open_meteo": om.health_check()
        },
        "modules": ["data_quality", "market_analysis", "scenario_challenger", "meeting_copilot", "presentation_generator", "knowledge_base"]
    }

@router.get("/")
def root():
    return {
        "name": "Power Market Intelligence Agent",
        "version": "1.0.0",
        "description": "Copilote IA pour analystes marchés électriques européens",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "data_quality": "/api/v1/data-quality",
            "market_analysis": "/api/v1/market-analysis",
            "scenario": "/api/v1/scenario",
            "meeting": "/api/v1/meeting",
            "presentation": "/api/v1/presentation",
            "knowledge": "/api/v1/knowledge",
            "market_data": "/api/v1/market-data",
            "agent": "/api/v1/agent"
        }
    }
