import os
import requests
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Charge le .env de la racine du depot (BACKEND_URL, ports...) sans ecraser les
# variables deja presentes dans l'environnement (start.ps1 / docker-compose).
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
except Exception:  # pragma: no cover - python-dotenv absent ou .env illisible
    pass

class APIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("BACKEND_URL", "http://localhost:8000")
        self.base_url = self.base_url.rstrip("/")
        logger.info(f"APIClient init: {self.base_url}")

    def health(self) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e), "backend_url": self.base_url}

    def market_analysis(self, prices: List[float], generation: Optional[List[float]] = None, country: str = "FR", technology: str = "solar") -> Dict[str, Any]:
        payload = {
            "prices": prices,
            "generation": generation,
            "country": country,
            "technology": technology
        }
        resp = requests.post(f"{self.base_url}/api/v1/market-analysis/analyze", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def data_quality_csv(self, file_path: str, data_type: str = "price") -> Dict[str, Any]:
        with open(file_path, 'rb') as f:
            files = {"file": f}
            data = {"data_type": data_type}
            resp = requests.post(f"{self.base_url}/api/v1/data-quality/check", files=files, data=data, timeout=30)
            resp.raise_for_status()
            return resp.json()

    def challenge_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(f"{self.base_url}/api/v1/scenario/challenge", json=scenario, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def prepare_meeting(self, meeting_type: str, topic: str, context: str = "", duration: int = 60) -> Dict[str, Any]:
        payload = {
            "meeting_type": meeting_type,
            "topic": topic,
            "context": context,
            "duration_min": duration
        }
        resp = requests.post(f"{self.base_url}/api/v1/meeting/prepare", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def generate_minutes(self, meeting_type: str, raw_notes: str) -> Dict[str, Any]:
        payload = {"meeting_type": meeting_type, "raw_notes": raw_notes}
        resp = requests.post(f"{self.base_url}/api/v1/meeting/minutes", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def generate_presentation(self, presentation_type: str, title: str, slides: List[Dict[str, Any]], subtitle: str = "", country: str = "FR") -> Dict[str, Any]:
        payload = {
            "presentation_type": presentation_type,
            "title": title,
            "subtitle": subtitle,
            "slides": slides,
            "country": country,
            "author": "Power Market Intelligence Agent"
        }
        resp = requests.post(f"{self.base_url}/api/v1/presentation/generate", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def knowledge_search(self, query: str, category: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
        payload = {"query": query, "category": category, "top_k": top_k}
        resp = requests.post(f"{self.base_url}/api/v1/knowledge/search", json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def fetch_market_data(self, country: str = "FR", data_type: str = "day_ahead_prices", start_date: str = "2024-01-01", end_date: str = "2024-01-31") -> Dict[str, Any]:
        payload = {"country": country, "data_type": data_type, "start_date": start_date, "end_date": end_date}
        resp = requests.post(f"{self.base_url}/api/v1/market-data/fetch", json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def live_prices(self, country: str = "FR") -> Dict[str, Any]:
        resp = requests.get(f"{self.base_url}/api/v1/market-data/live/{country}", timeout=15)
        resp.raise_for_status()
        return resp.json()

    def agent_chat(self, query: str, country: str = "FR") -> Dict[str, Any]:
        resp = requests.post(f"{self.base_url}/api/v1/agent/chat", params={"query": query, "country": country}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def bess_revenue(self, prices: List[float], capacity_mw: float = 10, duration_h: float = 2) -> Dict[str, Any]:
        payload = {"prices": prices, "capacity_mw": capacity_mw, "duration_h": duration_h}
        # Note: endpoint expects prices as body? Actually query params
        resp = requests.post(f"{self.base_url}/api/v1/market-analysis/bess-revenue", json=prices, params={"capacity_mw": capacity_mw, "duration_h": duration_h}, timeout=20)
        # Fallback try different format
        if resp.status_code != 200:
            resp = requests.post(f"{self.base_url}/api/v1/market-analysis/bess-revenue?capacity_mw={capacity_mw}&duration_h={duration_h}", json=prices, timeout=20)
        resp.raise_for_status()
        return resp.json()
