from dataclasses import dataclass
from typing import Optional

@dataclass
class SupportQueryResponse:
    answer: str
    related_article: Optional[str]
    related_article_url: Optional[str]
    confidence_score: float
