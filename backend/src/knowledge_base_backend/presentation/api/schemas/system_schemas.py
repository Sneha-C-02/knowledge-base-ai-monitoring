from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
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
    severity: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SystemActivityPageResponse(BaseModel):
    items: List[SystemActivitySchema]
    pagination: PaginationMetadataSchema
    
class SystemNotificationSchema(BaseModel):
    id: str
    title: str
    message: str
    type: str
    read: bool
    timestamp: datetime.datetime
    
class SystemNotificationPageResponse(BaseModel):
    items: List[SystemNotificationSchema]
    pagination: PaginationMetadataSchema

class CreateActivityRequest(BaseModel):
    type: str = Field(..., description="The type of the activity")
    message: str = Field(..., description="The message detailing the activity")
    severity: str = Field("INFO", description="The severity of the activity")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional structured information")
