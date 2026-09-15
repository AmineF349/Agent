# Guide VS Code - Power Market Intelligence Agent

## Ouverture Projet

1. Ouvrir VS Code
2. `File > Open Folder` -> sélectionner dossier `Agent`
3. VS Code détecte `.vscode/settings.json` et propose installer extensions recommandées -> Accepter

## Extensions Recommandées (auto)

- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter
- Flake8
- PowerShell
- YAML
- Jupyter

## Configuration Python

**Windows :** lancez d'abord `.\setup.ps1` (terminal PowerShell, à la racine). Le venv
`.venv\Scripts\python.exe` est alors présélectionné par `.vscode/settings.json`.

**Linux / macOS :** lancez `./setup.sh --dev` puis `Ctrl+Shift+P` (ou `Cmd+Shift+P`) ->
"Python: Select Interpreter" -> `.venv/bin/python` (le chemin par défaut de `settings.json`
vise le venv Windows ; VS Code détecte de toute façon le `.venv` du workspace).

Manuel (toutes plateformes) :

```bash
python -m venv .venv
source .venv/bin/activate                          # Windows : .\.venv\Scripts\Activate.ps1
pip install --only-binary :all: -r requirements.txt -r requirements-dev.txt
```

## Lancement Debug (F5)

### Option 1: Backend seul

- `F5` -> Choisir "Backend FastAPI"
- Lance `uvicorn app.main:app --reload --port 8000`
- Breakpoints dans `backend/app/...`
- Docs: http://localhost:8000/docs

### Option 2: Frontend seul

- `F5` -> "Frontend Streamlit"
- Lance Streamlit sur 8501
- Frontend: http://localhost:8501

### Option 3: Backend + Frontend ensemble

- `F5` -> "Backend + Frontend (Compound)"
- Lance les deux en parallèle
- Voir 2 terminaux debug

## Tasks (Ctrl+Shift+P -> Tasks: Run Task)

- **Windows: Setup (setup.ps1)**: installation complète (`-Dev` inclus)
- **Windows: Start (setup.ps1)**: backend + frontend dans deux fenêtres (tâche build par défaut : `Ctrl+Shift+B`)
- **Windows: Stop (stop.ps1)**: arrêt des deux services
- **Windows: Tests (test.ps1)**: pytest (tâche test par défaut)
- **Linux/macOS: Setup / Start / Stop / Tests (`.sh`)**: mêmes rôles avec `setup.sh --dev`, `start.sh`, `stop.sh`, `test.sh`
- **Run Backend (venv)**: lance backend sans debug (interpréteur `.venv`)
- **Run Frontend (venv)**: lance frontend sans debug
- **Run Tests (venv)**: pytest
- **Lint Backend (flake8)**

Les tâches « Run … (venv) » fonctionnent sur toutes les plateformes (l'interpréteur `.venv` est résolu
par OS : `.venv\Scripts\python.exe` sous Windows, `.venv/bin/python` sous Linux/macOS).

## Tests

### Via UI

- Onglet Testing (flask icon) à gauche
- Voir tous les tests backend/tests/
- Cliquer ▶️ pour lancer un test
- Debug test avec breakpoint

### Via Terminal

```bash
cd backend
pytest tests/ -v
pytest tests/test_market_analysis.py -v
pytest tests/test_data_quality.py -v -k test_missing
```

### Debug Test

- `F5` -> "Pytest All" ou "Test Data Quality"
- Breakpoint dans test
- Inspect variables

## Développement Workflow

### Ajouter nouvelle fonctionnalité

1. Créer branche: `git checkout -b feature/ma-feature`
2. Backend: ajouter service dans `backend/app/services/`, route dans `backend/app/api/routes/`, test dans `backend/tests/`
3. Frontend: ajouter page dans `frontend/pages/` ou component dans `frontend/components/`
4. Tester: `pytest` + manuel via UI
5. Linter: `black backend/` + `flake8`
6. Commit: `git add . && git commit -m "feat: ma feature"`
7. Push: `git push origin arena/01a09f1d-agent`

