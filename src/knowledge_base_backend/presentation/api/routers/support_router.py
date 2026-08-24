from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from src.knowledge_base_backend.presentation.api.schemas.support_schemas import SupportQueryRequest, SupportQueryResponseSchema
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
    return SupportQueryResponseSchema(
        answer=result.answer,
        related_article=result.related_article,
        related_article_url=result.related_article_url,
        confidence_score=result.confidence_score
    )
