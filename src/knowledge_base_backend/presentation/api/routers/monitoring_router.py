from fastapi import APIRouter, Depends, UploadFile, File
from typing import List
from dependency_injector.wiring import inject, Provide
from src.knowledge_base_backend.presentation.api.schemas.monitoring_schemas import MonitoringAnalysisResponse
from src.knowledge_base_backend.application.use_cases.analyze_uploaded_logs import AnalyzeUploadedLogsUseCase
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import get_current_user_token

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@router.post("/analyze", response_model=MonitoringAnalysisResponse)
@inject
async def analyze_logs(
    logs: List[UploadFile] = File(...),
    token: str = Depends(get_current_user_token),
    use_case: AnalyzeUploadedLogsUseCase = Depends(Provide[ApplicationContainer.analyze_uploaded_logs_use_case])
):
    files = [(log.filename, log.file) for log in logs]
    result = await use_case.execute(files)
    
    return MonitoringAnalysisResponse(
        status=result.status,
        file_status=result.file_status,
        file_info={"size": result.file_info.size, "last_modified": result.file_info.last_modified},
        issues=[
            {
                "id": iss.id,
                "severity": iss.severity,
                "timestamp": iss.timestamp,
                "pattern": iss.pattern,
                "description": iss.description,
                "recommended_action": iss.recommended_action,
                "related_article": iss.related_article,
                "related_article_url": iss.related_article_url
            } for iss in result.issues
        ],
        recent_events=[
            {
                "timestamp": ev.timestamp,
                "level": ev.level,
                "message": ev.message
            } for ev in result.recent_events
        ]
    )
