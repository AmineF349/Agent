from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
import pandas as pd
import io
import logging

from ...services.data_quality_checker import DataQualityChecker
from ...models.schemas import DataQualityReport

router = APIRouter()
checker = DataQualityChecker()
logger = logging.getLogger(__name__)

@router.post("/check", response_model=DataQualityReport)
async def check_data_quality(
    file: UploadFile = File(..., description="CSV or Excel file"),
    data_type: str = Form("price", description="Type: price, capacity, energy, etc.")
):
    """
    Vérifie qualité d'un fichier de données marché
    - Détecte valeurs manquantes, anomalies, incohérences, unités
    """
    try:
        content = await file.read()
        # Try CSV then Excel
        try:
            df = pd.read_csv(io.BytesIO(content))
        except:
            df = pd.read_excel(io.BytesIO(content))

        logger.info(f"Checking data quality: {file.filename} shape {df.shape}")
        report = checker.check_dataframe(df, data_type=data_type)
        return report
    except Exception as e:
        logger.error(f"Data quality check failed: {e}")
        raise

@router.post("/check-prices")
async def check_prices(prices: list[float], data_type: str = "price"):
    """Quick check for price list"""
    report = checker.check_prices(prices)
    suggestions = checker.suggest_fixes(report)
    return {"report": report, "suggestions": suggestions}
