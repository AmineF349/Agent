# FAQ - Power Market Intelligence Agent

## Général

**Q: Qu'est-ce que Power Market Intelligence Agent?**
R: Copilote IA pour analystes marchés électriques européens. 6 modules: Data Quality, Market Analysis, Scenario Challenger, Meeting Copilot, Presentation Generator, Knowledge Base. Déployable localement via Docker, fonctionne sans clé API (fallback local) ou avec OpenAI/Claude/Azure.

**Q: Quelle est la stack technique?**
R: Backend Python FastAPI, Frontend Streamlit, Agent LangGraph/CrewAI, Data Pandas/Polars, Visu Plotly, DB Postgres/SQLite, Docker.

**Q: Besoin de clé API?**
R: Non, 100% fonctionnel sans clé grâce à APIs publiques gratuites (Energy-Charts.info, Open-Meteo) et fallback local. Optionnel: ENTSO-E clé gratuite, OpenAI/Claude/Azure pour LLM plus riche.

## Data Quality Checker

**Q: Que vérifie le module?**
R: Unités, valeurs manquantes, anomalies (IQR, z-score), incohérences (prix négatif + faible RES), gaps temporels, duplicates. Score qualité /100.

**Q: Quel format fichier?**
R: CSV ou Excel, avec colonnes prix, génération, timestamps. Exemple dans backend/data_samples/

**Q: Que faire si score <70?**
R: Bloquer utilisation en prod, investiguer source, corriger, relancer. Voir suggestions dans rapport.

## Market Analysis Engine

**Q: Comment calculer capture rate?**
R: Fournir prix horaires + génération horaire (ex: solaire). Engine calcule Capture Price = Σ(prix*gen)/Σ(gen), Capture Rate = Capture Price / Baseload.

**Q: C'est quoi cannibalisation?**
R: Quand beaucoup de solaire produit midi, prix baisse, capture rate baisse. 1 - capture_rate = cannibalisation factor.

**Q: Comment estimer revenu BESS?**
R: Endpoint /bess-revenue, avec prix horaires, capacité MW, duration h, efficacité. Calcul simplifié perfect foresight 1 cycle/jour.

**Q: Quelle différence baseload/peakload?**
R: Baseload = moyenne toutes heures, Peakload = Mon-Fri 8-20h, Offpeak = reste. Peak/offpeak spread = valeur flexibilité.

## Scenario Challenger

**Q: Quelle différence AFRY vs Aurora?**
R: AFRY BID3: focus réseau + dispatch, prix souvent plus haut. Aurora: focus capture rates + BESS, prix plus bas, plus de flexibilité assumée. Écart 10-20% typique baseload 2030.

**Q: Comment challenger un scénario?**
R: Fournir hypothèses (gas, CO2, demande, capacités RES, nucléaire, etc.). Module compare avec benchmarks historiques, ranges AFRY/Aurora, détecte incohérences.

**Q: C'est quoi une hypothèse inhabituelle?**
R: Ex: gas 20€ 2030 vs 35€ forward = très bas, implique abondance LNG. Ou nucléaire 90% dispo = jamais atteint historiquement.

**Q: Comment préparer COMEX?**
R: Utiliser Scenario Challenger pour identifier 3 hypothèses clés + sensibilités, puis Meeting Copilot pour agenda + Q&A, puis Presentation Generator pour slides.

## Meeting Copilot

**Q: Quels types réunions?**
R: AFRY Review (90min), Aurora Review (60min), COMEX (45min), Trading (30min), Strategy, Modeling, Client.

**Q: Que génère le module?**
R: Agenda détaillé avec time slots, questions challenge (8), checklist préparation, risques à soulever, data à préparer, executive summary.

**Q: Comment générer compte rendu?**
R: Fournir notes brutes, participants, type réunion. Module génère summary, décisions, actions avec owner/deadline, questions ouvertes, next steps.

## Presentation Generator

**Q: Quels formats?**
R: PPTX (slides), DOCX (note exécutive), PDF (export). Générés dans generated/.

**Q: Quels types présentations?**
R: Management (KPI + risques), COMEX (synthèse + recommandation), AFRY Support (hypothèses + écarts), Executive Note, Market Update.

**Q: Comment personnaliser template?**
R: Modifier backend/app/services/presentation_generator.py, COLORS, layouts. Ou fournir slides content avec bullets, notes, data.

## Knowledge Base

**Q: Que contient la base?**
R: Concepts marché (capture rate, baseload, negative hours, BESS, interco), modèles (AFRY BID3, Aurora), hypothèses, FAQ.

**Q: Comment rechercher?**
R: Endpoint /knowledge/search avec query, category optionnelle, top_k. Recherche keyword + TF-IDF simple, synthèse via LLM si disponible.

**Q: Puis-je ajouter documents?**
R: Oui, ajouter .md dans knowledge_base/concepts/ ou knowledge_base/models/, redémarrer backend, ils seront chargés automatiquement.

## APIs Publiques

**Q: Quelles APIs gratuites?**
R: Energy-Charts.info (prix day-ahead, génération, sans clé), Open-Meteo (météo, vent, solaire, sans clé), ENTSO-E (optionnel, clé gratuite).

**Q: Comment obtenir clé ENTSO-E?**
R: Créer compte gratuit sur https://transparency.entsoe.eu/usrm/user/createAccount, générer token, mettre dans .env ENTSOE_API_KEY.

**Q: Et si APIs down?**
R: Fallback mock generator avec données réalistes, 100% fonctionnel.

## LLM

**Q: Sans clé LLM, ça marche?**
R: Oui, fallback local avec templates experts marché électrique, 100% fonctionnel pour tous calculs techniques. LLM apporte plus de richesse rédactionnelle.

**Q: Quelle clé recommandée?**
R: OpenAI gpt-4o-mini (économique) ou Anthropic Claude 3.5 Sonnet (meilleur pour analyse). Azure OpenAI si entreprise.

**Q: Coût LLM?**
R: gpt-4o-mini ~0.15$/1M tokens input, 0.6$/1M output. Pour usage analyste (100 requêtes/jour), <10$/mois.

## Déploiement

**Q: Comment lancer localement?**
R: Voir docs/INSTALLATION.md et docs/VSCODE_GUIDE.md. Docker Compose: docker-compose up --build. Ou local: pip install -r backend/requirements.txt + uvicorn + streamlit.

**Q: Besoin de GPU?**
R: Non, tout CPU. LLM via API, pas local.

**Q: Données sensibles?**
R: Tout local, pas d'envoi données vers cloud sauf si LLM activé (OpenAI/Claude). Possibilité de rester 100% local avec fallback.

## Roadmap

**Q: Prochaines fonctionnalités?**
R: Voir ROADMAP.md: PLEXOS connector, BESS optimizer, PPA pricer, forward curve builder, automated reporting, Teams/Slack bot, etc.

## Support

**Q: Qui contacter?**
R: Voir README.md, ouvrir issue GitHub, ou contacter équipe modélisation.

**Q: Comment contribuer?**
R: Fork, branch, PR. Voir docs/CONTRIBUTING.md (à venir).
