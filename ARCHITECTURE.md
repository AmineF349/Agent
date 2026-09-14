# Architecture - Power Market Intelligence Agent

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Streamlit)                      │
│  Dashboard | Data Analysis | Scenario Review | Presentation      │
│  Meeting Assistant | Knowledge Center | Agent Chat               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP REST
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ API Routes (6 modules)                                    │   │
│  │ /data-quality | /market-analysis | /scenario | /meeting  │   │
│  │ /presentation | /knowledge | /market-data | /agent       │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │ Services (Business Logic)                                 │   │
│  │ DataQualityChecker | MarketAnalysisEngine | ScenarioChallenger│
│  │ MeetingCopilot | PresentationGenerator | KnowledgeBase    │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │ Agent Layer (LangGraph + LLM Provider)                    │   │
│  │ PowerMarketAgent (routing) | LLMProvider (OpenAI/Claude/Azure/Local)│
│  │ Prompts Templates                                         │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │ Data Layer (Connectors + Repositories)                    │   │
│  │ EnergyCharts (free) | OpenMeteo (free) | ENTSO-E (optional)│
│  │ MockGenerator (fallback) | FileRepository                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Postgres │ │  SQLite  │ │  Files   │
        │ (Docker) │ │ (local)  │ │ generated│
        └──────────┘ └──────────┘ └──────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │Energy-   │ │Open-Meteo│ │ ENTSO-E  │
        │Charts API│ │   API    │ │   API    │
        │ (free)   │ │  (free)  │ │(optional)│
        └──────────┘ └──────────┘ └──────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ OpenAI   │ │ Anthropic│ │  Azure   │
        │ (optional)│ │(optional)│ │(optional)│
        └──────────┘ └──────────┘ └──────────┘
