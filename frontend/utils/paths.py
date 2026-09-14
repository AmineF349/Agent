"""
Chemins absolus utilisés par le frontend Streamlit.

Streamlit peut être lancé depuis n'importe quel répertoire (frontend/, racine du
dépôt, VS Code, start.ps1...) : on ne dépend donc jamais du répertoire courant.
"""
import os
import sys
from pathlib import Path

# .../frontend/utils/paths.py -> parents[1] = .../frontend
FRONTEND_DIR: Path = Path(__file__).resolve().parents[1]
REPO_ROOT: Path = FRONTEND_DIR.parent
BACKEND_DIR: Path = REPO_ROOT / "backend"


def _env_path(var_name: str, default: Path) -> Path:
    value = os.getenv(var_name)
    if value:
        return Path(value).expanduser().resolve()
    return default


# Mêmes variables d'environnement que le backend (voir backend/app/core/paths.py)
GENERATED_DIR: Path = _env_path("GENERATED_DIR", BACKEND_DIR / "generated")
DATA_SAMPLES_DIR: Path = _env_path("DATA_SAMPLES_DIR", BACKEND_DIR / "data_samples")
KNOWLEDGE_BASE_DIR: Path = _env_path("KNOWLEDGE_BASE_DIR", REPO_ROOT / "knowledge_base")


def enable_backend_imports() -> None:
    """
    Permet `from backend.app... import ...` depuis les pages Streamlit
    (mode "direct", sans passer par l'API HTTP) quel que soit le CWD.
    """
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
