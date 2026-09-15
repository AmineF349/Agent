# Installation - Power Market Intelligence Agent

## Prérequis

- Python 3.10 - 3.12, 64 bits (recommandé 3.11). **Optionnel sous Windows :**
  `setup.ps1` le télécharge et l'installe sans droits administrateur.
- Docker + Docker Compose : **facultatif** (le mode natif Windows s'en passe)
- VS Code (recommandé)
- 4GB RAM minimum, 8GB recommandé

> ⚠️ **PostgreSQL n'est pas requis.** Aucun module du backend n'ouvre de
> connexion SQL : la persistance est fichier (`backend/generated/`). Il n'y a
> pas de Redis non plus. Le service `postgres` du `docker-compose.yml` est
> donc décoratif, et le mode natif n'a besoin d'aucun service externe.

---

## 🪟 Option 0 : Windows natif, SANS Docker (recommandé en entreprise)

Deux commandes PowerShell, aucun droit administrateur, aucune règle de pare-feu :

```powershell
.\setup.ps1
.\start.ps1
```

- Interface : <http://127.0.0.1:8501>
- API Swagger : <http://127.0.0.1:8000/docs>
- Arrêt : `.\stop.ps1` — Tests : `.\test.ps1`
- Diagnostic : `.\.venv\Scripts\python.exe scripts\win\doctor.py`

Si la GPO bloque l'exécution de scripts PowerShell, utilisez `.\setup.bat` et
`.\start.bat`, ou `powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1`.

📘 **Guide détaillé, options et dépannage :
[`INSTALLATION_WINDOWS.md`](INSTALLATION_WINDOWS.md)**

---

## Option 1: Docker Compose (1 commande)

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

## Option 2: Local sans Docker, à la main (Linux / macOS / Windows avancé)

> Sous Windows, préférez l'Option 0 (`setup.ps1` / `start.ps1`) : elle fait
> exactement ces étapes en gérant le venv, le `.env`, `PYTHONPATH`, les ports et
> le diagnostic.

Un seul environnement virtuel à la racine suffit pour le backend et le frontend.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r frontend/requirements.txt
cp .env.example .env

# Terminal 1 - backend
cd backend && python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

# Terminal 2 - frontend
cd frontend && python -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1
```

### Windows (PowerShell, sans les scripts)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r frontend\requirements.txt
Copy-Item .env.example .env

# Fenetre 1 - backend (le repertoire de travail DOIT etre backend\)
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

# Fenetre 2 - frontend
cd frontend
..\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1
```

### Vérification

```bash
# Linux / macOS
curl http://127.0.0.1:8000/health
```

```powershell
# Windows
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json
```

Puis ouvrir <http://127.0.0.1:8000/docs> et <http://127.0.0.1:8501>.

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
# Backend health (Linux / macOS)
curl http://127.0.0.1:8000/health

# Doit retourner:
# {"status":"ok","version":"1.0.0","llm_available":false,"public_apis":{...}}

# Tests
cd backend && python -m pytest tests/ -v     # 18 tests
```

```powershell
# Windows
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json
.\test.ps1
.\.venv\Scripts\python.exe scripts\win\doctor.py   # diagnostic complet
```

## Troubleshooting

**Backend ne démarre pas:**
- Vérifier que le port 8000 est libre
  - Linux/macOS : `lsof -i :8000`
  - Windows : `Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -InformationLevel Quiet`
    (`$true` = déjà occupé)
- Vérifier PYTHONPATH / répertoire de travail : le backend doit être lancé
  depuis `backend\` (`$env:PYTHONPATH = "<depot>\backend"`)
- Windows : `.\start.ps1` le fait pour vous ; logs dans `logs\backend.log`
- Docker : `docker-compose logs backend`

**Frontend ne se connecte pas au backend:**
- Vérifier BACKEND_URL dans .env: `BACKEND_URL=http://127.0.0.1:8000` (natif) ou `http://backend:8000` (docker)
- Vérifier CORS_ORIGINS
- Windows : `start.ps1` force `BACKEND_URL` sur l'URL réelle du backend démarré

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
