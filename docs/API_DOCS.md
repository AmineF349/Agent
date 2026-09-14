# API Documentation - Power Market Intelligence Agent

Base URL: `http://localhost:8000`

Docs interactives: `http://localhost:8000/docs` (Swagger) et `/redoc`

## Health

- `GET /health` - Health check, version, LLM status, public APIs status
- `GET /` - Root, liste endpoints

## Module 1: Data Quality Checker

- `POST /api/v1/data-quality/check` - Upload CSV/Excel, vérifie qualité
  - Form: file (UploadFile), data_type (price, capacity, energy...)
  - Return: DataQualityReport (score, issues, missing_pct, summary)

- `POST /api/v1/data-quality/check-prices` - Quick check list prix
  - Body: [45, 42, 38, ...]
  - Return: report + suggestions

## Module 2: Market Analysis Engine

- `POST /api/v1/market-analysis/analyze` - Calcule KPI marché
  - Body: MarketAnalysisRequest {prices, generation (optional), timestamps, country, technology}
  - Return: MarketAnalysisResponse {metrics (baseload, peakload, negative_hours, capture_price, capture_rate...), insights, warnings, chart_data}

- `POST /api/v1/market-analysis/bess-revenue` - Estime revenu BESS
  - Query: capacity_mw, duration_h, efficiency
  - Body: prices list
  - Return: {annual_revenue, annual_per_mw, daily...}

- `GET /api/v1/market-analysis/kpi-definitions` - Définitions KPI

## Module 3: Scenario Challenger

- `POST /api/v1/scenario/challenge` - Challenge scénario AFRY/Aurora/Interne
  - Body: ScenarioInput {scenario_name, model_type, country, horizon, assumptions: [{name, value, unit, year}]}
  - Return: ScenarioChallengerResponse {overall_score, issues (unusual_hypothesis, historical_deviation...), summary, peer_comparison, risk_opportunities}

- `GET /api/v1/scenario/benchmarks/{country}` - Benchmarks FR/DE
- `GET /api/v1/scenario/afry-vs-aurora` - Comparatif modèles

## Module 4: Meeting Copilot

- `POST /api/v1/meeting/prepare` - Prépare réunion
  - Body: MeetingRequest {meeting_type, topic, participants, duration_min, context}
  - Return: MeetingResponse {agenda, key_questions, preparation_checklist, risks_to_raise, data_to_prepare, executive_summary}

- `POST /api/v1/meeting/minutes` - Génère CR à partir notes brutes
  - Body: MinutesRequest {meeting_type, raw_notes, participants}
  - Return: MinutesResponse {summary, decisions, actions, open_questions, next_steps, formatted_minutes}

- `GET /api/v1/meeting/templates` - Templates réunions

## Module 5: Presentation Generator

- `POST /api/v1/presentation/generate` - Génère PPTX/DOCX/PDF
  - Body: PresentationRequest {presentation_type, title, subtitle, slides: [{title, bullets, notes, data}], author, country, include_toc}
  - Return: PresentationResponse {pptx_path, docx_path, pdf_path, slide_count}

- `GET /api/v1/presentation/download/{filename}` - Télécharge fichier généré
- `GET /api/v1/presentation/types` - Types présentations

## Module 6: Knowledge Base

- `POST /api/v1/knowledge/search` - Recherche base connaissances
  - Body: KnowledgeQuery {query, category, top_k}
  - Return: KnowledgeResponse {query, results: [{title, content, category, relevance_score, source_path, tags}], synthesized_answer, related_questions}

- `GET /api/v1/knowledge/categories` - Liste catégories
- `GET /api/v1/knowledge/documents` - Liste documents
- `GET /api/v1/knowledge/concept/{concept_name}` - Concept rapide

## Market Data (Public APIs)

- `POST /api/v1/market-data/fetch` - Fetch via Energy-Charts (free), Open-Meteo (free), ENTSO-E (optional)
  - Body: MarketDataRequest {country, start_date, end_date, data_type (day_ahead_prices, wind, solar, load, generation)}
  - Return: MarketDataResponse {country, data_type, data, source, cached}

- `GET /api/v1/market-data/live/{country}` - Prix live 7 derniers jours
- `GET /api/v1/market-data/weather/{country}?days=7` - Météo forecast + historique
- `GET /api/v1/market-data/sources` - Liste sources, auth, status

## Agent (LangGraph)

- `POST /api/v1/agent/chat?query=...&country=FR` - Agent conversationnel, route vers bon module
  - Return: {query, intent, results, messages, mode (langgraph/simple), proactive_suggestions}

- `GET /api/v1/agent/capabilities` - Capacités agent, modules, exemples queries

## Exemples curl

```bash
# Health
curl http://localhost:8000/health

# Market analysis
curl -X POST http://localhost:8000/api/v1/market-analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"prices":[45,42,38,52,68,78,85,82,75,68],"country":"FR","technology":"solar"}'

# Scenario challenge
curl -X POST http://localhost:8000/api/v1/scenario/challenge \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_name":"AFRY Central 2030 FR",
    "model_type":"AFRY",
    "country":"FR",
    "horizon":2030,
    "assumptions":[
      {"name":"gas_price","value":38.5,"unit":"EUR/MWh","year":2030},
      {"name":"co2_price","value":120,"unit":"EUR/t","year":2030}
    ]
  }'

# Knowledge search
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query":"capture rate solaire BESS","top_k":3}'

# Agent chat
curl -X POST "http://localhost:8000/api/v1/agent/chat?query=Explique%20capture%20rate&country=FR"

# Market data live
curl http://localhost:8000/api/v1/market-data/live/FR

# Data quality (upload)
curl -X POST http://localhost:8000/api/v1/data-quality/check \
  -F "file=@backend/data_samples/sample_prices.csv" \
  -F "data_type=price"
```

## Codes Retour

- 200 OK
- 422 Unprocessable (validation error)
- 500 Internal Error

## Auth

Aucune auth par défaut (local). Pour prod, ajouter API key via middleware.

## Rate Limiting

Pas de rate limiting par défaut. Pour prod, ajouter via middleware.

## Pagination

Pas de pagination, limit 500 data points pour market data.

## Versioning

v1 actuellement, via prefix `/api/v1/`

## OpenAPI

- `/openapi.json` - Spec OpenAPI
- `/docs` - Swagger UI
- `/redoc` - ReDoc
