from pydantic import BaseModel
from typing import Optional

class SupportQueryRequest(BaseModel):
    query: str

class SupportQueryResponseSchema(BaseModel):
    answer: str
    related_article: Optional[str]
    related_article_url: Optional[str]
    confidence_score: float
