from fastapi import APIRouter
import logging

from ...services.meeting_copilot import MeetingCopilot
from ...models.schemas import MeetingRequest, MeetingResponse, MinutesRequest, MinutesResponse

router = APIRouter()
copilot = MeetingCopilot()
logger = logging.getLogger(__name__)

@router.post("/prepare", response_model=MeetingResponse)
async def prepare_meeting(request: MeetingRequest):
    """
    Prépare réunion:
    - Agenda détaillé
    - Questions challenge
    - Checklist préparation
    - Risques à soulever
    - Data à préparer
    """
    logger.info(f"Preparing meeting: {request.meeting_type} - {request.topic}")
    result = copilot.prepare_meeting(request)
    return result

@router.post("/minutes", response_model=MinutesResponse)
async def generate_minutes(request: MinutesRequest):
    """
    Génère compte rendu structuré à partir de notes brutes
    """
    logger.info(f"Generating minutes for {request.meeting_type}")
    result = copilot.generate_minutes(request)
    return result

@router.get("/templates")
async def meeting_templates():
    return {
        "AFRY Review": {
            "duration": "90 min",
            "objectives": ["Challenger hypothèses BID3", "Comparer Aurora", "Identifier écarts"],
            "participants": ["Analystes", "Modélisation", "Trading", "Stratégie"]
        },
        "COMEX": {
            "duration": "45 min",
            "objectives": ["Présenter vision marché", "Défendre hypothèses", "Obtenir arbitrage"],
            "participants": ["COMEX", "Direction", "Analystes"]
        },
        "Trading": {
            "duration": "30 min",
            "objectives": ["Vue court terme", "Hedging", "Signaux marché"],
            "participants": ["Traders", "Analystes"]
        }
    }
