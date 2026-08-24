from pydantic import BaseModel
from typing import Optional, List

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
