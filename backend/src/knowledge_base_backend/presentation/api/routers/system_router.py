from fastapi import APIRouter, Depends, Query
from typing import Optional
from dependency_injector.wiring import inject, Provide
from src.knowledge_base_backend.presentation.api.schemas.system_schemas import DashboardStatisticsResponse, SystemActivityPageResponse, SystemNotificationPageResponse, CreateActivityRequest
from src.knowledge_base_backend.application.use_cases.get_dashboard_statistics import GetDashboardStatisticsUseCase
from src.knowledge_base_backend.application.use_cases.list_activities import ListActivitiesUseCase
from src.knowledge_base_backend.application.use_cases.create_activity import CreateActivityUseCase
from src.knowledge_base_backend.application.use_cases.list_notifications import ListNotificationsUseCase
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import get_current_user_token
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/stats", response_model=DashboardStatisticsResponse)
@inject
async def get_stats(
    token: str = Depends(get_current_user_token),
    use_case: GetDashboardStatisticsUseCase = Depends(Provide[ApplicationContainer.get_dashboard_statistics_use_case])
):
    stats = await use_case.execute()
    return DashboardStatisticsResponse(
        supportQueries=stats.support_queries,
        activeLogs=stats.active_logs,
        detectedIssues=stats.detected_issues,
        kbArticles=stats.kb_articles
    )

@router.get("/activities", response_model=SystemActivityPageResponse)
@inject
async def list_activities(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    activity_type: Optional[str] = None,
    token: str = Depends(get_current_user_token),
    use_case: ListActivitiesUseCase = Depends(Provide[ApplicationContainer.list_activities_use_case])
):
    if page_size > 100:
        raise ValidationError("Page size cannot exceed 100")
        
    pagination = PaginationRequest(page=page, page_size=page_size)
    result = await use_case.execute(pagination, activity_type)
    
    return SystemActivityPageResponse(
        items=[
            {
                "id": act.activity_identifier,
                "type": act.activity_type,
                "message": act.message,
                "timestamp": act.created_at,
                "user": act.username,
                "severity": act.severity,
                "metadata": act.metadata
            } for act in result.items
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

@router.get("/notifications", response_model=SystemNotificationPageResponse)
@inject
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    notification_type: Optional[str] = None,
    is_read: Optional[bool] = None,
    token: str = Depends(get_current_user_token),
    use_case: ListNotificationsUseCase = Depends(Provide[ApplicationContainer.list_notifications_use_case])
):
    if page_size > 100:
        raise ValidationError("Page size cannot exceed 100")
        
    pagination = PaginationRequest(page=page, page_size=page_size)
    result = await use_case.execute(pagination, notification_type, is_read)
    
    return SystemNotificationPageResponse(
        items=[
            {
                "id": notif.notification_identifier,
                "title": notif.title,
                "message": notif.message,
                "type": notif.notification_type,
                "is_read": notif.is_read,
                "timestamp": notif.created_at
            } for notif in result.items
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

@router.post("/activities", status_code=201)
@inject
async def create_activity(
    request: CreateActivityRequest,
    token: str = Depends(get_current_user_token),
    use_case: CreateActivityUseCase = Depends(Provide[ApplicationContainer.create_activity_use_case])
):
    from jose import jwt
    decoded = jwt.get_unverified_claims(token)
    username = decoded.get("sub", "system")
    await use_case.execute(request.type, request.message, username, severity=request.severity, metadata=request.metadata)
    return {"status": "success"}
