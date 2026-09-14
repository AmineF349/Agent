import pytest
from app.services.scenario_challenger import ScenarioChallenger
from app.models.schemas import ScenarioInput, ScenarioAssumption

def test_scenario_challenger_basic():
    challenger = ScenarioChallenger()
    scenario = ScenarioInput(
        scenario_name="Test AFRY 2030",
        model_type="AFRY",
        country="FR",
        horizon=2030,
        assumptions=[
            ScenarioAssumption(name="gas_price", value=38.5, unit="EUR/MWh", year=2030),
            ScenarioAssumption(name="co2_price", value=120, unit="EUR/t", year=2030),
            ScenarioAssumption(name="demand", value=580, unit="TWh", year=2030),
        ]
    )
    result = challenger.challenge(scenario)
    assert result.overall_score >= 0
    assert result.overall_score <= 100
    assert len(result.issues) >= 0
    assert "AFRY" in result.scenario_name or "Test" in result.scenario_name

def test_scenario_challenger_unusual_gas():
    challenger = ScenarioChallenger()
    scenario = ScenarioInput(
        scenario_name="High Gas",
        model_type="AFRY",
        country="FR",
        horizon=2030,
        assumptions=[
            ScenarioAssumption(name="gas_price", value=100, unit="EUR/MWh", year=2030),  # Very high
        ]
    )
    result = challenger.challenge(scenario)
    # Should detect unusual hypothesis
    assert len(result.issues) > 0
    assert any("gas" in i.assumption.lower() for i in result.issues)

def test_scenario_challenger_nuclear():
    challenger = ScenarioChallenger()
    scenario = ScenarioInput(
        scenario_name="Low Nuclear",
        model_type="AFRY",
        country="FR",
        horizon=2030,
        assumptions=[
            ScenarioAssumption(name="nuclear_availability", value=0.5, unit="factor", year=2030),
        ]
    )
    result = challenger.challenge(scenario)
    assert len(result.issues) > 0

def test_scenario_challenger_capture_rate():
    challenger = ScenarioChallenger()
    scenario = ScenarioInput(
        scenario_name="Low Capture",
        model_type="Aurora",
        country="FR",
        horizon=2030,
        assumptions=[
            ScenarioAssumption(name="solar_capture_rate", value=0.5, unit="factor", year=2030),
        ]
    )
    result = challenger.challenge(scenario)
    assert result.overall_score < 100  # Should have penalty
