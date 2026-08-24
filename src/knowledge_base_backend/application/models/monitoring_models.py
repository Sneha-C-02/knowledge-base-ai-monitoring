from dataclasses import dataclass
from typing import List, Optional

@dataclass
class FileInfo:
    size: str
    last_modified: str

@dataclass
class MonitoringIssueDto:
    id: str
    severity: str
    timestamp: Optional[str]
    pattern: str
    description: str
    recommended_action: str
    related_article: Optional[str]
    related_article_url: Optional[str]

@dataclass
class MonitoringEventDto:
    timestamp: str
    level: str
    message: str

@dataclass
class MonitoringAnalysisResult:
    status: str
    file_status: str
    file_info: FileInfo
    issues: List[MonitoringIssueDto]
    recent_events: List[MonitoringEventDto]
