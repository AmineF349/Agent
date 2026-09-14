# Avoid circular imports - import directly where needed
# from .data_quality_checker import DataQualityChecker
# from .market_analysis_engine import MarketAnalysisEngine
# from .scenario_challenger import ScenarioChallenger
# from .meeting_copilot import MeetingCopilot
# from .presentation_generator import PresentationGenerator
# from .knowledge_base import KnowledgeBaseService

__all__ = [
    "DataQualityChecker",
    "MarketAnalysisEngine",
    "ScenarioChallenger",
    "MeetingCopilot",
    "PresentationGenerator",
    "KnowledgeBaseService"
]

def __getattr__(name):
    if name == "DataQualityChecker":
        from .data_quality_checker import DataQualityChecker
        return DataQualityChecker
    if name == "MarketAnalysisEngine":
        from .market_analysis_engine import MarketAnalysisEngine
        return MarketAnalysisEngine
    if name == "ScenarioChallenger":
        from .scenario_challenger import ScenarioChallenger
        return ScenarioChallenger
    if name == "MeetingCopilot":
        from .meeting_copilot import MeetingCopilot
        return MeetingCopilot
    if name == "PresentationGenerator":
        from .presentation_generator import PresentationGenerator
        return PresentationGenerator
    if name == "KnowledgeBaseService":
        from .knowledge_base import KnowledgeBaseService
        return KnowledgeBaseService
    raise AttributeError(f"module {__name__} has no attribute {name}")

