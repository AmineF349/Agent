# User Guide - Power Market Intelligence Agent

## Pour Analystes Marché Électrique (sans compétences dev avancées)

### Lancement

Aucun Docker, aucune base de données, aucun droit administrateur : tout tourne dans un `.venv` local.

**Windows (poste d'entreprise, sans droits admin) :**
```powershell
.\setup.ps1     # une seule fois
.\start.ps1     # ouvre http://localhost:8501
```
Arrêt : `.\stop.ps1`. Si PowerShell bloque les scripts, double-cliquez sur `setup.cmd` puis `start.cmd`.
Détails : `docs/WINDOWS_SETUP.md`.

**Linux / macOS :**
```bash
./setup.sh      # une seule fois
./start.sh      # ouvre http://localhost:8501 (services en arrière-plan, logs dans logs/)
```
Arrêt : `./stop.sh`. Détails : `docs/INSTALLATION.md`.

**Ou local manuel :**
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && streamlit run app.py --server.port 8501` (avec `BACKEND_URL=http://localhost:8000`)
- Ouvrir http://localhost:8501

### Workflow Analyste Quotidien

#### 1. Dashboard (Vue d'ensemble)

- Voir prix live FR/DE via Energy-Charts (gratuit)
- Alertes proactives: negative hours, spread BESS, écart AFRY/Aurora
- KPIs: capture rates, BESS revenue, benchmarks

#### 2. Data Analysis (2 modules)

**Data Quality Checker:**
1. Upload CSV prix (ex: `backend/data_samples/sample_prices.csv`)
2. Choisir type: price
3. Lancer check
4. Voir score /100, issues (missing, anomalies, incohérences), suggestions correction
5. Si score <70, corriger source

**Market Analysis Engine:**
1. Choisir source: Mock FR 30j, Live API, Upload CSV, Manuel
2. Sélectionner pays (FR) et techno (solar)
3. Calculer KPI: baseload, peakload, negative hours, capture price/rate, MVF, cannibalisation, volatility
4. Voir insights proactifs: ex "Capture rate 0.65 faible -> opportunité BESS"
5. Charts: timeseries, histogram, gauge capture rate
6. BESS Revenue: slider capacité/duration, calculer revenu annuel

**Use case:** Vous avez 1 an prix horaires + profil solaire 100MW, calculez valorisation PPA: baseload * capture_rate.

#### 3. Scenario Review (Challenge AFRY/Aurora)

1. Entrer scénario: nom, modèle (AFRY/Aurora/Interne), pays, horizon
2. Hypothèses JSON: gas_price, co2_price, demand, solar_capacity, wind_capacity, nuclear_availability, capture_rate, negative_hours...
3. Ou charger sample: `sample_scenario.json`
4. Challenger: score /100, issues (unusual_hypothesis, historical_deviation, economic_inconsistency), peer comparison AFRY/Aurora, risques & opportunités business
5. Benchmarks: voir ranges typiques FR/DE
6. AFRY vs Aurora: comparatif modèles

**Use case:** Avant COMEX, challenger scénario AFRY Central 2030 FR: gas 38€ vs forward 32€ -> warning, à justifier. Préparer 3 sensibilités.

#### 4. Presentation Builder

1. Choisir type: Management, COMEX, AFRY Support, Executive Note, Market Update
2. Titre, sous-titre, pays, auteur
3. Slides JSON: title, bullets, notes, data (ou utiliser default 6 slides)
4. Générer: PPTX + DOCX + PDF dans `generated/`
5. Télécharger via UI ou `generated/` folder

**Use case:** Préparer COMEX 15min: 5 slides (executive summary, hypothèses, capture rates, BESS, reco) + DOCX note 2 pages.

#### 5. Meeting Assistant

**Préparer réunion:**
1. Type: AFRY Review (90min), COMEX (45min), Trading (30min)...
2. Topic: ex "Revue scénario AFRY Central 2030 FR"
3. Durée, participants, contexte
4. Générer: agenda avec time slots, 8 questions challenge, checklist préparation, risques à soulever, data à préparer, executive summary

**Générer CR:**
1. Type réunion, participants, notes brutes (copier notes)
2. Générer: summary, décisions, actions avec owner/deadline, questions ouvertes, next steps, CR formaté markdown

**Use case:** Préparer AFRY Review 90min, puis générer CR après réunion.

#### 6. Knowledge Center

1. Recherche: question libre ex "Explique capture rate solaire et opportunité BESS"
2. Catégorie: all, concepts, models
3. Top K résultats
4. Voir réponse synthétisée (via LLM si clé, sinon template expert) + résultats avec score + source + tags + questions liées
5. Documents: lister tous docs par catégorie
6. FAQ: questions fréquentes

**Use case:** Nouveau analyste, apprendre capture rate, BESS, AFRY vs Aurora.

#### 7. Agent Chat (Dashboard)

- Chat conversationnel en bas Dashboard
- Posez question: "Analyse capture rate solaire FR", "Challenge scénario AFRY 2030", "Prépare réunion COMEX", "Donne prix day-ahead FR dernière semaine"
- Agent détecte intent (LangGraph ou simple routing) et route vers bon module
- Réponse synthétique + suggestions proactives

### Exemples Concrets

#### Exemple 1: Valorisation PPA Solaire 100MW FR

1. Data Analysis -> Market Analysis -> Mock FR 30j + solar
2. Calculer: baseload 65€, capture rate 0.78, capture price 50.7€
3. PPA price = baseload * capture_rate * (1 - discount 10%) = 65*0.78*0.9 = 45.6€/MWh
4. Si capture rate tombe à 0.65 en 2030 (cannibalisation), PPA 38€ -> perte 7.6€/MWh * 100MW * 8760h * 0.14 CF * 20 ans = ~18M€!
5. Scenario Review -> challenger scénario capture rate 0.78 vs 0.65 Aurora
6. Presentation Builder -> slides pour COMEX avec risque
7. Meeting Assistant -> préparer COMEX

#### Exemple 2: Business Case BESS 10MW/2h FR

1. Dashboard -> voir spread peak/offpeak 28€, negative hours 150h
2. Data Analysis -> BESS Revenue -> 10MW/2h, 85% efficacité -> revenu 220k€/MW/an
3. Knowledge Center -> recherche "BESS revenue stacking" -> FCR + aFRR + capacité = 300k€/MW/an total
4. Scenario Review -> challenger scénario BESS 5GW FR 2030 réaliste?
5. Presentation Builder -> slides BESS opportunity pour management

#### Exemple 3: Préparer COMEX sur AFRY vs Aurora

1. Scenario Review -> charger sample_scenario.json AFRY Central 2030 FR
2. Challenger -> score 85/100, 2 warnings (gas 38€ vs forward 32€, BESS 5GW ambitieux)
3. Benchmarks -> voir ranges
4. AFRY vs Aurora -> comparer baseload 80€ vs 70€
5. Meeting Assistant -> préparer COMEX 45min sur "AFRY vs Aurora - arbitrage valorisation"
6. Presentation Builder -> générer slides COMEX 5 slides + note exécutive DOCX
7. Knowledge Center -> recherche "Comment challenger scénario gaz?" pour Q&A

### Tips Productivité

- **Toujours** Data Quality Checker avant Market Analysis
- **Toujours** Scenario Challenger avant COMEX
- **Toujours** comparer AFRY vs Aurora, écart >20% = investiguer
- **Proactif**: agent suggère analyses complémentaires, risques, opportunités
- **Next steps**: chaque module suggère next steps concrets
- **Templates**: utiliser sample files dans `backend/data_samples/`

### Raccourcis

- Dashboard: vue d'ensemble + agent chat
- Data Analysis: qualité + KPI + BESS
- Scenario Review: challenge + benchmarks + AFRY vs Aurora
- Presentation Builder: PPTX/DOCX/PDF
- Meeting Assistant: agenda + Q&A + CR
- Knowledge Center: concepts + FAQ

### Support

- README.md pour overview technique
- docs/INSTALLATION.md pour installation
- docs/VSCODE_GUIDE.md pour dev
- docs/API_DOCS.md pour API
- http://localhost:8000/docs pour API interactive
- knowledge_base/faq.md pour FAQ

### Glossaire Rapide

- **Baseload**: moyenne toutes heures
- **Peakload**: Mon-Fri 8-20h
- **Capture Rate**: prix capté / baseload, <1 = cannibalisation
- **Negative Hours**: prix <0, cause surproduction RES
- **BESS**: batteries stockage, 2-4h, arbitrage
- **AFRY BID3**: modèle fondamental dispatch EU
- **Aurora**: modèle focus capture rates + BESS
- **PPA**: contrat achat élec long-terme
- **TTF**: prix gaz référence EU
- **EUA**: prix CO2

### Feedback

- Ouvrir issue GitHub
- Contacter équipe modélisation
- Proposer features via ROADMAP.md
