# Roadmap - Power Market Intelligence Agent

## v1.0.0 (Actuel) - MVP SaaS

**Date**: Sept 2024

**Modules**:
- ✅ Data Quality Checker (unités, anomalies, missing, incohérences)
- ✅ Market Analysis Engine (baseload, peakload, negative hours, capture price/rate, MVF, cannibalisation, BESS revenue)
- ✅ Scenario Challenger (AFRY, Aurora, interne - hypothèses inhabituelles, écarts historiques, incohérences éco)
- ✅ Meeting Copilot (agenda, Q&A, checklist, CR)
- ✅ Presentation Generator (PPTX, DOCX, PDF - management, COMEX, AFRY)
- ✅ Knowledge Base (concepts marché, modèles, FAQ)

**Tech**:
- ✅ FastAPI backend + Streamlit frontend
- ✅ LangGraph agent + LLM provider (OpenAI/Claude/Azure/Local fallback)
- ✅ Public APIs gratuites (Energy-Charts, Open-Meteo) + ENTSO-E optional + Mock fallback
- ✅ Installation 100 % native (Windows sans admin : setup.ps1/start.ps1 ; Linux/macOS : setup.sh/start.sh) + VS Code config
- ✅ Tests (15+ tests)
- ✅ Docs (INSTALLATION, VSCODE_GUIDE, API_DOCS, USER_GUIDE, ARCHITECTURE)

**Fonctionnel**: 100% sans clé API, fallback local

## v1.1.0 - Améliorations UX + Data

**Prévu**: Q4 2024

- [ ] **Forward Curve Builder**: Construire courbe forward à partir spot + futures (EEX)
- [ ] **PPA Pricer**: Pricer PPA pay-as-produced vs baseload avec floor/cap, calcul MtM
- [ ] **BESS Optimizer**: Optimisation dispatch BESS avec MILP, revenue stacking détaillé (FCR, aFRR, NEBEF)
- [ ] **Weather Data Enhancement**: Intégrer plus de variables Open-Meteo (température, cloud cover) pour proxy solaire/éolien plus précis
- [ ] **ENTSO-E Full Integration**: Load, generation, cross-border flows, plus de pays
- [ ] **UI Improvements**: 
  - Dark mode
  - Export CSV des analyses
  - Comparaison multi-scénarios côte-à-côte
  - Dashboard personnalisable (drag & drop)
- [ ] **Auth**: Ajouter API key + user management basique

## v1.2.0 - Modélisation Avancée

**Prévu**: Q1 2025

- [ ] **PLEXOS Connector**: Importer runs PLEXOS, comparer avec AFRY/Aurora
- [ ] **RTE Data Connector**: Bilan Prévisionnel, éCO2mix, données temps réel RTE
- [ ] **EPEX Spot Connector**: Prix intraday, volumes
- [ ] **Capture Rate Forecast**: Modèle ML simple pour forecast capture rate basé sur capacités RES
- [ ] **Negative Hours Forecast**: Forecast heures négatives basé sur météo + capacités
- [ ] **Sensitivity Runner**: Lancer automatiquement sensibilités gas +/-20%, CO2 +/-30%, demande +/-10%, et générer slides comparatives
- [ ] **Automated Reporting**: Rapport mensuel automatique (prix, capture rates, news) envoyé par email

## v1.3.0 - Collaboration + Intégration

**Prévu**: Q2 2025

- [ ] **Teams/Slack Bot**: Bot pour poser questions marché directement dans Teams/Slack, recevoir alertes
- [ ] **SharePoint Integration**: Lire/écrire documents SharePoint (notes internes, docs AFRY)
- [ ] **JIRA Integration**: Créer tickets JIRA à partir actions CR
- [ ] **Multi-user**: Gestion utilisateurs, rôles (analyste, trader, manager), partage analyses
- [ ] **Comments & Annotations**: Commenter analyses, partager insights
- [ ] **Versioning**: Versioning scénarios, comparatif historique
- [ ] **Notifications**: Alertes si prix > seuil, negative hours > X, écart AFRY/Aurora >20%

## v2.0.0 - Intelligence Avancée + SaaS

**Prévu**: Q3 2025

- [ ] **Vector DB + RAG**: Qdrant/Chroma pour Knowledge Base, RAG avancé avec embeddings (OpenAI, HuggingFace)
- [ ] **Fine-tuned LLM**: Fine-tune LLM sur docs internes (AFRY, notes) pour réponses plus précises
- [ ] **ML Models**:
  - Forecast prix day-ahead avec ML (LSTM, XGBoost)
  - Forecast capture rate
  - Clustering scénarios
- [ ] **Optimization Engine**: Optimisation portefeuille RES + BESS (quelles technos, où, quand)
- [ ] **Risk Engine**: VaR, CVaR pour portefeuille, stress tests
- [ ] **API Gateway**: Rate limiting, auth JWT, quotas, monitoring Prometheus
- [ ] **Frontend React**: Migrer Streamlit vers React pour plus de customisation (optionnel, garder Streamlit pour rapidité)
- [ ] **Mobile App**: App mobile pour dashboard + alertes
- [ ] **SaaS Deployment**: Déploiement cloud (Azure/AWS/GCP) avec CI/CD, auto-scaling, monitoring

## v2.1.0 - Marchés Avancés

**Prévu**: Q4 2025

- [ ] **Intraday Market**: Analyse intraday, continuous trading
- [ ] **Balancing Market**: aFRR, mFRR, FCR, NEBEF
- [ ] **Capacity Market**: Modélisation capacity market FR, GB, BE
- [ ] **Hydro Modeling**: Modélisation hydro (lac, fil eau) avec optimisation
- [ ] **Hydrogen**: Électrolyseur, H2 market, couplage élec/H2
- [ ] **Carbon Market**: EU ETS modeling, forecast CO2
- [ ] **Gas Market**: TTF modeling, spread spark

## Idées Long-Terme (v3.0+)

- [ ] **Digital Twin**: Jumeau numérique réseau EU
- [ ] **Scenario Generator**: Génération automatique scénarios avec IA
- [ ] **Automated Trading**: Signaux trading basés sur analyses
- [ ] **PPA Marketplace**: Matching producteurs/consommateurs PPA
- [ ] **BESS Fleet Optimizer**: Optimisation fleet BESS EU
- [ ] **Interconnector Optimizer**: Optimisation flows interco
- [ ] **Policy Simulator**: Simuler impact politiques (Fit-for-55, RED III)
- [ ] **Climate Impact**: Impact changement climatique sur demande/offre

## Feedback & Priorisation

- **Analystes**: Quelle feature la plus utile au quotidien?
- **Traders**: Besoin intraday, forward curve, VaR?
- **Stratégie**: Besoin long-terme, scénarios, optimisation portefeuille?
- **Management**: Besoin COMEX slides, executive summary, risques?

Ouvrir issue GitHub avec label `enhancement` pour proposer feature.

## Métriques Succès

- **Adoption**: Nombre analystes utilisant quotidiennement
- **Time saved**: Heures gagnées par analyste (vs Excel manuel)
- **Quality**: Réduction erreurs données, amélioration challenge scénarios
- **Business impact**: Meilleure valorisation PPA, BESS, hedging -> M€ économisés

## Contribuer

Voir CONTRIBUTING.md (à venir) - fork, branch, PR.

## Changelog

### v1.0.0 (Sept 2024)
- Initial release, 6 modules, scripts d'installation natifs, VS Code, tests, docs
- 100% fonctionnel sans clé API
- APIs publiques gratuites Energy-Charts + Open-Meteo
- Fallback local LLM
