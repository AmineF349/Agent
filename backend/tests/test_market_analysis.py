import pytest
import numpy as np
from app.services.market_analysis_engine import MarketAnalysisEngine

def test_market_analysis_basic():
    engine = MarketAnalysisEngine()
    prices = [45, 42, 38, 52, 68, 78, 85, 82, 75, 68, 65, 62]*10  # 120 hours
    metrics = engine.calculate_metrics(prices=prices, country="FR")
    assert metrics.baseload > 0
    assert metrics.peakload > 0
    assert metrics.negative_hours >= 0
    assert metrics.total_hours == len(prices)

def test_market_analysis_capture_rate():
    engine = MarketAnalysisEngine()
    prices = [50, 60, 70, 80, 90, 100]*10
    generation = [0, 0, 10, 50, 80, 90]*10  # Solar profile
    metrics = engine.calculate_metrics(prices=prices, generation=generation, technology="solar")
    assert metrics.capture_price is not None
    assert metrics.capture_rate is not None
    assert 0 < metrics.capture_rate < 2

def test_market_analysis_negative_hours():
    engine = MarketAnalysisEngine()
    prices = [45, -5, -10, 50, 60, -2]
    metrics = engine.calculate_metrics(prices=prices)
    assert metrics.negative_hours == 3
    assert metrics.negative_hours_pct == 50.0

def test_market_analysis_bess():
    engine = MarketAnalysisEngine()
    prices = list(np.random.normal(65, 20, 24*7))  # 1 week
    result = engine.calculate_bess_revenue(prices, capacity_mw=10, duration_h=2)
    assert "annual_revenue" in result
    assert result["annual_revenue"] > 0

def test_market_analysis_full():
    engine = MarketAnalysisEngine()
    prices = [45, 42, 38, 52, 68, 78, 85, 82, 75, 68]*10
    generation = [0, 0, 5, 15, 35, 55, 75, 85, 90, 85]*10
    response = engine.analyze(prices=prices, generation=generation, country="FR", technology="solar")
    assert response.metrics.baseload > 0
    assert len(response.insights) > 0
    assert "price_histogram" in response.chart_data
