from pydantic_settings import BaseSettings
from typing import Optional, List

from .paths import ENV_FILE, ensure_runtime_dirs

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 8501

    # Public APIs (free, no key)
    ENERGY_CHARTS_BASE_URL: str = "https://api.energy-charts.info"
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    OPEN_METEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    ENTSOE_API_KEY: Optional[str] = None
    ENTSOE_BASE_URL: str = "https://web-api.tp.entsoe.eu/api"

    # LLM
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"

    DATABASE_URL: Optional[str] = None
    SECRET_KEY: str = "change-me-in-production-power-market-intelligence-2024"
    CORS_ORIGINS: str = "http://localhost:8501,http://localhost:3000"

    ENABLE_LLM: bool = True
    ENABLE_ENTSOE: bool = False
    MOCK_DATA_FALLBACK: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def has_llm(self) -> bool:
        return bool(self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY or self.AZURE_OPENAI_API_KEY)

    @property
    def has_entsoe(self) -> bool:
        return bool(self.ENTSOE_API_KEY)

    class Config:
        # Le .env de la racine du dépôt est chargé quel que soit le répertoire
        # courant (lancement depuis backend/, la racine, VS Code, start.ps1...).
        # Un .env dans le répertoire courant reste pris en compte en priorité.
        env_file = (str(ENV_FILE), ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Crée generated/ et data_samples/ à côté du code backend (chemins absolus),
# et non dans le répertoire courant.
ensure_runtime_dirs()
