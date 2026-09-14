"""
Module 4: Meeting Copilot
Prépare réunions, génère questions, agendas, comptes rendus
"""
from typing import List, Dict, Any, Optional
import logging
from ..models.schemas import MeetingRequest, MeetingResponse, MinutesRequest, MinutesResponse
from ..agent.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

class MeetingCopilot:
    """
    Copilote réunion pour analystes marché électrique
    Utilise LLM si disponible, sinon templates experts
    """

    MEETING_TEMPLATES = {
        "AFRY Review": {
            "objectives": ["Challenger hypothèses BID3", "Comparer avec Aurora", "Identifier écarts vs interne"],
            "typical_duration": 90,
            "key_topics": ["Gas/CO2", "RES capacities", "Demand", "Interconnectors", "Capture rates", "BESS"]
        },
        "Aurora Review": {
            "objectives": ["Valider chronique prix", "Analyser capture rates", "Vérifier negative hours"],
            "typical_duration": 60,
            "key_topics": ["Price forecast", "Cannibalisation", "Flexibility", "Policy"]
        },
        "COMEX": {
            "objectives": ["Présenter vision marché", "Défendre hypothèses", "Obtenir arbitrage"],
            "typical_duration": 45,
            "key_topics": ["Executive summary", "Risques", "Opportunités", "Sensibilités", "Recommandation"]
        },
        "Trading": {
            "objectives": ["Partager vue court terme", "Aligner hedging", "Signaux marché"],
            "typical_duration": 30,
            "key_topics": ["Spot", "Forward", "Volatility", "Weather", "Outages"]
        }
    }

    def __init__(self):
        self.llm = LLMProvider()

    def prepare_meeting(self, request: MeetingRequest) -> MeetingResponse:
        template = self.MEETING_TEMPLATES.get(request.meeting_type, self.MEETING_TEMPLATES["AFRY Review"])

        # Generate agenda using LLM or template
        if self.llm.is_available():
            agenda = self._generate_agenda_llm(request, template)
            questions = self._generate_questions_llm(request, template)
            checklist = self._generate_checklist_llm(request, template)
            summary = self._generate_summary_llm(request, template)
        else:
            agenda = self._generate_agenda_template(request, template)
            questions = self._generate_questions_template(request, template)
            checklist = self._generate_checklist_template(request, template)
            summary = self._generate_summary_template(request, template)

        risks = self._generate_risks(request, template)
        data_to_prepare = self._generate_data_needs(request, template)

        return MeetingResponse(
            agenda=agenda,
            key_questions=questions,
            preparation_checklist=checklist,
            risks_to_raise=risks,
            data_to_prepare=data_to_prepare,
            executive_summary=summary
        )

    def _generate_agenda_template(self, request: MeetingRequest, template: Dict) -> List[Dict[str, str]]:
        base_agenda = [
            {"time": "0-5 min", "topic": "Objectifs & agenda", "owner": "Chair"},
            {"time": "5-20 min", "topic": f"Rappel contexte: {request.topic}", "owner": "Analyste"},
        ]
        # Add topic-specific slots
        for i, topic in enumerate(template["key_topics"][:4]):
            start = 20 + i*15
            base_agenda.append({
                "time": f"{start}-{start+15} min",
                "topic": f"Deep-dive {topic}",
                "owner": "Expert"
            })
        base_agenda.extend([
            {"time": f"{20+len(template['key_topics'][:4])*15}-{(20+len(template['key_topics'][:4])*15)+10} min", "topic": "Q&A & Challenge", "owner": "Tous"},
            {"time": "Dernier 5 min", "topic": "Next steps & actions", "owner": "Chair"}
        ])
        return base_agenda

    def _generate_agenda_llm(self, request: MeetingRequest, template: Dict) -> List[Dict[str, str]]:
        prompt = f"""
Tu es un analyste marché électrique senior préparant une réunion {request.meeting_type} sur {request.topic}.
Contexte: {request.context or 'Revue scénario long-terme'}
Participants: {', '.join(request.participants) if request.participants else 'Analystes, Traders, Management'}
Durée: {request.duration_min} min

Génère un agenda détaillé avec time slots, topics, owners.
Format JSON list: [{{"time": "...", "topic": "...", "owner": "..."}}]
"""
        try:
            resp = self.llm.generate(prompt, max_tokens=800)
            # Try to parse, fallback to template if fails
            import json, re
            # Extract JSON
            json_match = re.search(r'\[.*\]', resp, re.DOTALL)
            if json_match:
                agenda = json.loads(json_match.group(0))
                return agenda[:8]
        except Exception as e:
            logger.warning(f"LLM agenda failed: {e}")
        return self._generate_agenda_template(request, template)

    def _generate_questions_template(self, request: MeetingRequest, template: Dict) -> List[str]:
        base_questions = {
            "AFRY Review": [
                "Quelle est l'hypothèse gaz TTF 2030 et sensibilité vs forward actuel?",
                "Comment AFRY modélise la dispo nucléaire FR 70% vs 75% historique?",
                "Quelle trajectoire interco FR-DE 8GW vs 4GW actuel impact prix?",
                "Capture rate solaire 2030: 0.75 vs 0.85 Aurora - d'où vient l'écart?",
                "Hypothèse BESS: 20GW FR 2030 réaliste? Impact sur negative hours?",
                "Demande 600 TWh FR 2030: électrification vs sobriété, source RTE?",
                "Coût marginal: CCGT reste marginal combien d'heures en 2030?",
                "Stress test: si hiver froid + faible vent, prix cap?"
            ],
            "Aurora Review": [
                "Pourquoi Aurora voit 500h négatives vs 200h AFRY en 2030?",
                "Market Value Factor éolien offshore: comment évolue avec 10GW+ ?",
                "Hypothèse flexibilité demande: 5GW effacement réaliste?",
                "Curtailment RES: modélisé ou prix négatifs illimités?",
            ],
            "COMEX": [
                "Quel est le scénario central et le range P10-P90 pour baseload 2030?",
                "Quels sont les 3 risques majeurs sur valorisation portefeuille renouvelable?",
                "Opportunité BESS: business case à jour avec spreads actuels?",
                "Recommandation hedging: % à fixer 2025-2027?",
            ],
            "Trading": [
                "Vue spot semaine prochaine: impact météo vent/solaire?",
                "Outages nucléaires prévus: impact offre?",
                "Position gaz: TTF forward vs hypothèse long-terme?",
            ]
        }
        return base_questions.get(request.meeting_type, base_questions["AFRY Review"])[:8]

    def _generate_questions_llm(self, request: MeetingRequest, template: Dict) -> List[str]:
        prompt = f"""
Génère 8 questions percutantes pour challenger une réunion {request.meeting_type} sur {request.topic}.
Contexte marché électrique européen, modèles AFRY/Aurora.
Questions doivent être techniques, business-oriented, pour analyste senior.
Une question par ligne, numérotée.
"""
        try:
            resp = self.llm.generate(prompt, max_tokens=600)
            lines = [l.strip() for l in resp.split("\n") if l.strip() and "?" in l]
            # Clean numbering
            cleaned = [l.split(".",1)[-1].strip() if l[0].isdigit() else l for l in lines]
            return cleaned[:8]
        except Exception as e:
            logger.warning(f"LLM questions failed: {e}")
            return self._generate_questions_template(request, template)

    def _generate_checklist_template(self, request: MeetingRequest, template: Dict) -> List[str]:
        return [
            "📊 Extraire derniers runs AFRY/Aurora + comparer avec run précédent",
            "📈 Préparer graphe baseload 2025-2050 vs historique 2020-2024",
            "🔍 Vérifier unités et cohérence données (Data Quality Checker)",
            "📑 Lire executive summary AFRY/Aurora (10 pages)",
            "💡 Préparer 3 slides: hypothèses clés, écarts, risques",
            "📧 Envoyer pre-read 24h avant avec questions",
            "🎯 Définir objectif: validation, arbitrage, ou information?",
            "📝 Préparer template compte rendu"
        ]

    def _generate_checklist_llm(self, request: MeetingRequest, template: Dict) -> List[str]:
        # For now use template, LLM would add context-specific items
        base = self._generate_checklist_template(request, template)
        if request.context:
            base.append(f"📌 Spécifique contexte: {request.context[:100]} - vérifier données associées")
        return base

    def _generate_summary_template(self, request: MeetingRequest, template: Dict) -> str:
        return f"""
Réunion {request.meeting_type} sur {request.topic} ({request.duration_min}min)

Objectifs: {', '.join(template['objectives'])}

Contexte marché actuel: Forte volatilité, focus sur capture rates renouvelables, BESS, et hypothèses nucléaires FR.
Enjeu business: Valorisation portefeuille {request.topic} et sécurisation PPA long-terme.

Préparation critique: Data Quality Checker + Market Analysis Engine pour avoir chiffres à jour.
Message clé à faire passer: Vision fact-based, avec sensibilités quantifiées.

Risque si mal préparé: Hypothèses non challengées -> erreur valorisation multi-M€.
"""

    def _generate_summary_llm(self, request: MeetingRequest, template: Dict) -> str:
        prompt = f"""
Rédige un executive summary de préparation pour réunion {request.meeting_type} sur {request.topic}.
Contexte: {request.context}
Durée: {request.duration_min}min
Objectifs: {template['objectives']}

Format: 5-6 lignes, ton senior, business-oriented, marché électrique européen.
"""
        try:
            return self.llm.generate(prompt, max_tokens=400)
        except:
            return self._generate_summary_template(request, template)

    def _generate_risks(self, request: MeetingRequest, template: Dict) -> List[str]:
        return [
            "🚨 Risque modèle: AFRY et Aurora divergent de >20% sur baseload 2030 - lequel croire?",
            "⚠️ Hypothèse gaz: forward 2027 à 35€ mais scénario 2030 à 25€ - justification?",
            "📉 Cannibalisation: si capture rate solaire tombe à 0.6, impact -15€/MWh sur valorisation",
            "🔋 BESS: si déploiement plus lent que prévu, negative hours explosent",
            "🇫🇷 Nucléaire: dispo <70% = +10-15€/MWh baseload FR, sensibilité majeure",
            "🌍 Interco: retard projets FR-DE/FR-ES = prix FR plus volatil"
        ]

    def _generate_data_needs(self, request: MeetingRequest, template: Dict) -> List[str]:
        return [
            "Prix day-ahead FR/DE 2024 YTD vs 2023 (Energy-Charts API)",
            "Capture rates solaire/éolien calculés Market Analysis Engine",
            "Derniers runs AFRY/Aurora + run interne comparé Scenario Challenger",
            "Hypothèses RTE Bilan Prévisionnel 2023",
            "Forward TTF + EUA (CO2) 2025-2030",
            "Planning maintenance nucléaire EDF",
            "Pipeline projets BESS FR (source RTE)",
            "Météo: forecast vent/solaire 2 semaines (Open-Meteo)"
        ]

    def generate_minutes(self, request: MinutesRequest) -> MinutesResponse:
        """Génère compte rendu structuré à partir de notes brutes"""
        if self.llm.is_available():
            return self._generate_minutes_llm(request)
        else:
            return self._generate_minutes_template(request)

    def _generate_minutes_template(self, request: MinutesRequest) -> MinutesResponse:
        raw = request.raw_notes
        # Simple heuristic parsing
        decisions = []
        actions = []
        questions = []
        # Look for keywords
        lines = raw.split("\n")
        for line in lines:
            low = line.lower()
            if any(k in low for k in ["décidé", "decision", "validé", "approved"]):
                decisions.append(line.strip())
            if any(k in low for k in ["action", "todo", "à faire", "next"]):
                actions.append({"action": line.strip(), "owner": "TBD", "deadline": "TBD"})
            if "?" in line:
                questions.append(line.strip())

        if not decisions:
            decisions = ["Pas de décision explicite dans notes - à clarifier"]
        if not actions:
            actions = [{"action": "Partager compte rendu + slides", "owner": "Analyste", "deadline": "J+1"}]

        summary = f"Réunion {request.meeting_type}: {raw[:200]}..."
        formatted = f"""
# Compte Rendu - {request.meeting_type}
Date: Aujourd'hui
Participants: {', '.join(request.participants) if request.participants else 'Non spécifié'}

## Résumé
{summary}

## Décisions
{chr(10).join('- '+d for d in decisions)}

## Actions
{chr(10).join(f"- {a['action']} | {a['owner']} | {a['deadline']}" for a in actions)}

## Questions Ouvertes
{chr(10).join('- '+q for q in questions)}

## Next Steps
- Envoyer CR sous 24h
- Mettre à jour modèle si besoin
- Préparer COMEX si arbitrage nécessaire
"""
        return MinutesResponse(
            summary=summary,
            decisions=decisions,
            actions=actions,
            open_questions=questions,
            next_steps=["Envoyer CR", "Mettre à jour hypothèses", "Planifier suivi"],
            formatted_minutes=formatted
        )

    def _generate_minutes_llm(self, request: MinutesRequest) -> MinutesResponse:
        prompt = f"""
Tu es un analyste marché électrique. Génère un compte rendu structuré à partir de ces notes brutes:

Type: {request.meeting_type}
Notes: {request.raw_notes}
Participants: {request.participants}

Format JSON:
{{
  "summary": "résumé 3 lignes",
  "decisions": ["décision 1", ...],
  "actions": [{{"action": "...", "owner": "...", "deadline": "..."}}],
  "open_questions": ["question 1", ...],
  "next_steps": ["step 1", ...]
}}
"""
        try:
            resp = self.llm.generate(prompt, max_tokens=1000)
            import json, re
            json_match = re.search(r'\{.*\}', resp, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                formatted = f"# CR {request.meeting_type}\n\n## Résumé\n{data.get('summary')}\n\n## Décisions\n" + "\n".join(f"- {d}" for d in data.get('decisions',[]))
                return MinutesResponse(
                    summary=data.get('summary', ''),
                    decisions=data.get('decisions', []),
                    actions=data.get('actions', []),
                    open_questions=data.get('open_questions', []),
                    next_steps=data.get('next_steps', []),
                    formatted_minutes=formatted
                )
        except Exception as e:
            logger.warning(f"LLM minutes failed: {e}")
        return self._generate_minutes_template(request)
