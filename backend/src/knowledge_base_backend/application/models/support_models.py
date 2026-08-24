from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class RelatedArticleDto:
    article_number: str
    title: str
    article_url: str
    snippet: str
    retrieval_reason: str
    relevance_score: float

@dataclass
class SupportQueryResponse:
    answer: str
    related_articles: List[RelatedArticleDto] = field(default_factory=list)
