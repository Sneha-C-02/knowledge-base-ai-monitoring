from typing import List, Optional

from pydantic import BaseModel, Field


class InstrumentSchema(BaseModel):
    id: int
    name: str


class DashboardSummaryBulletSchema(BaseModel):
    text: str
    severity: Optional[str] = None
    confidence_score: Optional[int] = None
    possible_root_causes: Optional[List[str]] = None
    pattern_name: Optional[str] = None


class KeywordArticleSchema(BaseModel):
    id: Optional[str] = None
    database_id: Optional[int] = None
    article_number: str
    title: str
    url: Optional[str] = None
    summary: Optional[str] = None
    relevance_score: Optional[float] = None
    retrieval_reason: Optional[str] = None


class DashboardFindingSchema(BaseModel):
    filename: str
    line_number: int
    snippet: str
    severity: str
    explanation: str
    detected_by: str
    kb_article: Optional[KeywordArticleSchema] = None
    simple_summary: Optional[str] = None
    pre_incident_summary: Optional[str] = None
    pre_incident_pattern: Optional[str] = None
    pre_incident_events: Optional[List[dict]] = None
    major_events: Optional[List[dict]] = None
    system_changes: Optional[List[dict]] = None
    grounding_citations: Optional[List[dict]] = None
    confidence_score: Optional[float] = None
    suggested_search_query: Optional[str] = None


class MonitoredFileSchema(BaseModel):
    filename: str
    status: str = "MONITORING"
    total_lines_analyzed: int = 0
    updated_at: Optional[str] = None


class LogDashboardResponse(BaseModel):
    instrument_id: int
    instrument_name: str
    critical_incidents: int
    warnings: int
    errors: int
    healthy_apps: int
    overall_status: str
    files_analyzed: int
    daily_summary_bullets: List[DashboardSummaryBulletSchema]
    analysis_status: str = "FULL_AI_ANALYSIS"
    total_chunks: int = 1
    successful_ai_chunks: int = 1
    fallback_chunks: int = 0
    failed_chunks: int = 0
    original_line_count: Optional[int] = None
    analyzed_line_count: Optional[int] = None
    was_log_reduced: bool = False
    coverage_mode: str = "exhaustive"
    complete_findings: List[DashboardFindingSchema] = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    monitoring_status: str = "MONITORING"
    monitored_files: List[MonitoredFileSchema] = Field(default_factory=list)


class InstrumentMonitoringStatusResponse(BaseModel):
    instrument_id: int
    instrument_name: Optional[str] = None
    is_active: bool = True
    status: str = "MONITORING"
    monitored_files: List[MonitoredFileSchema] = Field(default_factory=list)


class AppendLogLinesRequest(BaseModel):
    instrument_id: int
    filename: str
    lines: str


class AppendLogLinesResponse(BaseModel):
    instrument_id: int
    filename: str
    lines_appended: int
    total_lines: int
    status: str = "MONITORING"




class KeywordFindingSchema(BaseModel):
    keyword: str
    filename: str
    line_number: int
    matched_text: str
    context: List[str]
    context_start_line: Optional[int] = None
    is_error: bool
    error_type: Optional[str] = None
    problem_summary: Optional[str] = None
    search_query: Optional[str] = None
    rationale: str
    confidence_score: int
    classification_source: str
    recommended_action: Optional[str] = None
    kb_article: Optional[KeywordArticleSchema] = None


class KeywordSearchResponse(BaseModel):
    keywords: List[str]
    total_matches: int
    findings: List[KeywordFindingSchema]


class KeywordSuggestionSchema(BaseModel):
    keyword: str
    severity: str
    occurrence_count: int


class KeywordSuggestionsResponse(BaseModel):
    suggestions: List[KeywordSuggestionSchema]


class InstrumentMemoryEntrySchema(BaseModel):
    id: int
    instrument_id: int
    instrument_name: str
    analysis_timestamp: str
    log_filename: str
    critical_incidents: int
    warnings: int
    errors: int
    healthy_apps: int
    ai_summary: str


class InstrumentMemoryResponse(BaseModel):
    instrument_id: int
    instrument_name: str
    total_analyses: int
    history: List[InstrumentMemoryEntrySchema]


class AiLearningFeedbackSubmitSchema(BaseModel):
    pattern_number: str
    ai_recommendation: str
    actual_action: str
    result: bool
    helpful_points: Optional[str] = None


class AiLearningFeedbackResponseSchema(BaseModel):
    id: int
    pattern_number: str
    ai_recommendation: str
    actual_action: str
    result: bool
    helpful_points: Optional[str]
    created_at: str


class FindingKbSearchRequest(BaseModel):
    snippet: str
    explanation: Optional[str] = None
    filename: Optional[str] = None
    line_number: Optional[int] = None
    search_query: Optional[str] = None
    instrument_name: Optional[str] = None


class FindingKbSearchResponse(BaseModel):
    kb_article: Optional[KeywordArticleSchema] = None
    search_query: str
    found: bool


class DiscoveredKeywordSchema(BaseModel):
    keyword: str
    severity: str
    failure_indicator: str
    occurrence_count: int
    sample_line: str
    sample_line_number: int
    sample_file: str
    confidence_score: float


class DiscoverKeywordsResponse(BaseModel):
    keywords: List[DiscoveredKeywordSchema]
    total_discovered: int
    files_scanned: int


class AcceptKeywordRequest(BaseModel):
    keyword: str
    severity: str = "warning"
    failure_indicator: Optional[str] = None
    sample_line: Optional[str] = None
    notes: Optional[str] = None
    instrument_id: Optional[int] = 0


class RejectKeywordRequest(BaseModel):
    keyword: str
    reason: Optional[str] = None


class AcceptedKeywordSchema(BaseModel):
    id: int
    instrument_id: int = 0
    keyword: str
    severity: str
    occurrence_count: int = 1
    failure_indicator: Optional[str] = None
    sample_line: Optional[str] = None
    notes: Optional[str] = None
    status: str = "accepted"
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None


class AcceptedKeywordsListResponse(BaseModel):
    keywords: List[AcceptedKeywordSchema]
    total: int

