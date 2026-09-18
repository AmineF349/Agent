"""Utilitaires du frontend Streamlit.

Pourquoi ce module contient de la logique
-----------------------------------------
Toutes les pages font `from utils.api_client import APIClient` : ce paquet est
donc importe en premier, ce qui en fait le bon endroit pour preparer
``sys.path`` une seule fois.

Les pages utilisent des imports directs du code backend, par exemple ::

    from backend.app.services.market_analysis_engine import MarketAnalysisEngine

pour pouvoir calculer localement sans dependre de la disponibilite du backend.
Ces imports ne fonctionnent que si la **racine du depot** est presente dans
``sys.path`` (``backend`` est un paquet d'espace de noms PEP 420 : il n'y a pas
de ``backend/__init__.py``). Sans cet ajout, la page "Data Analysis" plante des
l'affichage avec ``ModuleNotFoundError: No module named 'backend'``.

Modes d'execution
-----------------
* **Natif Windows** (``setup.ps1`` / ``start.ps1``) : backend et frontend
  partagent le meme ``.venv``, les dependances du backend sont donc deja
  installees et les imports ``backend.*`` fonctionnent.
* **Docker** : l'image ``Dockerfile.frontend`` ne contient que ``frontend/``,
  le paquet ``backend`` est absent. ``backend_available()`` renvoie alors
  ``False`` et l'appelant doit passer par l'API HTTP (``APIClient``).
"""
import os
import sys

_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))   # <repo>/frontend/utils
APP_DIR = os.path.dirname(_UTILS_DIR)                     # <repo>/frontend
REPO_ROOT = os.path.dirname(APP_DIR)                      # <repo>

# APP_DIR en premier (import "utils.*" / "components.*"), puis la racine.
for _path in (REPO_ROOT, APP_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)


def backend_available() -> bool:
    """True si le code source du backend est importable depuis ce processus."""
    return os.path.isdir(os.path.join(REPO_ROOT, "backend", "app"))
