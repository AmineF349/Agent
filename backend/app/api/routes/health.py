import threading
import time
from typing import Any, Dict

from fastapi import APIRouter

from ...core.config import settings
from ...data.connectors import EnergyChartsConnector, OpenMeteoConnector

router = APIRouter()

# ---------------------------------------------------------------------------
# Sonde des APIs publiques (Energy-Charts / Open-Meteo)
#
# Sur un poste d'entreprise (proxy, filtrage sortant), un appel réseau externe
# peut mettre plusieurs secondes à échouer. /health ne doit jamais bloquer
# là-dessus (sinon le frontend affiche "Backend KO" alors qu'il tourne) :
# la sonde s'exécute en arrière-plan et /health renvoie le dernier état connu.
# ---------------------------------------------------------------------------
_PROBE_TTL_SECONDS = 300
_probe_lock = threading.Lock()
_probe_state: Dict[str, Any] = {
    "energy_charts": None,   # None = pas encore vérifié
    "open_meteo": None,
    "checked_at": None,
    "running": False,
}


def _run_probe() -> None:
    try:
        ec = EnergyChartsConnector().health_check()
        om = OpenMeteoConnector().health_check()
    except Exception:
        ec, om = False, False
    with _probe_lock:
        _probe_state.update({"energy_charts": ec, "open_meteo": om, "checked_at": time.time(), "running": False})


def refresh_public_api_probe_async() -> None:
    """Relance la sonde en tâche de fond si le dernier résultat est périmé."""
    with _probe_lock:
        checked_at = _probe_state["checked_at"]
        stale = checked_at is None or (time.time() - checked_at) > _PROBE_TTL_SECONDS
        if not stale or _probe_state["running"]:
            return
        _probe_state["running"] = True
    threading.Thread(target=_run_probe, name="public-api-probe", daemon=True).start()


def public_api_status(sync: bool = False) -> Dict[str, Any]:
    if sync:
        _run_probe()
    else:
        refresh_public_api_probe_async()
    with _probe_lock:
        return {
            "energy_charts": _probe_state["energy_charts"],
            "open_meteo": _probe_state["open_meteo"],
            "checked_at": _probe_state["checked_at"],
        }


@router.get("/health")
def health_check(sync: bool = False):
    """
    État du backend. Répond immédiatement (les APIs publiques sont sondées en
    arrière-plan). `?sync=true` force une vérification réseau synchrone.
    """
    apis = public_api_status(sync=sync)
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "llm_available": settings.has_llm,
        "llm_type": "openai" if settings.OPENAI_API_KEY else "anthropic" if settings.ANTHROPIC_API_KEY else "fallback",
        "entsoe_enabled": settings.has_entsoe,
        "public_apis": {
            "energy_charts": apis["energy_charts"],
            "open_meteo": apis["open_meteo"],
        },
        "public_apis_checked_at": apis["checked_at"],
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