```

## Stack Technique

### Backend

- **Framework**: FastAPI 0.110 (Python 3.11)
- **Data**: Pandas 2.2, Polars 0.20, Numpy 1.26, Scipy 1.12
- **IA**: LangChain 0.1, LangGraph 0.0, OpenAI 1.30, Anthropic 0.28, tiktoken
- **Visu**: Plotly 5.19, Matplotlib 3.8
- **Presentation**: python-pptx 0.6, python-docx 1.1, reportlab 4.1
- **Connectors**: requests, httpx, entsoe-py 0.6
- **DB**: SQLAlchemy 2.0, psycopg2, alembic
- **Utils**: tenacity, structlog, orjson, aiofiles

### Frontend

- **Framework**: Streamlit 1.35
- **Visu**: Plotly 5.19, Pandas 2.2
- **HTTP**: requests, httpx
- **UI**: streamlit-option-menu, streamlit-extras

### Infra

- **Docker**: Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
- **DB**: Postgres 15 (Docker) ou SQLite (local)
- **IDE**: VS Code avec settings, launch, tasks, extensions

## Modules Détail

### Module 1: Data Quality Checker

**Responsabilité**: Vérifier qualité données marché

**Classes**:
- `DataQualityChecker` dans `backend/app/services/data_quality_checker.py`

**Fonctions**:
- `check_dataframe(df, data_type)` -> DataQualityReport
- `check_prices(prices)` -> DataQualityReport
- `suggest_fixes(report)` -> List[str]

**Logique**:
- Missing values (% par colonne)
- Anomalies: IQR (1.5*IQR) + Z-score (|z|>4)
- Realistic ranges: price (-500,3000), gas (5,350), CO2 (0,300)
- Temporal: duplicates, gaps (median diff *1.5)
- Cross-column: negative price + low renewable = suspicious
- Quality score: 100 - penalty (critical 15, high 8, medium 3, low 1)

**API**: `/api/v1/data-quality/check` (upload CSV/Excel), `/check-prices`

**Frontend**: `pages/2_Data_Analysis.py` tab Data Quality

### Module 2: Market Analysis Engine

**Responsabilité**: Calculer KPI marché

**Classes**:
- `MarketAnalysisEngine` dans `backend/app/services/market_analysis_engine.py`

**Fonctions**:
- `calculate_metrics(prices, generation, timestamps, country, technology)` -> MarketMetrics
- `_calculate_peak_offpeak(prices, timestamps)` -> (peak, offpeak)
- `analyze(...)` -> MarketAnalysisResponse (metrics + insights + warnings + chart_data)
- `calculate_bess_revenue(prices, capacity_mw, duration_h, efficiency)` -> Dict

**KPI**:
- Baseload: mean(prices)
- Peakload: mean(Mon-Fri 8-20h) ou proxy 8-20h
- Offpeak: mean(rest)
- Negative hours: sum(price<0)
- Capture Price: sum(price*gen)/sum(gen)
- Capture Rate: capture_price / baseload
- MVF: same as capture rate
- Cannibalisation: 1 - capture_rate
- P10/P50/P90, volatility, min/max, std

**Insights proactifs**:
- Baseload >100 = crise gaz/CO2
- Negative hours >5% = cannibalisation sévère, opportunité BESS
- Capture rate <0.7 = forte cannibalisation
- Volatility >0.8 = marché instable
- Spread peak/offpeak >30 = BESS opportunity

**API**: `/api/v1/market-analysis/analyze`, `/bess-revenue`, `/kpi-definitions`

**Frontend**: `pages/2_Data_Analysis.py` tab Market Analysis + BESS

### Module 3: Scenario Challenger

**Responsabilité**: Challenger scénarios AFRY/Aurora/Interne

**Classes**:
- `ScenarioChallenger` dans `backend/app/services/scenario_challenger.py`

**Fonctions**:
- `challenge(scenario: ScenarioInput)` -> ScenarioChallengerResponse
- `_check_gas_price`, `_check_co2_price`, `_check_demand`, `_check_res_capacity`, `_check_nuclear`, `_check_capture_rate`, `_check_negative_hours`, `_check_economic_consistency`, `_check_afry_specific`, `_check_aurora_specific`
- `_calculate_score(issues)` -> 0-100
- `_peer_comparison(...)` -> Dict
- `_generate_risks_opportunities(...)` -> List[str]

**Benchmarks**:
- `BENCHMARKS` dans `domain.py`: FR/DE baseload, gas, CO2, demand_growth, solar_cf, wind_cf, nuclear_availability
- `AFRY_RANGES`, `AURORA_RANGES`

**Issues**:
- unusual_hypothesis: valeur hors range réaliste
- historical_deviation: vs historique
- economic_inconsistency: gas haut + CO2 haut mais élec bas = incohérent
- model_specific: AFRY/Aurora specific

**Score**: 100 - penalty (critical 20, warning 8, info 2)

**API**: `/api/v1/scenario/challenge`, `/benchmarks/{country}`, `/afry-vs-aurora`

**Frontend**: `pages/3_Scenario_Review.py`

### Module 4: Meeting Copilot

**Responsabilité**: Préparer réunions, générer CR

**Classes**:
- `MeetingCopilot` dans `backend/app/services/meeting_copilot.py`

**Fonctions**:
- `prepare_meeting(request: MeetingRequest)` -> MeetingResponse
- `_generate_agenda_template`, `_generate_agenda_llm`
- `_generate_questions_template`, `_generate_questions_llm`
- `_generate_checklist_template`, `_generate_checklist_llm`
- `_generate_summary_template`, `_generate_summary_llm`
- `_generate_risks`, `_generate_data_needs`
- `generate_minutes(request: MinutesRequest)` -> MinutesResponse
- `_generate_minutes_template`, `_generate_minutes_llm`

**Templates**:
- `MEETING_TEMPLATES`: AFRY Review (90min), Aurora Review (60min), COMEX (45min), Trading (30min)

**LLM**: Utilise LLMProvider si disponible, sinon templates

**API**: `/api/v1/meeting/prepare`, `/minutes`, `/templates`

**Frontend**: `pages/5_Meeting_Assistant.py`

### Module 5: Presentation Generator

**Responsabilité**: Générer PPTX/DOCX/PDF

**Classes**:
- `PresentationGenerator` dans `backend/app/services/presentation_generator.py`

**Fonctions**:
- `generate(request: PresentationRequest)` -> PresentationResponse
- `_generate_pptx(request, output_path)`
- `_add_title_slide`, `_add_toc_slide`, `_add_content_slide`, `_add_chart_slide`, `_add_conclusion_slide`
- `_generate_docx(request, output_path)`
- `_generate_pdf(request, output_path)`

**Libs**:
- python-pptx pour PPTX
- python-docx pour DOCX
- reportlab pour PDF

**Templates**:
- COLORS: primary #003366, secondary #0099CC, accent #FF6600
- Layouts: title, toc, content, conclusion
- Types: Management, COMEX, AFRY Support, Executive Note, Market Update

**API**: `/api/v1/presentation/generate`, `/download/{filename}`, `/types`

**Frontend**: `pages/4_Presentation_Builder.py`

### Module 6: Knowledge Base

**Responsabilité**: Base connaissances marché

**Classes**:
- `KnowledgeBaseService` dans `backend/app/services/knowledge_base.py`

**Fonctions**:
- `_load_documents()` -> charge .md de knowledge_base/
- `_builtin_knowledge()` -> fallback si pas de fichiers
- `search(query, category, top_k)` -> KnowledgeResponse
- `_synthesize_answer(query, results)` -> str (via LLM si dispo, sinon template)
- `_generate_related_questions(query, results)` -> List[str]
- `list_categories()`, `list_documents()`

**Recherche**:
- Simple TF-IDF + keyword matching (pas de vector DB pour rester léger)
- Score: title match weight 3, content match weight 1, exact phrase bonus 5, tag bonus 2
- Pas de dépendance lourde, 100% fonctionnel sans clé

**Docs**:
- `knowledge_base/concepts/`: capture_rate, baseload_peakload, negative_hours, bess, interconnectors
- `knowledge_base/models/`: afry_bid3, aurora, assumptions
- `knowledge_base/faq.md`

**API**: `/api/v1/knowledge/search`, `/categories`, `/documents`, `/concept/{name}`

**Frontend**: `pages/6_Knowledge_Center.py`

## Data Layer

### Connectors

**EnergyChartsConnector** (`energy_charts.py`):
- Public, free, no key: https://api.energy-charts.info
- `get_day_ahead_prices(country, year)` -> List[Dict]
- `get_renewable_generation(country)` -> Dict
- `get_spot_prices_last_days(country, days)` -> List[Dict]
- Fallback mock si API down

**OpenMeteoConnector** (`open_meteo.py`):
- Public, free, no key: https://open-meteo.com/
- `get_weather_forecast(country, days)` -> Dict
- `get_historical_weather(country, start_date, end_date)` -> Dict (solar_cf_proxy, wind_cf_proxy)
- Country coords mapping (FR Paris, DE Berlin...)

**EntsoeConnector** (`entsoe_connector.py`):
- Optional, free key required: https://transparency.entsoe.eu/
- `get_day_ahead_prices(country, start_date, end_date)` -> List[Dict]
- `get_generation(country)` -> Dict
- Fallback mock si pas de clé

**MockDataGenerator** (`mock_generator.py`):
- `generate_prices(country, days, base_price)` -> List[Dict] (realistic daily/weekly/seasonal patterns + 3% negative prices + 1% spikes)
- `generate_renewable_profile(technology, days, capacity_mw)` -> List[Dict] (solar daylight curve, wind random)
- `generate_load(country, days)` -> List[Dict]
- `generate_scenario(model_type, country, year)` -> Dict

### Repositories

**FileRepository** (`file_repo.py`):
- `save_json(data, filename)` -> path
- `load_json(filename)` -> Dict
- `list_files()` -> List[str]

## Agent Layer

### LLMProvider

**Fichier**: `backend/app/agent/llm_provider.py`

**Détection**:
- OpenAI si OPENAI_API_KEY
- Anthropic si ANTHROPIC_API_KEY
- Azure si AZURE_OPENAI_API_KEY + ENDPOINT
- Sinon local_fallback

**Méthodes**:
- `is_available()` -> toujours True (fallback)
- `has_real_llm()` -> True si OpenAI/Anthropic/Azure
- `generate(prompt, max_tokens, temperature, system)` -> str
- `_generate_openai`, `_generate_anthropic`, `_generate_azure`, `_generate_fallback`

**Fallback**:
- Templates experts basés sur keywords (meeting, capture rate, afry, bess, price...)
- 100% fonctionnel sans clé, ton senior, chiffré

### PowerMarketAgent

**Fichier**: `backend/app/agent/langgraph_agent.py`

**State**: `AgentState` (TypedDict): query, intent, context, results, messages, next_action

**Méthodes**:
- `_build_graph()` -> StateGraph si LangGraph disponible
- `_detect_intent(state)` -> keyword detection (data_quality, market_analysis, scenario, meeting, market_data, knowledge)
- `_route_intent(state)` -> intent string
- `_handle_data_quality`, `_handle_market_analysis`, `_handle_scenario`, `_handle_knowledge`, `_handle_market_data`, `_synthesize`
- `run(query, context)` -> Dict (query, intent, results, messages, mode)
- `proactive_suggestions(last_analysis)` -> List[str]

**Graph**:
- Nodes: intent_detection -> (data_quality|market_analysis|scenario_challenge|knowledge_search|market_data_fetch) -> synthesis -> END
- Fallback simple routing si LangGraph non disponible

### Prompts

**Fichier**: `backend/app/agent/prompts/templates.py`

- `SYSTEM_PROMPT`: expert marché EU, proactive, fact-based, senior
- `MARKET_ANALYSIS_PROMPT`, `SCENARIO_CHALLENGE_PROMPT`, `MEETING_PREP_PROMPT`, `KNOWLEDGE_PROMPT`

## API Layer

**Main**: `backend/app/main.py`

- FastAPI app avec CORS, routers, exception handler, startup/shutdown events
- Routers: health, data_quality, market_analysis, scenario, meeting, presentation, knowledge, market_data
- Agent endpoints: `/api/v1/agent/chat`, `/capabilities`
- Docs: `/docs`, `/redoc`, `/openapi.json`

**Config**: `backend/app/core/config.py`

- `Settings` via pydantic-settings, .env support
- Public APIs URLs, LLM keys, DB URL, CORS, feature flags
- Properties: cors_origins_list, has_llm, has_entsoe

**Logging**: `backend/app/core/logging.py`

- setup_logging() avec level from settings

**Schemas**: `backend/app/models/schemas.py`

- Pydantic models pour tous requests/responses

**Domain**: `backend/app/models/domain.py`

- Enums Country, Technology, BENCHMARKS, AFRY_RANGES, AURORA_RANGES

## Frontend

**Main**: `frontend/app.py`

- Streamlit page config, custom CSS SaaS look
- Sidebar: country, tech, navigation, backend health, tips
- Main: header, top metrics, tabs (Marché Live, Agent Chat, Quick Actions)
- Market Live: fetch live prices via APIClient, plotly chart, metrics
- Agent Chat: chat_input, session_state messages, agent_chat via APIClient, proactive suggestions
- Quick Actions: 6 modules navigation via switch_page

**Pages**:

- `1_Dashboard.py`: KPIs, BESS scanner, AFRY vs Aurora bar chart
- `2_Data_Analysis.py`: tabs Data Quality (upload, check), Market Analysis (mock/live/upload/manual, KPI cards, charts, insights), BESS Revenue
- `3_Scenario_Review.py`: tabs Challenge (form + JSON + sample), Benchmarks, AFRY vs Aurora
- `4_Presentation_Builder.py`: tabs Générateur (form + slides JSON + generate), Fichiers Générés (list + download)
- `5_Meeting_Assistant.py`: tabs Préparer Réunion (form + generate), Générer CR (form + generate)
- `6_Knowledge_Center.py`: tabs Recherche (query + results + synthesized + related), Documents (list), FAQ (markdown)

**Components**:

- `charts.py`: price_timeseries_chart, price_histogram, capture_rate_gauge, scenario_comparison_chart
- `cards.py`: metric_card, insight_card, kpi_row
- `sidebar.py`: render_sidebar()

**Utils**:

- `api_client.py`: APIClient class avec methods health, market_analysis, data_quality_csv, challenge_scenario, prepare_meeting, generate_minutes, generate_presentation, knowledge_search, fetch_market_data, live_prices, agent_chat, bess_revenue

## Docker

**Dockerfile.backend**:
- python:3.11-slim, build-essential, libpq-dev, requirements.txt, app code, generated folder, uvicorn

**Dockerfile.frontend**:
- python:3.11-slim, requirements.txt, app code, streamlit

**docker-compose.yml**:
- postgres:15-alpine, healthcheck, volume postgres_data
- backend: build Dockerfile.backend, port 8000, env_file .env, volumes backend, knowledge_base, generated, depends_on postgres healthy, DATABASE_URL
- frontend: build Dockerfile.frontend, port 8501, env_file .env, volumes frontend, depends_on backend, BACKEND_URL=http://backend:8000
- volumes: postgres_data, backend_generated

## VS Code

**.vscode/settings.json**:
- python.defaultInterpreterPath .venv/bin/python, linting flake8, formatting black, testing pytest backend/tests, PYTHONPATH

**.vscode/launch.json**:
- Backend FastAPI (uvicorn), Frontend Streamlit, Compound, Pytest All, Test Data Quality, Test Market Analysis

**.vscode/tasks.json**:
- Install Backend/Frontend/All, Run Backend/Frontend, Docker Compose Up, Run Tests, Lint Backend

**.vscode/extensions.json**:
- Python, Pylance, Black, Flake8, Docker, YAML, Prettier, Jupyter, Copilot

## Tests

**backend/tests/**:
- test_data_quality.py: basic, missing, anomaly, negative_hours
- test_market_analysis.py: basic, capture_rate, negative_hours, bess, full
- test_scenario.py: basic, unusual_gas, nuclear, capture_rate
- test_meeting.py: prepare, minutes, templates
- test_presentation.py: generator, colors

**Run**: `pytest backend/tests/ -v`

## Data Samples

**backend/data_samples/**:
- sample_prices.csv: 29 rows hourly FR avec 3 negative hours
- sample_renewable.csv: solar + wind_onshore profiles
- sample_scenario.json: AFRY Central 2030 FR avec 10 assumptions

## Knowledge Base

**knowledge_base/concepts/**:
- capture_rate.md, baseload_peakload.md, negative_hours.md, bess.md, interconnectors.md

**knowledge_base/models/**:
- afry_bid3.md, aurora.md, assumptions.md

**knowledge_base/faq.md**

## Diagramme Séquence Exemple

**User -> Frontend -> Backend -> Market Analysis**:

1. User sélectionne Mock FR 30j + solar dans Data Analysis page
2. Frontend appelle MockDataGenerator directement (si import) ou via API
3. Backend MarketAnalysisEngine.calculate_metrics(prices, generation)
4. Calcule baseload, peakload, negative_hours, capture_price, capture_rate...
5. Génère insights proactifs
6. Return MarketAnalysisResponse
7. Frontend affiche KPI cards, gauge, charts, insights

**Agent Chat**:

1. User tape "Analyse capture rate solaire FR" dans Dashboard chat
2. Frontend APIClient.agent_chat(query, country)
3. Backend PowerMarketAgent.run(query, context)
4. _detect_intent -> market_analysis
5. _handle_market_analysis (si prices dans context) ou _handle_knowledge
6. _synthesize via LLMProvider.generate()
7. Return synthesis + proactive_suggestions
8. Frontend affiche réponse + suggestions

## Choix Techniques Justifiés

**FastAPI**:
- Async, performant, docs auto (/docs), pydantic validation, moderne
- vs Flask: plus rapide, typé, docs

**Streamlit**:
- Rapide pour MVP analyste, pas besoin React expertise
- Plotly intégré, facile déploiement
- vs React: plus simple pour analystes sans dev avancé, mais moins customizable (OK pour v1)

**LangGraph**:
- Orchestration agent, routing intent, state management
- vs simple if/else: plus scalable, ajoute mémoire, tools
- Fallback simple routing si non dispo -> robustesse

**LLM Provider abstraction**:
- Support OpenAI, Anthropic, Azure, fallback local
- 100% fonctionnel sans clé -> adoption facile analystes
- Fallback templates experts -> pas bloquant

**Public APIs gratuites**:
- Energy-Charts (Fraunhofer) + Open-Meteo = 100% gratuit, sans clé, fiable
- ENTSO-E optionnel (clé gratuite)
- Mock fallback -> toujours fonctionnel

**Pandas + Polars**:
- Pandas pour compatibilité, Polars pour perf (optionnel)
- Analystes connaissent Pandas

**Plotly**:
- Interactif, beau, Streamlit compatible
- vs Matplotlib: plus moderne

**Docker Compose**:
- 1 commande pour tout lancer, reproducibilité
- Postgres pour prod, SQLite fallback local

**VS Code config**:
- Pour dev local facile, debugging, tests, tasks

## Scalabilité

- **Horizontal**: Backend stateless, peut scaler via k8s, plusieurs replicas
- **DB**: Postgres pour prod, peut passer à TimescaleDB pour time series
- **Cache**: Ajouter Redis pour market data cache (actuellement pas de cache, mais prévu)
- **Queue**: Pour génération présentation longue, ajouter Celery
- **Vector DB**: Pour Knowledge Base RAG avancé, ajouter Qdrant/Chroma (actuellement keyword search simple pour rester léger)

## Sécurité

- Pas d'auth par défaut (local)
- Pour prod: ajouter API key middleware, OAuth2, CORS restrictif
- Secrets via .env, pas commités
- SECRET_KEY pour JWT si besoin

## Monitoring

- Logging via structlog, level INFO
- Health endpoint avec public APIs status
- Pour prod: ajouter Prometheus metrics, Sentry error tracking

## Roadmap Technique

Voir ROADMAP.md pour évolutions: PLEXOS connector, BESS optimizer, PPA pricer, forward curve builder, automated reporting, Teams/Slack bot, vector DB, etc.
