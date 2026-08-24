from pydantic import BaseModel, Field
from typing import List, Optional
from src.knowledge_base_backend.presentation.api.schemas.shared_schemas import PaginationMetadataSchema
import datetime

class KnowledgeBaseArticleSummarySchema(BaseModel):
    id: str
    database_id: int
    article_number: str
    title: str
    description: str
    url: str
    instruments: List[str]
    last_updated: Optional[datetime.datetime]

class KnowledgeBaseArticlePageResponse(BaseModel):
    items: List[KnowledgeBaseArticleSummarySchema]
    pagination: PaginationMetadataSchema

class KnowledgeBaseArticleDetailResponse(BaseModel):
    id: str
    database_id: int
    article_number: str
    title: str
    url: str
    searchable_content: str
    instruments: List[str]
    last_updated: Optional[datetime.datetime]
