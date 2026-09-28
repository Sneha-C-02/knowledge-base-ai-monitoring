from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class SupportQueryRequest(BaseModel):
    query: str


class RelatedArticleSchema(BaseModel):
    article_number: str
    title: str
    article_url: str
    snippet: str
    retrieval_reason: str
    relevance_score: float


class SupportQueryResponseSchema(BaseModel):
    answer: str
    related_articles: List[RelatedArticleSchema]


# --- Redesigned Reactive Support Schemas ---

class MatchingMajorEventSchema(BaseModel):
    timestamp: str
    event_type: str
    description: str
    match_reason: str
    line_number: int
    log_file: str


class SystemChangeComparisonSchema(BaseModel):
    aspect: str
    before_incident: str
    after_incident: str
    change_summary: str


class GroundingEvidenceSchema(BaseModel):
    log_file: str
    line_number: int
    snippet: str
    relevance_reason: str


class IncidentInvestigationResponseSchema(BaseModel):
    found: bool
    problem_description: str
    log_file: Optional[str] = None
    line_number: Optional[int] = None
    matched_line: Optional[str] = None
    matched_timestamp: Optional[str] = None
    severity: Optional[str] = None
    pre_incident_summary: str
    pre_incident_pattern: str
    pre_incident_events: List[Dict[str, Any]] = []
    major_events: List[MatchingMajorEventSchema] = []
    system_changes: List[SystemChangeComparisonSchema] = []
    grounding_citations: List[GroundingEvidenceSchema] = []
    confidence_score: float
    suggested_search_query: str
    anti_hallucination_verified: bool
    files_scanned: int
    lines_scanned: int


class KbSolutionRequestSchema(BaseModel):
    query: str
    matched_log_file: Optional[str] = None
    line_number: Optional[int] = None
    incident_pattern: Optional[str] = None
    instrument_name: Optional[str] = None


class KbSolutionResponseSchema(BaseModel):
    answer: str
    related_articles: List[RelatedArticleSchema]


class SupportFeedbackRequestSchema(BaseModel):
    problem_description: str
    is_correct: bool
    log_file: Optional[str] = None
    line_number: Optional[int] = None
    detected_pattern: Optional[str] = None
    feedback_notes: Optional[str] = None


class SupportFeedbackResponseSchema(BaseModel):
    status: str
    message: str
    feedback_id: int
    is_correct: bool
    created_at: Optional[str] = None
