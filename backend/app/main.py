"""
Power Market Intelligence Agent - FastAPI Main
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .core.config import settings
from .core.logging import logger
from .core.paths import GENERATED_DIR, KNOWLEDGE_BASE_DIR
from .api.routes import health, data_quality, market_analysis, scenario, meeting, presentation, knowledge, market_data
from .agent.langgraph_agent import PowerMarketAgent
from .models.schemas import KnowledgeQuery

# Init FastAPI
app = FastAPI(
    title="Power Market Intelligence Agent",
    description="""
Copilote IA pour analystes marchés électriques européens.

**Modules:**
1. **Data Quality Checker** - Vérifie unités, anomalies, missing
2. **Market Analysis Engine** - Capture Price, Capture Rate, Baseload, Peakload, Negative Hours
3. **Scenario Challenger** - Challenge AFRY, Aurora, scénarios internes
4. **Meeting Copilot** - Prépare réunions, Q&A, CR
5. **PowerPoint Generator** - Slides management, COMEX, AFRY
6. **Knowledge Base** - Concepts marché, modèles, FAQ

**APIs publiques gratuites:**
- Energy-Charts.info (sans clé)
- Open-Meteo (sans clé)
- ENTSO-E (clé gratuite optionnelle)

**LLM:** Fonctionne sans clé (fallback local) ou avec OpenAI/Claude/Azure
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(data_quality.router, prefix="/api/v1/data-quality", tags=["Data Quality"])
app.include_router(market_analysis.router, prefix="/api/v1/market-analysis", tags=["Market Analysis"])
app.include_router(scenario.router, prefix="/api/v1/scenario", tags=["Scenario Challenger"])
app.include_router(meeting.router, prefix="/api/v1/meeting", tags=["Meeting Copilot"])
app.include_router(presentation.router, prefix="/api/v1/presentation", tags=["Presentation Generator"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"])
app.include_router(market_data.router, prefix="/api/v1/market-data", tags=["Market Data"])

# Agent endpoint
agent = PowerMarketAgent()

@app.post("/api/v1/agent/chat")
async def agent_chat(query: str, country: str = "FR", context: dict = None):
    """
    Agent conversationnel principal - route vers bon module via LangGraph
    """
    result = agent.run(query, context={"country": country, **(context or {})})
    suggestions = agent.proactive_suggestions(result.get("results", {}))
    return {
        **result,
        "proactive_suggestions": suggestions
    }

@app.get("/api/v1/agent/capabilities")
async def agent_capabilities():
    return {
        "agent": "Power Market Intelligence Agent",
        "version": "1.0.0",
        "mode": "LangGraph" if agent.langgraph_available else "Simple Routing",
        "llm_provider": agent.llm._client_type,
        "has_real_llm": agent.llm.has_real_llm(),
        "modules": {
            "data_quality": "Vérifie unités, anomalies, missing, incohérences",
            "market_analysis": "Capture Price, Capture Rate, Baseload, Peakload, Negative Hours, BESS",
            "scenario": "Challenge AFRY, Aurora, interne - hypothèses inhabituelles",
            "meeting": "Agenda, questions, checklist, CR",
            "presentation": "PPTX, DOCX, PDF - management, COMEX, AFRY",
            "knowledge": "Concepts marché, modèles, FAQ",
            "market_data": "Energy-Charts (free), Open-Meteo (free), ENTSO-E (optional)"
        },
        "example_queries": [
            "Analyse capture rate solaire FR avec 5000h prix",
            "Challenge scénario AFRY Central 2030 FR",
            "Prépare réunion COMEX sur valorisation renouvelable",
            "Explique negative hours et opportunité BESS",
            "Donne prix day-ahead FR dernière semaine"
        ]
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal error: {str(exc)}", "type": "internal_error"}
    )

# Startup
@app.on_event("startup")
async def startup_event():
    logger.info("="*80)
    logger.info("⚡ Power Market Intelligence Agent starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM: {agent.llm._client_type} (real LLM: {agent.llm.has_real_llm()})")
    logger.info(f"ENTSO-E: {'enabled' if settings.has_entsoe else 'disabled (mock fallback)'}")
    logger.info(f"Public APIs: Energy-Charts (free), Open-Meteo (free)")
    logger.info(f"Knowledge base: {KNOWLEDGE_BASE_DIR}")
    logger.info(f"Generated files: {GENERATED_DIR}")
    logger.info("Modules: Data Quality, Market Analysis, Scenario Challenger, Meeting, Presentation, Knowledge")
    logger.info(f"Docs: http://localhost:{settings.BACKEND_PORT}/docs")
    logger.info("="*80)
    # Sonde réseau des APIs publiques lancée en arrière-plan (ne bloque pas le démarrage)
    health.refresh_public_api_probe_async()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Power Market Intelligence Agent")
