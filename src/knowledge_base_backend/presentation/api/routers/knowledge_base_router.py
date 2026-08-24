from fastapi import APIRouter, Depends, Query
from typing import Optional
from dependency_injector.wiring import inject, Provide
from src.knowledge_base_backend.presentation.api.schemas.article_schemas import KnowledgeBaseArticlePageResponse, KnowledgeBaseArticleDetailResponse
from src.knowledge_base_backend.application.use_cases.list_knowledge_base_articles import ListKnowledgeBaseArticlesUseCase
from src.knowledge_base_backend.application.use_cases.get_knowledge_base_article import GetKnowledgeBaseArticleUseCase
from src.knowledge_base_backend.domain.value_objects.article_search_criteria import ArticleSearchCriteria
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import get_current_user_token
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError

router = APIRouter(prefix="/kb/articles", tags=["Knowledge Base"])

@router.get("", response_model=KnowledgeBaseArticlePageResponse)
@inject
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    search: Optional[str] = None,
    instrument: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_direction: Optional[str] = None,
    token: str = Depends(get_current_user_token),
    use_case: ListKnowledgeBaseArticlesUseCase = Depends(Provide[ApplicationContainer.list_knowledge_base_articles_use_case])
):
    if page_size > 100:
        raise ValidationError("Page size cannot exceed 100")
        
    criteria = ArticleSearchCriteria(
        search_query=search,
        instrument_name=instrument,
        sort_by=sort_by,
        sort_direction=sort_direction
    )
    pagination = PaginationRequest(page=page, page_size=page_size)
    
    result = await use_case.execute(criteria, pagination)
    
    return KnowledgeBaseArticlePageResponse(
        items=[
            {
                "id": str(item.id),
                "database_id": item.database_id,
                "article_number": item.article_number,
                "title": item.title,
                "description": item.description,
                "url": item.url,
                "instruments": item.instruments,
                "last_updated": item.last_updated
            } for item in result.items
        ],
        pagination={
            "current_page": result.current_page,
            "page_size": result.page_size,
            "total_items": result.total_items,
            "total_pages": result.total_pages,
            "has_next_page": result.has_next_page,
            "has_previous_page": result.has_previous_page,
            "next_page": result.next_page,
            "previous_page": result.previous_page
        }
    )

@router.get("/{article_identifier}", response_model=KnowledgeBaseArticleDetailResponse)
@inject
async def get_article(
    article_identifier: str,
    token: str = Depends(get_current_user_token),
    use_case: GetKnowledgeBaseArticleUseCase = Depends(Provide[ApplicationContainer.get_knowledge_base_article_use_case])
):
    article = await use_case.execute(article_identifier)
    return KnowledgeBaseArticleDetailResponse(
        id=str(article.id),
        database_id=article.database_id,
        article_number=article.article_number,
        title=article.title,
        url=article.url,
        searchable_content=article.searchable_content,
        instruments=article.instruments,
        last_updated=article.last_updated
    )
