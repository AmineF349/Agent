"""
Chemins du projet - résolus de façon absolue (indépendants du répertoire courant).

Objectif : le backend doit fonctionner identiquement qu'il soit lancé depuis
`backend/`, depuis la racine du dépôt, depuis VS Code, depuis un script Windows
(`start.ps1`) ou dans un conteneur Docker.

Chaque chemin peut être surchargé par une variable d'environnement.
"""
import os
from pathlib import Path

# .../backend/app/core/paths.py -> parents[2] = .../backend
BACKEND_DIR: Path = Path(__file__).resolve().parents[2]
REPO_ROOT: Path = BACKEND_DIR.parent


def _env_path(var_name: str, default: Path) -> Path:
    value = os.getenv(var_name)
    if value:
        return Path(value).expanduser().resolve()
    return default


# Fichiers générés (PPTX / DOCX / PDF)
GENERATED_DIR: Path = _env_path("GENERATED_DIR", BACKEND_DIR / "generated")
# Jeux de données d'exemple
DATA_SAMPLES_DIR: Path = _env_path("DATA_SAMPLES_DIR", BACKEND_DIR / "data_samples")
# Base de connaissances (markdown)
KNOWLEDGE_BASE_DIR: Path = _env_path("KNOWLEDGE_BASE_DIR", REPO_ROOT / "knowledge_base")
# Fichier .env (racine du dépôt)
ENV_FILE: Path = _env_path("PMIA_ENV_FILE", REPO_ROOT / ".env")


def ensure_runtime_dirs() -> None:
    """Crée les répertoires nécessaires à l'exécution (idempotent)."""
    for d in (GENERATED_DIR, DATA_SAMPLES_DIR):
        d.mkdir(parents=True, exist_ok=True)
