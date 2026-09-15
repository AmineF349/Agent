# Installation - Power Market Intelligence Agent

## Prérequis

- Python 3.10, 3.11 ou 3.12 – 64 bits (recommandé 3.11). Python 3.13+ non supporté.
- Docker + Docker Compose (**optionnel** – inutile sous Windows, voir Option 0)
- VS Code (recommandé)
- 4GB RAM minimum, 8GB recommandé
- Aucune base de données ni service externe : le projet n'utilise ni PostgreSQL, ni Redis
  (le service `postgres` de `docker-compose.yml` est optionnel et n'est pas utilisé par le code).

## Option 0: Windows natif – sans Docker, sans droits admin (Recommandé sur poste d'entreprise)

```powershell
git clone https://github.com/AmineF349/Agent.git
cd Agent
.\setup.ps1     # détecte/installe Python 3.11 (sans admin), crée .venv, installe les dépendances, crée .env
.\start.ps1     # backend :8000 + frontend :8501, ouvre le navigateur
.\stop.ps1      # arrêt
.\test.ps1      # pytest
```

Si PowerShell bloque les scripts : `powershell -ExecutionPolicy Bypass -File .\setup.ps1`
ou double-clic sur `setup.cmd` / `start.cmd`.

Guide complet (options, proxy d'entreprise, Python absent, dépannage) : [WINDOWS_SETUP.md](WINDOWS_SETUP.md).

## Option 1: Docker Compose (Linux / macOS / Windows non restreint)

```bash
# Cloner repo
git clone <repo_url>
cd Agent

# Copier env
cp .env.example .env
# Editer .env si besoin (optionnel - fonctionne sans clé)

# Lancer
docker-compose up --build

# Accès:
# Backend API: http://localhost:8000/docs
# Frontend: http://localhost:8501
# Postgres: localhost:5432 (power_user/power_pass)
```

C'est tout! Tout est fonctionnel.

## Option 2: Local sans Docker, manuel (Dev – Linux / macOS / Windows)

Un seul environnement virtuel à la racine pour le backend et le frontend
(`requirements-windows.txt` regroupe les deux et ne contient que des wheels précompilées ;
il fonctionne aussi sous Linux/macOS).

```bash
git clone https://github.com/AmineF349/Agent.git
cd Agent
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell : .\.venv\Scripts\Activate.ps1
pip install -r requirements-windows.txt
cp .env.example .env               # Windows : Copy-Item .env.example .env
```

### Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

# Vérifier
curl http://localhost:8000/health
# Docs : http://localhost:8000/docs
```

Le backend charge automatiquement le `.env` de la racine du dépôt et résout ses chemins
(`knowledge_base/`, `backend/generated/`) de façon absolue : il peut être lancé depuis
n'importe quel répertoire (`uvicorn app.main:app` depuis `backend/`, ou
`PYTHONPATH=backend uvicorn app.main:app` depuis la racine).

### Frontend

```bash
cd frontend
BACKEND_URL=http://localhost:8000 streamlit run app.py --server.port 8501 --server.address 127.0.0.1
# Windows PowerShell : $env:BACKEND_URL = "http://localhost:8000"; streamlit run app.py --server.port 8501
# Ouvrir http://localhost:8501
```

> Les `requirements.txt` séparés de `backend/` et `frontend/` restent utilisés par les Dockerfiles.

### Variables d'environnement

Voir `.env.example`:

- **Sans clé**: fonctionne 100% avec fallback local + APIs publiques gratuites
- **Avec LLM** (optionnel, pour réponses plus riches):
  - `OPENAI_API_KEY=sk-...` (https://platform.openai.com/api-keys)
  - Ou `ANTHROPIC_API_KEY=sk-ant-...` (https://console.anthropic.com/settings/keys)
  - Ou Azure OpenAI

- **ENTSO-E** (optionnel, gratuit):
  - Créer compte https://transparency.entsoe.eu/
  - Générer token
  - `ENTSOE_API_KEY=...`

## Option 3: VS Code Dev Container (Avancé)

1. Installer extension "Dev Containers"
2. Ouvrir repo dans VS Code
3. `F1` -> "Dev Containers: Reopen in Container"
4. Tout est installé automatiquement

## APIs Publiques Gratuites Utilisées

- **Energy-Charts.info**: https://api.energy-charts.info - Prix day-ahead EU, sans clé, 100% gratuit (Fraunhofer ISE)
- **Open-Meteo**: https://open-meteo.com/ - Météo, vent, solaire, sans clé, 100% gratuit
- **ENTSO-E**: https://transparency.entsoe.eu/ - Optionnel, clé gratuite après inscription

## Vérification Installation

```bash
# Backend health
curl http://localhost:8000/health

# Doit retourner:
# {"status":"ok","version":"1.0.0","llm_available":false,"public_apis":{"energy_charts":true,"open_meteo":true}}

# Frontend
curl http://localhost:8501

# Tests
cd backend
pytest tests/ -v

# Doit passer 30 tests (Windows : .\test.ps1)
```

## Troubleshooting

**Windows (proxy, ExecutionPolicy, Python absent, ports occupés) :** voir [WINDOWS_SETUP.md – Dépannage](WINDOWS_SETUP.md#6-dépannage).

**Backend ne démarre pas:**
- Vérifier port 8000 libre: `lsof -i :8000` (Linux/macOS) / `Get-NetTCPConnection -LocalPort 8000` (Windows) / `.\stop.ps1`
- Vérifier PYTHONPATH: `export PYTHONPATH=backend` (ou lancer depuis `backend/`)
- Logs: fenêtre backend, `logs\backend.log` (mode `-Background`), ou `docker-compose logs backend`

**Frontend ne se connecte pas au backend:**
- Vérifier la variable d'environnement `BACKEND_URL` : `http://localhost:8000` (local, positionnée par `start.ps1`) ou `http://backend:8000` (docker)
- Derrière un proxy d'entreprise : `NO_PROXY=localhost,127.0.0.1` (positionnée par `start.ps1`)
- Vérifier CORS_ORIGINS

**APIs publiques down:**
- Normal, fallback mock automatique, 100% fonctionnel
- Vérifier https://api.energy-charts.info/price?bzn=FR&year=2024 dans navigateur

**LLM non disponible:**
- Normal si pas de clé, fallback local activé, 100% fonctionnel
- Pour activer, ajouter clé dans .env

## Structure Projet

```
.
├── backend/
│   ├── app/
│   │   ├── main.py (FastAPI)
│   │   ├── core/ (config, logging)
│   │   ├── api/routes/ (6 modules)
│   │   ├── services/ (logique métier)
│   │   ├── data/connectors/ (Energy-Charts, Open-Meteo, ENTSO-E, Mock)
│   │   └── agent/ (LLM provider, LangGraph)
│   ├── tests/
│   └── data_samples/
├── frontend/
│   ├── app.py (Streamlit main)
│   ├── pages/ (6 pages)
│   └── components/
├── knowledge_base/
│   ├── concepts/ (capture_rate, baseload, BESS...)
│   └── models/ (AFRY, Aurora)
├── docs/
├── setup.ps1 / start.ps1 / stop.ps1 / test.ps1 (Windows natif)
├── requirements-windows.txt
├── docker-compose.yml (optionnel)
└── .env.example
```

## Prochaines Étapes

1. Lire `docs/WINDOWS_SETUP.md` (Windows) et `docs/VSCODE_GUIDE.md` pour dev dans VS Code
2. Lire `docs/USER_GUIDE.md` pour utilisation
3. Lire `ARCHITECTURE.md` pour architecture
4. Explorer `http://localhost:8000/docs` pour API
5. Tester avec `backend/data_samples/sample_prices.csv`

## Support

- README.md pour overview
- ROADMAP.md pour évolutions
- Ouvrir issue GitHub