### Exemple: Ajouter nouveau KPI

```python
# backend/app/services/market_analysis_engine.py
def calculate_new_kpi(self, prices):
    return ...

# backend/app/api/routes/market_analysis.py
@router.get("/new-kpi")
def new_kpi():
    ...

# backend/tests/test_market_analysis.py
def test_new_kpi():
    ...

# frontend/pages/2_Data_Analysis.py
# Ajouter affichage KPI
```

## Debugging Tips

### Backend

- Logs dans terminal Debug Console
- `logger.info()` dans code -> voir dans console
- Breakpoint dans route API, puis appeler via `curl` ou frontend
- Vérifier `http://localhost:8000/docs` pour tester API manuellement

### Frontend

- Streamlit rerun automatique à chaque save
- `st.write()` pour debug
- `st.json()` pour afficher dict
- Logs dans terminal Streamlit

### Windows (scripts PowerShell)

- `start.ps1` ouvre deux fenêtres PowerShell : les logs y défilent en direct
- Mode `-Background` : logs dans `logs\backend.log` et `logs\frontend.log`
- `.\stop.ps1` pour tout arrêter (aussi disponible en tâche VS Code)

### Linux / macOS

- `./start.sh` : logs dans `logs/backend.log` et `logs/frontend.log` (`tail -f logs/backend.log`)
- `./start.sh --foreground` : garde la main dans le terminal, Ctrl+C arrête les deux services
- `./stop.sh` pour tout arrêter

## Environnement

### .env

- Copier `.env.example` -> `.env`
- VS Code charge automatiquement via `python-dotenv`
- Pour changer, éditer `.env` puis relancer debug

### PYTHONPATH

- Déjà configuré dans `.vscode/settings.json` et `launch.json`
- Si import error: vérifier `PYTHONPATH=backend` dans terminal
- Ou `export PYTHONPATH=$PWD/backend:$PWD`

## Raccourcis Utiles

- `F5`: Lancer debug
- `Shift+F5`: Stop debug
- `Ctrl+Shift+P`: Command palette
- `Ctrl+` ` `: Terminal
- `Ctrl+B`: Toggle sidebar
- `Ctrl+Shift+E`: Explorer
- `Ctrl+Shift+F`: Search
- `Ctrl+Shift+G`: Git
- `Ctrl+Shift+D`: Debug
- `Ctrl+Shift+X`: Extensions

## Git dans VS Code

- Onglet Source Control (Ctrl+Shift+G)
- Voir changements, commit, push
- Branch actuelle: `arena/01a09f1d-agent` (ne pas changer, session Arena)
- Toujours push sur `arena/01a09f1d-agent`

## Problèmes Courants

**Import error `app` not found:**
- Vérifier PYTHONPATH dans `.vscode/settings.json`
- Sélectionner bon interpreter `.venv/bin/python`
- Relancer VS Code

**Port déjà utilisé:**
- `./stop.sh` / `.\stop.ps1`, ou `lsof -i :8000` puis `kill <PID>`
- Ou changer port dans `launch.json`

**Streamlit ne se lance pas:**
- Vérifier `pip install --only-binary :all: -r requirements.txt` (ou relancer `setup.ps1` / `setup.sh`)
- Vérifier port 8501 libre
- Logs dans Debug Console

**Tests non détectés:**
- Vérifier `python.testing.pytestEnabled: true` dans settings.json
- `Python: Configure Tests` -> pytest -> backend/tests

## Productivité

- **Copilot**: Si activé, suggestions code automatiques
- **Jupyter**: Ouvrir `backend/data_samples/*.csv` avec Jupyter pour explorer
- **PowerShell extension**: coloration/analyse des scripts `setup.ps1` / `start.ps1`

## Prochaines Étapes

- Lire `docs/INSTALLATION.md` et `docs/WINDOWS_SETUP.md`
- Lire `docs/USER_GUIDE.md`
- Explorer `backend/app/main.py` et `frontend/app.py`
- Lancer tests et debugger
