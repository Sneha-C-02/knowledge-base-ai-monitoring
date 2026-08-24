from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from src.knowledge_base_backend.presentation.api.schemas.support_schemas import SupportQueryRequest, SupportQueryResponseSchema, RelatedArticleSchema
from src.knowledge_base_backend.application.use_cases.submit_support_query import SubmitSupportQueryUseCase
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import get_current_user_token

router = APIRouter(prefix="/support", tags=["Support"])

@router.post("/query", response_model=SupportQueryResponseSchema)
@inject
async def submit_query(
    request: SupportQueryRequest,
    token: str = Depends(get_current_user_token),
    use_case: SubmitSupportQueryUseCase = Depends(Provide[ApplicationContainer.submit_support_query_use_case])
):
    result = await use_case.execute(request.query)
    articles = [
        RelatedArticleSchema(
            article_number=a.article_number,
            title=a.title,
            article_url=a.article_url,
            snippet=a.snippet,
            retrieval_reason=a.retrieval_reason,
            relevance_score=a.relevance_score
        ) for a in result.related_articles
    ]
    return SupportQueryResponseSchema(
        answer=result.answer,
        related_articles=articles
    )
