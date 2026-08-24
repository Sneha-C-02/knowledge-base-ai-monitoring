from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class MonitoringIssueSearchContext:
    normalized_issue_description: str
    error_patterns: List[str] = field(default_factory=list)
    event_levels: List[str] = field(default_factory=list)
    source_file_identifiers: List[str] = field(default_factory=list)
    instrument_name: Optional[str] = None
