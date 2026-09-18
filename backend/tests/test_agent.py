from app.agent.langgraph_agent import PowerMarketAgent


def test_agent_comparison_uses_structured_price_context():
    agent = PowerMarketAgent()
    result = agent.run(
        "Compare prices between the two loaded series",
        context={
            "country": "FR",
            "comparison": {
                "series": [
                    {"name": "baseline", "prices": [10, 20, 30, 40] * 6},
                    {"name": "stress", "prices": [20, 30, 40, 50] * 6},
                ]
            },
        },
    )

    assert result["intent"] == "comparison"
    comparison = result["results"]["comparison"]
    assert comparison["series"][0]["name"] == "baseline"
    assert comparison["delta"]["baseload"] == -10.0


def test_agent_comparison_reports_missing_series():
    agent = PowerMarketAgent()
    result = agent.run("Compare prices", context={"country": "FR"})

    assert result["intent"] == "comparison"
    assert "error" in result["results"]["comparison"]
