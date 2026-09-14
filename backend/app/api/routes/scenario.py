from fastapi import APIRouter
import logging

from ...services.scenario_challenger import ScenarioChallenger
from ...models.schemas import ScenarioInput, ScenarioChallengerResponse

router = APIRouter()
challenger = ScenarioChallenger()
logger = logging.getLogger(__name__)

@router.post("/challenge", response_model=ScenarioChallengerResponse)
async def challenge_scenario(scenario: ScenarioInput):
    """
    Challenge scénario AFRY / Aurora / Interne
    Détecte:
    - Hypothèses inhabituelles
    - Écarts historiques
    - Incohérences économiques
    """
    logger.info(f"Challenging scenario: {scenario.scenario_name} {scenario.model_type} {scenario.country} {scenario.horizon}")
    result = challenger.challenge(scenario)
    return result

@router.get("/benchmarks/{country}")
async def get_benchmarks(country: str = "FR"):
    from ...models.domain import BENCHMARKS, AFRY_RANGES, AURORA_RANGES
    return {
        "country": country.upper(),
        "benchmarks": BENCHMARKS.get(country.upper(), BENCHMARKS["FR"]),
        "afry_ranges": AFRY_RANGES,
        "aurora_ranges": AURORA_RANGES
    }

@router.get("/afry-vs-aurora")
async def afry_vs_aurora():
    return {
        "AFRY BID3": {
            "description": "Modèle fondamental optimisation dispatch hourly, EU 30+ ans",
            "strengths": ["Très détaillé réseau", "Bonne modélisation interco", "Utilisé par utilities"],
            "typical_assumptions": "Gas 30-45€ 2030, CO2 100-140€, demande FR 550-620 TWh",
            "focus": "Réseau + dispatch"
        },
        "Aurora": {
            "description": "Modèle prix + capture rates, focus valorisation RES/BESS",
            "strengths": ["Capture rates détaillés", "BESS modeling", "Scénarios policy"],
            "typical_assumptions": "Gas 28-42€ 2030, CO2 90-130€, capture solaire 0.65-0.85",
            "focus": "Valorisation + flexibilité"
        },
        "comparison": "AFRY plus conservateur sur prix, Aurora plus optimiste sur flexibilité. Écart baseload 10-20% fréquent en 2030."
    }
