from src.knowledge_base_backend.domain.services.grounding_context_builder import GroundingContextBuilder
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from typing import List

class SecureGroundingContextBuilder(GroundingContextBuilder):
    def build_context(self, articles: List[RelevantArticleMatch]) -> str:
        if not articles:
            return "No context available."
            
        context_parts = []
        for i, match in enumerate(articles[:5]):
            article = match.article
            context_parts.append(
                f"Article Number: {article.article_number}\n"
                f"Title: {article.title}\n"
                f"URL: {article.url}\n"
                f"Relevance Score: {match.combined_relevance_score:.3f}\n"
                f"Retrieval Reason: {match.retrieval_reason}\n"
                f"Content: {article.searchable_content[:2000]}\n"
            )
        return "\n---\n".join(context_parts)
