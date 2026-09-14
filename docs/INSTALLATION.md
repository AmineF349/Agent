# Installation - Power Market Intelligence Agent

## Prérequis

- Python 3.10+ (recommandé 3.11)
- Docker + Docker Compose (optionnel mais recommandé)
- VS Code (recommandé)
- 4GB RAM minimum, 8GB recommandé

## Option 1: Docker Compose (Recommandé - 1 commande)

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

## Option 2: Local sans Docker (Dev)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

pip install -r requirements.txt

# Copier env
cp ../.env.example ../.env

# Lancer
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

# Vérifier
curl http://localhost:8000/health
# Ouvrir docs
open http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Lancer (dans autre terminal)
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# Ouvrir
open http://localhost:8501
```

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

# Doit passer 15+ tests
```

## Troubleshooting

**Backend ne démarre pas:**
- Vérifier port 8000 libre: `lsof -i :8000`
- Vérifier PYTHONPATH: `export PYTHONPATH=backend`
- Logs: `docker-compose logs backend`

**Frontend ne se connecte pas au backend:**
- Vérifier BACKEND_URL dans .env: `BACKEND_URL=http://localhost:8000` (local) ou `http://backend:8000` (docker)
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
├── docker-compose.yml
└── .env.example
```

## Prochaines Étapes

1. Lire `docs/VSCODE_GUIDE.md` pour dev dans VS Code
2. Lire `docs/USER_GUIDE.md` pour utilisation
3. Lire `ARCHITECTURE.md` pour architecture
4. Explorer `http://localhost:8000/docs` pour API
5. Tester avec `backend/data_samples/sample_prices.csv`

## Support

- README.md pour overview
- ROADMAP.md pour évolutions
- Ouvrir issue GitHub
