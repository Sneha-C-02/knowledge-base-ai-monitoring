from dataclasses import dataclass
from typing import List
from src.knowledge_base_backend.domain.entities.knowledge_base_article import KnowledgeBaseArticle

@dataclass(frozen=True)
class RelevantArticleMatch:
    article: KnowledgeBaseArticle
    matched_instruments: List[str]
    full_text_score: float
    vector_similarity_score: float
    combined_relevance_score: float
    retrieval_method: str
