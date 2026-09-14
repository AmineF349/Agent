"""
LangGraph Agent - Orchestrateur principal
Route les requêtes vers les bons modules
"""
from typing import Dict, Any, List, Optional, TypedDict
import logging

from .llm_provider import LLMProvider

# Lazy imports to avoid circular dependencies
def _get_services():
    from ..services.data_quality_checker import DataQualityChecker
    from ..services.market_analysis_engine import MarketAnalysisEngine
    from ..services.scenario_challenger import ScenarioChallenger
    from ..services.meeting_copilot import MeetingCopilot
    from ..services.knowledge_base import KnowledgeBaseService
    from ..data.connectors import EnergyChartsConnector, OpenMeteoConnector, MockDataGenerator
    return DataQualityChecker, MarketAnalysisEngine, ScenarioChallenger, MeetingCopilot, KnowledgeBaseService, EnergyChartsConnector, OpenMeteoConnector, MockDataGenerator


logger = logging.getLogger(__name__)

# State for LangGraph
class AgentState(TypedDict):
    query: str
    intent: str
    context: Dict[str, Any]
    results: Dict[str, Any]
    messages: List[Dict[str, str]]
    next_action: str

class PowerMarketAgent:
    """
    Agent principal orchestrant tous les modules
    Utilise LangGraph pattern mais implémentation légère sans dépendance obligatoire
    Fallback à routing simple si LangGraph non disponible
    """

    def __init__(self):
        self.llm = LLMProvider()
        DataQualityChecker, MarketAnalysisEngine, ScenarioChallenger, MeetingCopilot, KnowledgeBaseService, EnergyChartsConnector, OpenMeteoConnector, MockDataGenerator = _get_services()
        self.dq_checker = DataQualityChecker()
        self.market_engine = MarketAnalysisEngine()
        self.scenario_challenger = ScenarioChallenger()
        self.meeting_copilot = MeetingCopilot()
        self.kb = KnowledgeBaseService()

        self.energy_charts = EnergyChartsConnector()
        self.open_meteo = OpenMeteoConnector()
        self.mock_gen = MockDataGenerator()

        # Try to init LangGraph if available
        self.langgraph_available = False
        try:
            from langgraph.graph import StateGraph, END
            self.StateGraph = StateGraph
            self.END = END
            self.langgraph_available = True
            self._build_graph()
            logger.info("LangGraph initialized")
        except ImportError:
            logger.info("LangGraph not available, using simple routing")
            self.graph = None

    def _build_graph(self):
        """Build LangGraph workflow"""
        try:
            workflow = self.StateGraph(AgentState)

            # Nodes
            workflow.add_node("intent_detection", self._detect_intent)
            workflow.add_node("data_quality", self._handle_data_quality)
            workflow.add_node("market_analysis", self._handle_market_analysis)
            workflow.add_node("scenario_challenge", self._handle_scenario)
            workflow.add_node("knowledge_search", self._handle_knowledge)
            workflow.add_node("market_data_fetch", self._handle_market_data)
            workflow.add_node("synthesis", self._synthesize)

            # Edges
            workflow.set_entry_point("intent_detection")

            workflow.add_conditional_edges(
                "intent_detection",
                self._route_intent,
                {
                    "data_quality": "data_quality",
                    "market_analysis": "market_analysis",
                    "scenario": "scenario_challenge",
                    "knowledge": "knowledge_search",
                    "market_data": "market_data_fetch",
                    "synthesis": "synthesis"
                }
            )

            workflow.add_edge("data_quality", "synthesis")
            workflow.add_edge("market_analysis", "synthesis")
            workflow.add_edge("scenario_challenge", "synthesis")
            workflow.add_edge("knowledge_search", "synthesis")
            workflow.add_edge("market_data_fetch", "synthesis")
            workflow.add_edge("synthesis", self.END)

            self.graph = workflow.compile()
        except Exception as e:
            logger.warning(f"Failed to build LangGraph: {e}")
            self.graph = None
            self.langgraph_available = False

    def _detect_intent(self, state: AgentState) -> AgentState:
        query = state["query"].lower()

        # Simple keyword intent detection
        if any(k in query for k in ["qualité", "quality", "missing", "anomalie", "vérifier données"]):
            intent = "data_quality"
        elif any(k in query for k in ["capture rate", "capture price", "baseload", "peakload", "negative hours", "cannibalisation", "market value", "prix"]):
            intent = "market_analysis"
        elif any(k in query for k in ["afry", "aurora", "scénario", "scenario", "hypothèse", "challenger"]):
            intent = "scenario"
        elif any(k in query for k in ["réunion", "meeting", "agenda", "comex", "préparer"]):
            intent = "meeting"
        elif any(k in query for k in ["prix spot", "day-ahead", "energy-charts", "entsoe", "météo", "weather"]):
            intent = "market_data"
        else:
            intent = "knowledge"

        state["intent"] = intent
        state["messages"].append({"role": "assistant", "content": f"Intent détecté: {intent}"})
        return state

    def _route_intent(self, state: AgentState) -> str:
        return state.get("intent", "knowledge")

    def _handle_data_quality(self, state: AgentState) -> AgentState:
        # Placeholder - actual data passed via context
        state["results"]["data_quality"] = "Utilisez l'API /data-quality/check avec votre fichier CSV"
        return state

    def _handle_market_analysis(self, state: AgentState) -> AgentState:
        # If prices in context, calculate
        prices = state["context"].get("prices")
        if prices:
            try:
                generation = state["context"].get("generation")
                result = self.market_engine.analyze(prices, generation)
                state["results"]["market_analysis"] = result.model_dump()
            except Exception as e:
                state["results"]["market_analysis"] = {"error": str(e)}
        else:
            state["results"]["market_analysis"] = "Fournissez prix horaires pour analyse"
        return state

    def _handle_scenario(self, state: AgentState) -> AgentState:
        scenario = state["context"].get("scenario")
        if scenario:
            try:
                from ..models.schemas import ScenarioInput
                # Assume scenario is already ScenarioInput or dict
                if isinstance(scenario, dict):
                    scenario = ScenarioInput(**scenario)
                result = self.scenario_challenger.challenge(scenario)
                state["results"]["scenario"] = result.model_dump()
            except Exception as e:
                state["results"]["scenario"] = {"error": str(e)}
        else:
            state["results"]["scenario"] = "Fournissez scénario pour challenge"
        return state

    def _handle_knowledge(self, state: AgentState) -> AgentState:
        try:
            result = self.kb.search(state["query"], top_k=3)
            state["results"]["knowledge"] = result.model_dump()
        except Exception as e:
            state["results"]["knowledge"] = {"error": str(e)}
        return state

    def _handle_market_data(self, state: AgentState) -> AgentState:
        try:
            country = state["context"].get("country", "FR")
            data = self.energy_charts.get_day_ahead_prices(country=country, year=2024)
            state["results"]["market_data"] = {"country": country, "count": len(data), "sample": data[:5]}
        except Exception as e:
            state["results"]["market_data"] = {"error": str(e)}
        return state

    def _synthesize(self, state: AgentState) -> AgentState:
        # Final synthesis via LLM
        query = state["query"]
        results = state["results"]
        intent = state.get("intent", "unknown")

        prompt = f"""
Question utilisateur: {query}
Intent: {intent}
Résultats modules: {str(results)[:2000]}

En tant que Power Market Intelligence Agent, fournis une réponse synthétique, proactive, avec:
- Réponse directe
- 2-3 insights business
- 1-2 risques/opportunités
- Next steps concrets
Ton senior, marché électrique européen.
"""
        try:
            synthesis = self.llm.generate(prompt, max_tokens=800, system="Tu es un expert marché électrique européen senior.")
            state["results"]["synthesis"] = synthesis
            state["messages"].append({"role": "assistant", "content": synthesis})
        except Exception as e:
            state["results"]["synthesis"] = f"Synthèse: {results}"
            logger.warning(f"Synthesis failed: {e}")

        return state

    def run(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run agent with query + optional context
        """
        initial_state: AgentState = {
            "query": query,
            "intent": "",
            "context": context or {},
            "results": {},
            "messages": [{"role": "user", "content": query}],
            "next_action": ""
        }

        if self.graph and self.langgraph_available:
            try:
                final_state = self.graph.invoke(initial_state)
                return {
                    "query": query,
                    "intent": final_state.get("intent"),
                    "results": final_state.get("results"),
                    "messages": final_state.get("messages"),
                    "mode": "langgraph"
                }
            except Exception as e:
                logger.warning(f"LangGraph run failed: {e}, fallback to simple")

        # Fallback simple routing
        state = self._detect_intent(initial_state)
        intent = state["intent"]

        if intent == "data_quality":
            state = self._handle_data_quality(state)
        elif intent == "market_analysis":
            state = self._handle_market_analysis(state)
        elif intent == "scenario":
            state = self._handle_scenario(state)
        elif intent == "market_data":
            state = self._handle_market_data(state)
        else:
            state = self._handle_knowledge(state)

        state = self._synthesize(state)

        return {
            "query": query,
            "intent": intent,
            "results": state["results"],
            "messages": state["messages"],
            "mode": "simple_routing"
        }

    def proactive_suggestions(self, last_analysis: Dict[str, Any]) -> List[str]:
        """
        Génère suggestions proactives comme un vrai copilote
        """
        suggestions = [
            "💡 Avez-vous vérifié la qualité des données avec Data Quality Checker?",
            "📊 Calculez capture rates pour solaire/éolien - KPI clé pour PPA",
            "🔍 Challengez scénario avec Scenario Challenger avant COMEX",
            "📈 Comparez avec données Energy-Charts (gratuit) pour benchmark",
            "🔋 Évaluez opportunité BESS si negative hours >5% ou capture rate <0.7"
        ]

        # Contextual suggestions based on last analysis
        if "market_analysis" in last_analysis:
            ma = last_analysis["market_analysis"]
            if isinstance(ma, dict) and "metrics" in ma:
                metrics = ma["metrics"]
                if metrics.get("negative_hours_pct", 0) > 5:
                    suggestions.insert(0, "🚨 Negative hours élevées - modélisez BESS 2h/4h pour arbitrage")
                if metrics.get("capture_rate", 1) < 0.7:
                    suggestions.insert(0, "⚠️ Capture rate faible - vérifiez clauses floor dans PPA")

        return suggestions[:5]
