from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MonitoringIssue:
    id: int
    issue_identifier: str
    monitoring_run_id: int
    severity: str
    pattern: str
    description: str
    recommended_action: str
    event_timestamp: Optional[datetime] = None
    related_article_number: Optional[str] = None
    related_article_url: Optional[str] = None
