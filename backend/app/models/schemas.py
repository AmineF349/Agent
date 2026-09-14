from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import enum

# --- Data Quality ---
class DataQualityIssue(BaseModel):
    type: Literal["missing", "anomaly", "unit", "inconsistency", "outlier"]
    severity: Literal["low", "medium", "high", "critical"]
    column: str
    row_index: Optional[int] = None
    value: Optional[Any] = None
    expected: Optional[str] = None
    message: str
    suggestion: Optional[str] = None

class DataQualityReport(BaseModel):
    total_rows: int
    total_columns: int
    issues: List[DataQualityIssue]
    missing_pct: Dict[str, float]
    summary: str
    quality_score: float = Field(ge=0, le=100)
    passed: bool

# --- Market Analysis ---
class MarketAnalysisRequest(BaseModel):
    prices: List[float] = Field(description="Hourly prices in EUR/MWh")
    generation: Optional[List[float]] = Field(default=None, description="Renewable generation profile")
    timestamps: Optional[List[datetime]] = None
    baseload_price: Optional[float] = None
    country: str = "FR"
    technology: str = "solar"  # solar, wind_onshore, wind_offshore, etc.

class MarketMetrics(BaseModel):
    baseload: float
    peakload: float
    offpeak: float
    min_price: float
    max_price: float
    avg_price: float
    std_price: float
    negative_hours: int
    negative_hours_pct: float
    zero_hours: int
    capture_price: Optional[float] = None
    capture_rate: Optional[float] = None
    market_value_factor: Optional[float] = None
    cannibalisation_factor: Optional[float] = None
    p10: float
    p50: float
    p90: float
    volatility: float
    total_hours: int

class MarketAnalysisResponse(BaseModel):
    metrics: MarketMetrics
    insights: List[str]
    warnings: List[str]
    chart_data: Dict[str, Any]

# --- Scenario Challenger ---
class ScenarioAssumption(BaseModel):
    name: str
    value: float
    unit: str
    year: Optional[int] = None
    source: Optional[str] = None

class ScenarioInput(BaseModel):
    scenario_name: str
    model_type: Literal["AFRY", "Aurora", "Internal", "Other"] = "Internal"
    country: str = "FR"
    horizon: int = 2030
    assumptions: List[ScenarioAssumption]
    prices: Optional[List[float]] = None  # Optional price forecast

class ScenarioIssue(BaseModel):
    category: Literal["unusual_hypothesis", "historical_deviation", "economic_inconsistency", "model_specific"]
    severity: Literal["info", "warning", "critical"]
    assumption: str
    message: str
    benchmark: Optional[str] = None
    recommendation: str

class ScenarioChallengerResponse(BaseModel):
    scenario_name: str
    model_type: str
    overall_score: float
    issues: List[ScenarioIssue]
    summary: str
    peer_comparison: Dict[str, Any]
    risk_opportunities: List[str]

# --- Meeting Copilot ---
class MeetingRequest(BaseModel):
    meeting_type: Literal["AFRY Review", "Aurora Review", "COMEX", "Trading", "Strategy", "Modeling", "Client"] = "AFRY Review"
    topic: str
    participants: Optional[List[str]] = None
    duration_min: int = 60
    context: Optional[str] = None
    previous_notes: Optional[str] = None

class MeetingResponse(BaseModel):
    agenda: List[Dict[str, str]]
    key_questions: List[str]
    preparation_checklist: List[str]
    risks_to_raise: List[str]
    data_to_prepare: List[str]
    executive_summary: str

class MinutesRequest(BaseModel):
    meeting_type: str
    raw_notes: str
    participants: Optional[List[str]] = None

class MinutesResponse(BaseModel):
    summary: str
    decisions: List[str]
    actions: List[Dict[str, str]]
    open_questions: List[str]
    next_steps: List[str]
    formatted_minutes: str

# --- Presentation ---
class SlideContent(BaseModel):
    title: str
    bullets: Optional[List[str]] = None
    chart_type: Optional[str] = None
    notes: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class PresentationRequest(BaseModel):
    presentation_type: Literal["Management", "COMEX", "AFRY Support", "Executive Note", "Market Update"] = "Management"
    title: str
    subtitle: Optional[str] = None
    slides: List[SlideContent]
    author: str = "Power Market Intelligence Agent"
    country: str = "FR"
    include_toc: bool = True

class PresentationResponse(BaseModel):
    pptx_path: str
    docx_path: Optional[str] = None
    pdf_path: Optional[str] = None
    slide_count: int
    message: str

# --- Knowledge Base ---
class KnowledgeQuery(BaseModel):
    query: str
    category: Optional[str] = None
    top_k: int = 5

class KnowledgeResult(BaseModel):
    title: str
    content: str
    category: str
    relevance_score: float
    source_path: str
    tags: List[str]

class KnowledgeResponse(BaseModel):
    query: str
    results: List[KnowledgeResult]
    synthesized_answer: str
    related_questions: List[str]

# --- Market Data ---
class MarketDataRequest(BaseModel):
    country: str = "FR"
    start_date: str
    end_date: str
    data_type: Literal["day_ahead_prices", "wind", "solar", "load", "generation"] = "day_ahead_prices"

class MarketDataResponse(BaseModel):
    country: str
    data_type: str
    data: List[Dict[str, Any]]
    source: str
    cached: bool = False
