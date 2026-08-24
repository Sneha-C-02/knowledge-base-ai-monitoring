from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from src.knowledge_base_backend.presentation.api.schemas.shared_schemas import PaginationMetadataSchema
import datetime

class DashboardStatisticsResponse(BaseModel):
    supportQueries: int
    activeLogs: int
    detectedIssues: int
    kbArticles: int
    
    model_config = ConfigDict(populate_by_name=True)

class SystemActivitySchema(BaseModel):
    id: str
    type: str
    message: str
    timestamp: datetime.datetime
    user: Optional[str]

class SystemActivityPageResponse(BaseModel):
    items: List[SystemActivitySchema]
    pagination: PaginationMetadataSchema
    
class SystemNotificationSchema(BaseModel):
    id: str
    title: str
    message: str
    type: str
    is_read: bool
    timestamp: datetime.datetime
    
class SystemNotificationPageResponse(BaseModel):
    items: List[SystemNotificationSchema]
    pagination: PaginationMetadataSchema
