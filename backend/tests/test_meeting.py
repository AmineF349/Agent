import pytest
from app.services.meeting_copilot import MeetingCopilot
from app.models.schemas import MeetingRequest, MinutesRequest

def test_meeting_prepare():
    copilot = MeetingCopilot()
    req = MeetingRequest(
        meeting_type="AFRY Review",
        topic="Revue scénario AFRY Central 2030 FR",
        duration_min=60,
        context="Écart AFRY vs Aurora 12%"
    )
    result = copilot.prepare_meeting(req)
    assert len(result.agenda) > 0
    assert len(result.key_questions) > 0
    assert len(result.preparation_checklist) > 0

def test_meeting_minutes():
    copilot = MeetingCopilot()
    req = MinutesRequest(
        meeting_type="AFRY Review",
        raw_notes="- Décidé: lancer sensibilité gas\n- Action: Alice met à jour modèle J+3\n- Question: BESS 5GW réaliste?",
        participants=["Alice", "Bob"]
    )
    result = copilot.generate_minutes(req)
    assert len(result.decisions) > 0 or len(result.actions) > 0
    assert result.formatted_minutes != ""

def test_meeting_templates():
    copilot = MeetingCopilot()
    assert "AFRY Review" in copilot.MEETING_TEMPLATES
    assert "COMEX" in copilot.MEETING_TEMPLATES
