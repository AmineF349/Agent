# ⚡ Power Market Intelligence Agent

**Copilote IA quotidien des analystes marchés électriques européens - TotalEnergies-grade SaaS**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red.svg)](https://streamlit.io/)
[![Windows natif](https://img.shields.io/badge/Windows-natif%20sans%20Docker-0078D6.svg)](docs/INSTALLATION_WINDOWS.md)
[![Docker](https://img.shields.io/badge/Docker-Compose%20(option)-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 Vision Produit

Devenir le **copilote quotidien** des analystes travaillant sur:

- **Prix de marché** (spot, forward, PPA)
- **Scénarios long terme** (AFRY BID3, Aurora, internes)
- **Renouvelables** (solaire, éolien, capture rates, cannibalisation)
- **Heures négatives**, **BESS**, **nucléaire**, **interconnexions**
- **Expansion capacités**, **modélisation**, **prévisions offre/demande**

Aider à:
- ✅ Analyser des données (qualité, KPI)
- ✅ Challenger des hypothèses (AFRY/Aurora)
- ✅ Automatiser les calculs (capture rate, BESS revenue)
- ✅ Produire des présentations (PPTX/COMEX/AFRY)
- ✅ Préparer des réunions (agenda, Q&A, CR)
- ✅ Générer des rapports + contrôles qualité

**Niveau exigence**: SaaS professionnel pour utility européenne (TotalEnergies, EDF, Engie), utilisé par analystes, traders, stratégie, modélisation, management.

---

## 🚀 Quick Start

### ✅ Windows — natif, SANS Docker (recommandé en entreprise)

Aucun droit administrateur, aucune invite du pare-feu, rien d'installé hors du
dossier du dépôt.

```powershell
git clone <repo_url>
cd Agent
.\setup.ps1
.\start.ps1
```

Puis ouvrir :

- Interface : http://127.0.0.1:8501
- API Swagger : http://127.0.0.1:8000/docs
- Health : http://127.0.0.1:8000/health

Arrêt : `.\stop.ps1` — Tests : `.\test.ps1`

> PowerShell bloque les scripts (`ExecutionPolicy Restricted`) ? Utilisez
> `.\setup.bat` / `.\start.bat`, ou
> `powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1`.
>
> Python absent de la machine ? `setup.ps1` télécharge la distribution
> officielle python.org **sans installation** et la dézippe dans `.python\`
> (aucune élévation UAC).

📘 Guide complet : **[`docs/INSTALLATION_WINDOWS.md`](docs/INSTALLATION_WINDOWS.md)**

### 🐳 Docker Compose (optionnel)

```bash
git clone <repo_url>
cd Agent
cp .env.example .env   # Optionnel, fonctionne sans clé
docker-compose up --build
```

**Accès:**
- Frontend: http://localhost:8501
- Backend API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

**Dans les deux cas : 100% fonctionnel sans aucune clé API.**

> ℹ️ Le service `postgres` du compose est **inutile au fonctionnement** : aucun
> module du backend n'ouvre de connexion SQL (la persistance est fichier, dans
> `backend/generated/`). C'est ce qui rend le mode natif Windows possible sans
> aucun service externe. Il n'y a pas de Redis dans le projet.

---

## 📦 Modules (6)

### 1️⃣ Data Quality Checker

Vérifie:
- Unités (EUR/MWh, MW, GW...)
- Valeurs manquantes (%)
- Anomalies (IQR, Z-score)
- Incohérences (prix négatif + faible RES)
- Gaps temporels, duplicates

Score qualité /100 + suggestions correction.

### 2️⃣ Market Analysis Engine

Calcule:
- **Baseload**, **Peakload**, **Offpeak**, **Min/Max**, **P10/P50/P90**, **Volatility**
- **Negative Hours** (count + %)
- **Capture Price** = Σ(prix*gen)/Σ(gen)
- **Capture Rate** = Capture Price / Baseload
- **Market Value Factor** (synonyme capture rate)
- **Cannibalisation Factor** = 1 - capture_rate
- **BESS Revenue** (arbitrage perfect foresight)

Insights proactifs + warnings.

### 3️⃣ Scenario Challenger

Challenge:
- **AFRY BID3**, **Aurora**, **Scénarios internes**

Détecte:
- Hypothèses inhabituelles (gas 100€ vs 20-60€ range)
- Écarts historiques (demande FR 400 TWh vs 475 TWh 2024)
- Incohérences économiques (gas haut + CO2 haut mais élec bas)

Score /100 + peer comparison AFRY/Aurora + risques & opportunités business.

### 4️⃣ Meeting Copilot

Prépare:
- **Agenda** détaillé avec time slots + owners
- **Questions challenge** (8 percutantes)
- **Checklist** préparation
- **Risques** à soulever
- **Data** à préparer
- **Executive summary**

Génère **compte rendu** à partir notes brutes: summary, décisions, actions (owner/deadline), questions ouvertes, next steps, CR formaté markdown.

Types: AFRY Review (90min), Aurora Review (60min), COMEX (45min), Trading (30min)...

### 5️⃣ PowerPoint Generator

Crée:
- **PPTX** slides management, COMEX, AFRY support, market update
- **DOCX** note exécutive 2-3 pages
- **PDF** export

Templates pro TotalEnergies-grade (colors, layouts), TOC, conclusion, notes insights.

### 6️⃣ Knowledge Base

Base connaissances:
- **Concepts marché**: capture rate, baseload/peakload, negative hours, BESS, interco
- **Modèles**: AFRY BID3, Aurora, hypothèses
- **FAQ**

Recherche keyword + TF-IDF + synthèse via LLM (si clé) ou template expert (fallback). Related questions.

---

## 🏗️ Architecture

```
Frontend (Streamlit) ──HTTP──> Backend (FastAPI)
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
                Services      Agent (LangGraph)  Data Connectors
                (6 modules)   LLM Provider       Energy-Charts (free)
                              Prompts            Open-Meteo (free)
                                                 ENTSO-E (optional)
                                                 Mock (fallback)
                    │
              ┌─────┼─────┐
              ▼     ▼     ▼
           Postgres SQLite Files
```

**Stack**:
- Backend: Python 3.11, FastAPI, Pandas/Polars, Plotly, LangChain/LangGraph, python-pptx/docx, reportlab
- Frontend: Streamlit, Plotly, requests
- Data: Energy-Charts.info (gratuit, sans clé), Open-Meteo (gratuit, sans clé), ENTSO-E (optionnel, clé gratuite), Mock fallback
- IA: OpenAI/Claude/Azure OpenAI (optionnel) + Fallback local templates experts (100% fonctionnel sans clé)
- Infra: **Windows natif sans Docker (setup.ps1/start.ps1)** ou Docker Compose, persistance fichier, VS Code config

Voir `ARCHITECTURE.md` pour détails.

---

## 🔑 APIs Publiques Gratuites (sans clé)

| API | URL | Auth | Data |
|-----|-----|------|------|
| **Energy-Charts** | https://api.energy-charts.info | None, 100% public | Day-ahead prices, generation, installed power (Fraunhofer ISE) |
| **Open-Meteo** | https://open-meteo.com/ | None, 100% public | Weather forecast, historical, solar radiation, wind speed |
| **ENTSO-E** (optionnel) | https://transparency.entsoe.eu/ | Free key après inscription | Prices, generation, load, cross-border flows |

**Fallback**: Mock generator avec données réalistes si APIs down -> toujours fonctionnel.

---

## 🤖 LLM - Fonctionne sans clé

**Provider abstraction** dans `backend/app/agent/llm_provider.py`:

- Si `OPENAI_API_KEY` présent -> OpenAI gpt-4o-mini
- Si `ANTHROPIC_API_KEY` présent -> Claude 3.5 Sonnet
- Si `AZURE_OPENAI_API_KEY` présent -> Azure OpenAI
- Sinon -> **Fallback local** avec templates experts marché électrique (100% fonctionnel, ton senior, chiffré)

**Coût**: gpt-4o-mini ~0.15$/1M tokens input, 0.6$/1M output -> <10$/mois pour analyste (100 req/jour).

**Pour activer LLM** (optionnel, plus riche rédactionnel):
```bash
# Dans .env
OPENAI_API_KEY=sk-...
# ou
ANTHROPIC_API_KEY=sk-ant-...
```

Sinon, tout marche en mode fallback.

---

## 📁 Arborescence

```
.
├── backend/
│   ├── app/
│   │   ├── main.py (FastAPI)
│   │   ├── core/ (config, logging)
│   │   ├── api/routes/ (6 modules + health + market_data)
│   │   ├── services/ (business logic 6 modules)
│   │   ├── data/connectors/ (energy_charts, open_meteo, entsoe, mock)
│   │   ├── data/repositories/ (file_repo)
│   │   ├── models/ (schemas, domain)
│   │   └── agent/ (llm_provider, langgraph_agent, prompts)
│   ├── tests/ (5 fichiers, 15+ tests)
│   ├── data_samples/ (sample_prices.csv, sample_renewable.csv, sample_scenario.json)
│   └── requirements.txt
├── frontend/
│   ├── app.py (main Streamlit)
│   ├── pages/ (Dashboard, Data Analysis, Scenario Review, Presentation Builder, Meeting Assistant, Knowledge Center)
│   ├── components/ (charts, cards, sidebar)
│   ├── utils/ (api_client)
│   └── requirements.txt
├── knowledge_base/
│   ├── concepts/ (capture_rate, baseload_peakload, negative_hours, bess, interconnectors)
│   ├── models/ (afry_bid3, aurora, assumptions)
│   └── faq.md
├── docs/
│   ├── INSTALLATION.md
│   ├── VSCODE_GUIDE.md
│   ├── API_DOCS.md
│   └── USER_GUIDE.md
├── .vscode/
│   ├── settings.json
│   ├── launch.json
│   ├── tasks.json
│   └── extensions.json
├── scripts/
│   └── win/ (Common.ps1, env_writer.py, doctor.py)
├── setup.ps1 / start.ps1 / stop.ps1 / test.ps1   <- Windows natif, sans Docker
├── setup.bat / start.bat / stop.bat / test.bat   <- wrappers ExecutionPolicy
├── docker-compose.yml                            (optionnel)
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example
├── ARCHITECTURE.md
├── ROADMAP.md
└── README.md
```

---

## 🛠️ Installation

### Option 1 : Windows natif, sans Docker (recommandé)

```powershell
.\setup.ps1     # Python + .venv + dépendances + .env + auto-diagnostic
.\start.ps1     # backend :8000 + frontend :8501, navigateur ouvert
.\stop.ps1      # arrêt propre
.\test.ps1      # 18 tests pytest
```

Options utiles : `-Proxy`, `-IndexUrl` (miroir PyPI interne), `-WithDev`,
`-Recreate`, `-BackendPort`, `-FrontendPort`, `-ListenHost 0.0.0.0`,
`-NoNewWindow`, `-Reload`.

Voir **[`docs/INSTALLATION_WINDOWS.md`](docs/INSTALLATION_WINDOWS.md)**.

### Option 2 : Docker Compose

```bash
cp .env.example .env
docker-compose up --build
# Frontend http://localhost:8501, Backend http://localhost:8000/docs
```

### Option 3 : Local manuel (Linux / macOS / Windows avancé)

```bash
# Backend
cd backend
python -m venv ../.venv
../.venv/bin/python -m pip install -r requirements.txt
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

# Frontend (autre terminal)
cd frontend
../.venv/bin/python -m pip install -r requirements.txt
../.venv/bin/python -m streamlit run app.py --server.port 8501
```

> Sous Windows remplacez `../.venv/bin/python` par `..\.venv\Scripts\python.exe`.

Voir `docs/INSTALLATION.md` pour détails + troubleshooting.

---

## 💻 VS Code

1. Ouvrir dossier `Agent` dans VS Code
2. Installer extensions recommandées (popup)
3. `F5` -> Choisir "Backend FastAPI" ou "Frontend Streamlit" ou "Backend + Frontend (Compound)"
4. Breakpoints, debug, tests via UI Testing

Voir `docs/VSCODE_GUIDE.md` pour guide complet (settings, launch, tasks, extensions, workflow).

---

## 🧪 Tests

```powershell
# Windows (sans Docker)
.\test.ps1
```

```bash
# Linux / macOS
cd backend && python -m pytest tests/ -v
# 18 tests: data_quality, market_analysis, scenario, meeting, presentation
```

Via VS Code: Onglet Testing -> ▶️

---

## 📚 Documentation

- `README.md` (ce fichier) - Overview
- `ARCHITECTURE.md` - Architecture détaillée + diagramme + choix techniques
- `ROADMAP.md` - Roadmap v1.1, v1.2, v2.0...
- `docs/INSTALLATION_WINDOWS.md` - **Installation Windows native sans Docker** (entreprise restreinte)
- `docs/INSTALLATION.md` - Installation Docker/local + troubleshooting
- `docs/VSCODE_GUIDE.md` - Guide VS Code dev
- `docs/API_DOCS.md` - API endpoints + exemples curl
- `docs/USER_GUIDE.md` - Guide utilisateur analyste sans dev
- `knowledge_base/` - Concepts marché + modèles + FAQ
- `http://localhost:8000/docs` - API interactive Swagger

---

## 🎯 Exemples Usage

### Valorisation PPA Solaire 100MW FR

1. Data Analysis -> Market Analysis -> Mock FR 30j + solar
2. Baseload 65€, capture rate 0.78, capture price 50.7€
3. PPA = 65*0.78*0.9 (discount) = 45.6€/MWh
4. Si capture rate 0.65 en 2030, PPA 38€ -> perte 18M€ sur 20 ans!
5. Scenario Review -> challenger capture rate 0.78 vs 0.65 Aurora
6. Presentation Builder -> slides COMEX
7. Meeting Assistant -> préparer COMEX

### Business Case BESS 10MW/2h FR

1. Dashboard -> spread peak/offpeak 28€, 150h négatives
2. Data Analysis -> BESS Revenue -> 10MW/2h -> 220k€/MW/an
3. Knowledge Center -> "BESS revenue stacking" -> total 300k€/MW/an avec FCR/aFRR
4. Scenario Review -> BESS 5GW FR 2030 réaliste?
5. Presentation Builder -> slides BESS opportunity

### Préparer COMEX AFRY vs Aurora

1. Scenario Review -> sample_scenario.json AFRY Central 2030 FR
2. Challenger -> score 85/100, warnings gas 38€ vs forward 32€
3. Benchmarks + AFRY vs Aurora comparatif
4. Meeting Assistant -> COMEX 45min "AFRY vs Aurora - arbitrage"
5. Presentation Builder -> 5 slides COMEX + DOCX note

Voir `docs/USER_GUIDE.md` pour workflows détaillés.

---

## 🤝 Contribution

1. Fork, puis branchez une branche `feature/ma-feature` sur la branche de travail en cours
2. Code + tests + docs
3. `black backend/` + `flake8` + `pytest`
4. Commit + push sur votre branche
5. PR

---

## 📝 License

MIT

---

## 🙏 Remerciements

- Fraunhofer ISE Energy-Charts.info pour API publique gratuite
- Open-Meteo pour API météo gratuite
- ENTSO-E pour transparence
- AFRY, Aurora pour modèles marché (inspiration)
- TotalEnergies, EDF, Engie pour use cases utility

---

## 📞 Support

- Ouvrir issue GitHub
- Lire docs/
- Contacter équipe modélisation

---

**Made with ❤️ for analystes marchés électriques européens - TotalEnergies-grade SaaS**

**Version**: 1.0.0 | **Date**: Sept 2024 | **Status**: Production-ready MVP, 100% fonctionnel sans clé API
