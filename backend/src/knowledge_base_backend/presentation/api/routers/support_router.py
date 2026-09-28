from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form
from dependency_injector.wiring import inject, Provide

from src.knowledge_base_backend.presentation.api.schemas.support_schemas import (
    SupportQueryRequest,
    SupportQueryResponseSchema,
    RelatedArticleSchema,
    IncidentInvestigationResponseSchema,
    MatchingMajorEventSchema,
    SystemChangeComparisonSchema,
    GroundingEvidenceSchema,
    KbSolutionRequestSchema,
    KbSolutionResponseSchema,
    SupportFeedbackRequestSchema,
    SupportFeedbackResponseSchema,
)
from src.knowledge_base_backend.application.use_cases.submit_support_query import SubmitSupportQueryUseCase
from src.knowledge_base_backend.application.use_cases.investigate_log_incident import InvestigateLogIncidentUseCase
from src.knowledge_base_backend.application.use_cases.search_kb_for_incident import SearchKbForIncidentUseCase
from src.knowledge_base_backend.application.use_cases.submit_support_feedback import SubmitSupportFeedbackUseCase
from src.knowledge_base_backend.domain.repositories.support_feedback_repository import SupportFeedbackRepository
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import get_current_user_token

router = APIRouter(prefix="/support", tags=["Support"])


@router.post("/investigate", response_model=IncidentInvestigationResponseSchema)
@inject
async def investigate_incident(
    problem_description: str = Form(...),
    logs: List[UploadFile] = File(default=[]),
    token: str = Depends(get_current_user_token),
    use_case: InvestigateLogIncidentUseCase = Depends(
        Provide[ApplicationContainer.investigate_log_incident_use_case]
    ),
):
    """
    Reactive Support Log Incident Investigation:
    1. Pinpoints which log file and line number the user's problem is present in.
    2. Identifies and summarizes the pattern or incident in the log before the issue.
    3. Mentions major system events across all logs ONLY if they match the problem.
    4. Detects changes in system state after the incident compared to before the incident.
    5. Applies anti-hallucination verification against verbatim log lines.
    6. Speed and token optimized (sub-second bounded window processing).
    """
    if not logs:
        raise ValidationError("No log files or folder uploaded. At least one log file or folder is required for incident investigation.")

    file_tuples = []
    for log in logs:
        if not log.filename or not log.filename.strip():
            continue
        content = await log.read()
        file_tuples.append((log.filename, content))

    if not file_tuples:
        raise ValidationError("No log files or folder uploaded. At least one log file or folder is required for incident investigation.")

    result = await use_case.execute(
        files=file_tuples,
        problem_description=problem_description,
    )

    return IncidentInvestigationResponseSchema(
        found=result.found,
        problem_description=result.problem_description,
        log_file=result.log_file,
        line_number=result.line_number,
        matched_line=result.matched_line,
        matched_timestamp=result.matched_timestamp,
        severity=result.severity,
        pre_incident_summary=result.pre_incident_summary,
        pre_incident_pattern=result.pre_incident_pattern,
        pre_incident_events=result.pre_incident_events,
        major_events=[
            MatchingMajorEventSchema(
                timestamp=ev.timestamp,
                event_type=ev.event_type,
                description=ev.description,
                match_reason=ev.match_reason,
                line_number=ev.line_number,
                log_file=ev.log_file,
            )
            for ev in result.major_events
        ],
        system_changes=[
            SystemChangeComparisonSchema(
                aspect=c.aspect,
                before_incident=c.before_incident,
                after_incident=c.after_incident,
                change_summary=c.change_summary,
            )
            for c in result.system_changes
        ],
        grounding_citations=[
            GroundingEvidenceSchema(
                log_file=cit.log_file,
                line_number=cit.line_number,
                snippet=cit.snippet,
                relevance_reason=cit.relevance_reason,
            )
            for cit in result.grounding_citations
        ],
        confidence_score=result.confidence_score,
        suggested_search_query=result.suggested_search_query,
        anti_hallucination_verified=result.anti_hallucination_verified,
        files_scanned=result.files_scanned,
        lines_scanned=result.lines_scanned,
    )


@router.post("/kb-solution", response_model=KbSolutionResponseSchema)
@inject
async def search_kb_solution(
    payload: KbSolutionRequestSchema,
    token: str = Depends(get_current_user_token),
    use_case: SearchKbForIncidentUseCase = Depends(
        Provide[ApplicationContainer.search_kb_for_incident_use_case]
    ),
):
    """
    Dedicated endpoint to retrieve Knowledge Base articles for the issue.
    Executed ONLY when the user clicks the 'Search KB Article' button.
    """
    result = await use_case.execute(
        query=payload.query,
        matched_log_file=payload.matched_log_file,
        incident_pattern=payload.incident_pattern,
        instrument_name=payload.instrument_name,
    )

    articles = [
        RelatedArticleSchema(
            article_number=a.article_number,
            title=a.title,
            article_url=a.article_url,
            snippet=a.snippet,
            retrieval_reason=a.retrieval_reason,
            relevance_score=a.relevance_score,
        )
        for a in result.related_articles
    ]

    return KbSolutionResponseSchema(
        answer=result.answer,
        related_articles=articles,
    )


@router.post("/feedback", response_model=SupportFeedbackResponseSchema)
@inject
async def submit_support_feedback(
    payload: SupportFeedbackRequestSchema,
    token: str = Depends(get_current_user_token),
    use_case: SubmitSupportFeedbackUseCase = Depends(
        Provide[ApplicationContainer.submit_support_feedback_use_case]
    ),
):
    """
    Records user feedback (correct or wrong) on the AI incident analysis.
    This response is stored to continuously improve newer searches.
    """
    feedback = await use_case.execute(
        problem_description=payload.problem_description,
        is_correct=payload.is_correct,
        log_file=payload.log_file,
        line_number=payload.line_number,
        detected_pattern=payload.detected_pattern,
        feedback_notes=payload.feedback_notes,
    )

    return SupportFeedbackResponseSchema(
        status="success",
        message="Feedback stored successfully and will improve future searches.",
        feedback_id=feedback.id,
        is_correct=feedback.is_correct,
        created_at=feedback.created_at.isoformat() if feedback.created_at else None,
    )


@router.get("/feedback/recent")
@inject
async def get_recent_feedback(
    limit: int = 20,
    token: str = Depends(get_current_user_token),
    feedback_repo: SupportFeedbackRepository = Depends(
        Provide[ApplicationContainer.support_feedback_repository]
    ),
):
    """
    Retrieves recent feedback items to monitor user verification history.
    """
    items = await feedback_repo.get_recent_feedback(limit=limit)
    return [
        {
            "id": f.id,
            "problem_description": f.problem_description,
            "is_correct": f.is_correct,
            "log_file": f.log_file,
            "line_number": f.line_number,
            "detected_pattern": f.detected_pattern,
            "feedback_notes": f.feedback_notes,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in items
    ]


@router.post("/query", response_model=SupportQueryResponseSchema)
@inject
async def submit_query(
    request: SupportQueryRequest,
    token: str = Depends(get_current_user_token),
    use_case: SubmitSupportQueryUseCase = Depends(
        Provide[ApplicationContainer.submit_support_query_use_case]
    ),
):
    """
    Legacy general reactive support query endpoint.
    Reactive support requires uploaded log files or folder to function.
    """
    raise ValidationError(
        "No log files or folder uploaded. Reactive support and chat require at least one log file or folder for incident investigation."
    )

