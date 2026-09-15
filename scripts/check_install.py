"""
Verification post-installation (appele par setup.ps1 / setup.sh, utilisable seul) :

    .venv\Scripts\python.exe scripts\check_install.py

- verifie la version de Python,
- verifie que les dependances critiques s'importent,
- importe l'application backend (detecte les erreurs de code / de chemins),
- affiche les chemins resolus (knowledge base, fichiers generes, .env).

Code de sortie 0 = OK, 1 = probleme (details sur la sortie standard).
"""
import importlib
import io
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONUTF8", "1")

# Les warnings emis par certaines bibliotheques a l'import (pydantic, requests...)
# partent sur stderr : on les capture pour que setup.ps1 n'affiche que les resultats.
_stderr_capture = io.StringIO()
_real_stderr = sys.stderr
sys.stderr = _stderr_capture

REPO_ROOT = Path(__file__).resolve().parents[1]  # scripts/check_install.py -> racine du depot
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

problems = []

# --- 1. Version de Python ---------------------------------------------------
major, minor = sys.version_info[:2]
if not (major == 3 and 10 <= minor <= 12):
    problems.append(f"Python {major}.{minor} non supporte (3.10 - 3.12 requis)")

# --- 2. Dependances ---------------------------------------------------------
REQUIRED = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic-settings",
    "pandas": "pandas",
    "numpy": "numpy",
    "pptx": "python-pptx",
    "docx": "python-docx",
    "reportlab": "reportlab",
    "httpx": "httpx",
    "requests": "requests",
    "streamlit": "streamlit",
    "plotly": "plotly",
    "multipart": "python-multipart",
    "openpyxl": "openpyxl",
}
missing = []
for module, dist in REQUIRED.items():
    try:
        importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001
        missing.append(f"{dist} ({exc.__class__.__name__}: {exc})")
if missing:
    problems.append("Modules manquants : " + ", ".join(missing))

# --- 3. Import de l'application backend --------------------------------------
if not missing:
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        import logging

        logging.disable(logging.CRITICAL)
        from app.core import paths  # noqa: E402
        from app.main import app  # noqa: E402,F401

        logging.disable(logging.NOTSET)
        n_routes = len([r for r in app.routes if getattr(r, "path", "").startswith("/api/")])
        print(f"Backend importable ({n_routes} routes API)")
        print(f"Knowledge base : {paths.KNOWLEDGE_BASE_DIR} ({len(list(paths.KNOWLEDGE_BASE_DIR.rglob('*.md')))} fichiers .md)")
        print(f"Fichiers generes : {paths.GENERATED_DIR}")
        print(f"Fichier .env : {paths.ENV_FILE} ({'present' if paths.ENV_FILE.exists() else 'absent - valeurs par defaut'})")
        if not paths.KNOWLEDGE_BASE_DIR.exists():
            problems.append(f"Knowledge base introuvable : {paths.KNOWLEDGE_BASE_DIR}")
    except Exception as exc:  # noqa: BLE001
        import traceback

        problems.append("Import du backend impossible :\n" + traceback.format_exc())

    # Frontend : import du client API et des chemins (pas de lancement Streamlit)
    try:
        sys.path.insert(0, str(FRONTEND_DIR))
        from utils import api_client, paths as fpaths  # noqa: E402,F401

        print(f"Frontend importable (BACKEND_URL={os.getenv('BACKEND_URL', 'http://localhost:8000')})")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"Import du frontend impossible : {exc}")

print(f"Python {sys.version.split()[0]} ({sys.executable})")

sys.stderr = _real_stderr
if problems:
    print("")
    print("PROBLEMES :")
    for p in problems:
        print(" - " + p)
    captured = _stderr_capture.getvalue().strip()
    if captured:
        print("")
        print("Sortie d'erreur capturee :")
        print(captured[-4000:])
    sys.exit(1)

sys.exit(0)
