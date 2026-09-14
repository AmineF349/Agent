import pytest
import pandas as pd
import numpy as np
from app.services.data_quality_checker import DataQualityChecker

def test_data_quality_basic():
    checker = DataQualityChecker()
    prices = [45, 42, 38, 52, 68, 78, 85, 82, 75, 68]
    report = checker.check_prices(prices)
    assert report.total_rows == 10
    assert report.quality_score >= 0
    assert report.quality_score <= 100

def test_data_quality_missing():
    checker = DataQualityChecker()
    df = pd.DataFrame({"price": [45, None, 38, None, 68]})
    report = checker.check_dataframe(df, data_type="price")
    assert len([i for i in report.issues if i.type == "missing"]) > 0
    assert report.missing_pct["price"] > 0

def test_data_quality_anomaly():
    checker = DataQualityChecker()
    # Include extreme outlier
    prices = [50]*100 + [500]  # 500 is outlier
    report = checker.check_prices(prices)
    # Should detect anomaly
    assert len(report.issues) > 0

def test_data_quality_negative_hours():
    checker = DataQualityChecker()
    df = pd.DataFrame({
        "price": [45, -5, -10, 50, 60],
        "solar": [10, 80, 90, 20, 10]
    })
    report = checker.check_dataframe(df, data_type="price")
    # Should detect inconsistency negative price with low solar? Actually high solar with negative is normal, low solar with negative is suspicious
    # Our test has high solar with negative - should be OK, but check still runs
    assert report.total_rows == 5
