from pydantic import BaseModel
from typing import List, Optional

class FileInfoSchema(BaseModel):
    size: str
    last_modified: str

class MonitoringIssueSchema(BaseModel):
    id: str
    severity: str
    timestamp: Optional[str]
    pattern: str
    description: str
    recommended_action: str
    related_article: Optional[str]
    related_article_url: Optional[str]

class MonitoringEventSchema(BaseModel):
    timestamp: str
    level: str
    message: str

class MonitoringAnalysisResponse(BaseModel):
    status: str
    file_status: str
    file_info: FileInfoSchema
    issues: List[MonitoringIssueSchema]
    recent_events: List[MonitoringEventSchema]
