from src.knowledge_base_backend.domain.repositories.article_repository import ArticleRepository
from src.knowledge_base_backend.domain.value_objects.article_search_criteria import ArticleSearchCriteria
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.domain.value_objects.pagination_result import PaginationResult
from src.knowledge_base_backend.application.models.article_models import KnowledgeBaseArticleSummary

class ListKnowledgeBaseArticlesUseCase:
    def __init__(self, article_repository: ArticleRepository) -> None:
        self.article_repository = article_repository

    async def execute(
        self, criteria: ArticleSearchCriteria, pagination: PaginationRequest
    ) -> PaginationResult[KnowledgeBaseArticleSummary]:
        result = await self.article_repository.retrieve_paginated_articles(criteria, pagination)
        
        summaries = []
        for article in result.items:
            # Create a safe description from searchable content (max 250 chars)
            desc = " ".join(article.searchable_content.split())
            if len(desc) > 250:
                desc = desc[:247] + "..."
                
            summaries.append(KnowledgeBaseArticleSummary(
                id=article.id,
                database_id=article.database_id,
                article_number=article.article_number,
                title=article.title,
                description=desc,
                url=article.url,
                instruments=article.instruments,
                last_updated=article.last_updated
            ))
            
        return PaginationResult(
            items=summaries,
            current_page=result.current_page,
            page_size=result.page_size,
            total_items=result.total_items,
            total_pages=result.total_pages,
            has_next_page=result.has_next_page,
            has_previous_page=result.has_previous_page,
            next_page=result.next_page,
            previous_page=result.previous_page
        )
