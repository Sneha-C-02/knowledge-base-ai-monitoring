from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class IncidentFinding:
    log_file: str
    line_number: int
    matched_line: str
    matched_timestamp: Optional[str] = None
    severity: str = "ERROR"
    match_score: float = 0.0


@dataclass
class MatchingMajorEvent:
    timestamp: str
    event_type: str
    description: str
    match_reason: str
    line_number: int
    log_file: str


@dataclass
class SystemChangeComparison:
    aspect: str
    before_incident: str
    after_incident: str
    change_summary: str


@dataclass
class GroundingEvidence:
    log_file: str
    line_number: int
    snippet: str
    relevance_reason: str


@dataclass
class IncidentInvestigationResult:
    found: bool
    problem_description: str
    log_file: Optional[str] = None
    line_number: Optional[int] = None
    matched_line: Optional[str] = None
    matched_timestamp: Optional[str] = None
    severity: Optional[str] = None
    pre_incident_summary: str = ""
    pre_incident_pattern: str = ""
    pre_incident_events: List[Dict[str, Any]] = field(default_factory=list)
    major_events: List[MatchingMajorEvent] = field(default_factory=list)
    system_changes: List[SystemChangeComparison] = field(default_factory=list)
    grounding_citations: List[GroundingEvidence] = field(default_factory=list)
    confidence_score: float = 0.0
    suggested_search_query: str = ""
    anti_hallucination_verified: bool = True
    files_scanned: int = 0
    lines_scanned: int = 0


@dataclass
class SupportFeedback:
    id: int
    problem_description: str
    is_correct: bool
    log_file: Optional[str] = None
    line_number: Optional[int] = None
    detected_pattern: Optional[str] = None
    feedback_notes: Optional[str] = None
    created_at: Optional[datetime] = None
