import asyncio
import json
from typing import List, Literal, Optional, Tuple
from datetime import datetime


from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

import logging
from src.knowledge_base_backend.application.use_cases.analyze_logs_with_memory import AnalyzeLogsWithMemoryUseCase
from src.knowledge_base_backend.application.use_cases.discover_failure_keywords import DiscoverFailureKeywordsUseCase
from src.knowledge_base_backend.application.use_cases.get_learned_keyword_suggestions import (
    GetLearnedKeywordSuggestionsUseCase,
)
from src.knowledge_base_backend.application.use_cases.search_log_keywords import SearchLogKeywordsUseCase
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.domain.repositories.ai_learning_feedback_repository import (
    AiLearningFeedback,
    AiLearningFeedbackRepository,
)
from src.knowledge_base_backend.domain.repositories.instrument_memory_repository import InstrumentMemoryRepository
from src.knowledge_base_backend.domain.repositories.instrument_repository import InstrumentRepository
from src.knowledge_base_backend.domain.repositories.learned_keyword_repository import LearnedKeywordRepository
from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.infrastructure.events.event_bus import EventBus
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import get_current_user_token
from src.knowledge_base_backend.presentation.api.schemas.dashboard_schemas import (
    AcceptKeywordRequest,
    AcceptedKeywordSchema,
    AcceptedKeywordsListResponse,
    AiLearningFeedbackResponseSchema,
    AiLearningFeedbackSubmitSchema,
    DashboardFindingSchema,
    DashboardSummaryBulletSchema,
    DiscoverKeywordsResponse,
    DiscoveredKeywordSchema,
    FindingKbSearchRequest,
    FindingKbSearchResponse,
    InstrumentMemoryEntrySchema,
    InstrumentMemoryResponse,
    InstrumentSchema,
    KeywordArticleSchema,
    KeywordFindingSchema,
    KeywordSearchResponse,
    KeywordSuggestionSchema,
    KeywordSuggestionsResponse,
    LogDashboardResponse,
    RejectKeywordRequest,
)

logger = logging.getLogger(__name__)


def parse_flexible_date(date_str: str) -> datetime:
    """Parse date string with or without year, supporting Waters log format."""
    clean = date_str.strip()
    current_year = datetime.now().year
    try:
        return datetime.fromisoformat(clean)
    except ValueError:
        pass

    # Formats without year (e.g. MM-DDTHH:MM, MM-DDTHH:MM:SS, MM-DD HH:MM)
    for fmt in (
        "%m-%dT%H:%M:%S",
        "%m-%dT%H:%M",
        "%m-%d %H:%M:%S",
        "%m-%d %H:%M",
        "%m/%d %H:%M:%S",
        "%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(clean, fmt).replace(year=current_year)
        except ValueError:
            pass

    # Waters log style formats without year (e.g. "Oct 20 11:28:57 AM", "Oct 20 11:28")
    for fmt in (
        "%b %d %I:%M:%S %p",
        "%b %d %I:%M %p",
        "%b %d %H:%M:%S",
        "%b %d %H:%M",
        "%B %d %I:%M:%S %p",
        "%B %d %I:%M %p",
        "%B %d %H:%M:%S",
        "%B %d %H:%M",
    ):
        try:
            return datetime.strptime(clean, fmt).replace(year=current_year)
        except ValueError:
            pass

    raise ValueError(f"Unable to parse date string: {date_str}")


router = APIRouter(prefix="/monitoring/dashboard", tags=["Log Dashboard"])


@router.get("/instruments", response_model=List[InstrumentSchema])
@inject
async def list_instruments(
    token: str = Depends(get_current_user_token),
    instrument_repository: InstrumentRepository = Depends(Provide[ApplicationContainer.instrument_repository]),
):
    """
    List all available instruments for the monitoring dropdown.
    """
    instruments = await instrument_repository.get_all()
    return [InstrumentSchema(id=inst.id, name=inst.name) for inst in instruments]


@router.post("/analyze", response_model=LogDashboardResponse)
@inject
async def analyze_logs_with_dashboard(
    logs: List[UploadFile] = File(...),
    analysis_mode: Literal["exhaustive", "fast"] = Form("exhaustive"),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    token: str = Depends(get_current_user_token),
    use_case: AnalyzeLogsWithMemoryUseCase = Depends(Provide[ApplicationContainer.analyze_logs_with_memory_use_case]),
):
    """
    Upload one or more log files for an instrument.

    FIRST UPLOAD: The system reads ALL content, builds a full AI context map,
    and stores the analysis position + context summary.

    RE-UPLOAD: The system detects previously-analyzed lines, analyzes ONLY
    new content using the stored context, and updates the memory.

    Optional date_from / date_to (ISO format) to restrict analysis to a time window.
    """
    files = [(log.filename, log.file) for log in logs]

    # Parse date strings into datetime objects if provided
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = parse_flexible_date(date_from)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid date_from format: {date_from}")
    if date_to:
        try:
            parsed_date_to = parse_flexible_date(date_to)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid date_to format: {date_to}")

    result = await use_case.execute(
        files=files,
        analysis_mode=analysis_mode,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
    )

    return LogDashboardResponse(
        instrument_id=result.instrument_id,
        instrument_name=result.instrument_name,
        critical_incidents=result.critical_incidents,
        warnings=result.warnings,
        errors=result.errors,
        healthy_apps=result.healthy_apps,
        overall_status=result.overall_status,
        files_analyzed=result.files_analyzed,
        daily_summary_bullets=[
            DashboardSummaryBulletSchema(
                text=b.text,
                severity=b.severity,
                confidence_score=b.confidence_score,
                possible_root_causes=b.possible_root_causes,
                pattern_name=b.pattern_name,
            )
            for b in result.daily_summary_bullets
        ],
        analysis_status=result.analysis_status,
        total_chunks=result.total_chunks,
        successful_ai_chunks=result.successful_ai_chunks,
        fallback_chunks=result.fallback_chunks,
        failed_chunks=result.failed_chunks,
        original_line_count=result.original_line_count,
        analyzed_line_count=result.analyzed_line_count,
        was_log_reduced=result.was_log_reduced,
        coverage_mode=result.coverage_mode,
        complete_findings=[
            DashboardFindingSchema(
                filename=f.filename,
                line_number=f.line_number,
                snippet=f.snippet,
                severity=f.severity,
                explanation=f.explanation,
                detected_by=f.detected_by,
                kb_article=f.kb_article,
                simple_summary=getattr(f, "simple_summary", None),
                pre_incident_summary=getattr(f, "pre_incident_summary", None),
                pre_incident_pattern=getattr(f, "pre_incident_pattern", None),
                pre_incident_events=getattr(f, "pre_incident_events", None),
                major_events=getattr(f, "major_events", None),
                system_changes=getattr(f, "system_changes", None),
                grounding_citations=getattr(f, "grounding_citations", None),
                confidence_score=getattr(f, "confidence_score", None),
                suggested_search_query=getattr(f, "suggested_search_query", None),
            )
            for f in result.complete_findings
        ],

        date_from=date_from,
        date_to=date_to,
    )


@router.post("/keyword-search", response_model=KeywordSearchResponse)
@inject
async def search_log_keywords(
    logs: List[UploadFile] = File(...),
    keywords: List[str] = Form(...),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    token: str = Depends(get_current_user_token),
    use_case: SearchLogKeywordsUseCase = Depends(Provide[ApplicationContainer.search_log_keywords_use_case]),
):
    """Read-only search of uploaded logs for explicit user-selected terms, optionally filtered by date range."""
    if not keywords:
        raise HTTPException(status_code=422, detail="Select or enter at least one keyword")

    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = parse_flexible_date(date_from)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid date_from format: {date_from}")
    if date_to:
        try:
            parsed_date_to = parse_flexible_date(date_to)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid date_to format: {date_to}")

    files = [(log.filename or "uploaded.log", await log.read()) for log in logs]
    result = await use_case.execute(
        files=files,
        keywords=keywords,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
    )
    return KeywordSearchResponse(
        keywords=result.keywords,
        total_matches=len(result.findings),
        findings=[KeywordFindingSchema(**finding) for finding in result.findings],
    )


@router.get("/keyword-suggestions", response_model=KeywordSuggestionsResponse)
@inject
async def get_keyword_suggestions(
    instrument_id: Optional[int] = None,
    limit: int = 25,
    token: str = Depends(get_current_user_token),
    use_case: GetLearnedKeywordSuggestionsUseCase = Depends(
        Provide[ApplicationContainer.get_learned_keyword_suggestions_use_case]
    ),
):
    """
    Return the keywords the system has learned from error/warning lines
    observed in previously analyzed logs, ranked by how often each term has
    been seen. Pass instrument_id to bias results toward one instrument's
    own history (global terms are always included as a fallback).
    """
    suggestions = await use_case.execute(instrument_id=instrument_id or 0, limit=limit)
    return KeywordSuggestionsResponse(
        suggestions=[
            KeywordSuggestionSchema(keyword=s.keyword, severity=s.severity, occurrence_count=s.occurrence_count)
            for s in suggestions
        ]
    )


@router.get("/memory/{instrument_id}", response_model=InstrumentMemoryResponse)
@inject
async def get_instrument_memory(
    instrument_id: int,
    token: str = Depends(get_current_user_token),
    memory_repository: InstrumentMemoryRepository = Depends(Provide[ApplicationContainer.instrument_memory_repository]),
):
    """
    Retrieve the full analysis history (memory) for a specific instrument.
    Shows all past dashboard analyses, most recent first.
    """
    entries = await memory_repository.get_memory_for_instrument(instrument_id)

    instrument_name = entries[0].instrument_name if entries else "Unknown"

    return InstrumentMemoryResponse(
        instrument_id=instrument_id,
        instrument_name=instrument_name,
        total_analyses=len(entries),
        history=[
            InstrumentMemoryEntrySchema(
                id=e.id,
                instrument_id=e.instrument_id,
                instrument_name=e.instrument_name,
                analysis_timestamp=e.analysis_timestamp.isoformat(),
                log_filename=e.log_filename,
                critical_incidents=e.critical_incidents,
                warnings=e.warnings,
                errors=e.errors,
                healthy_apps=e.healthy_apps,
                ai_summary=e.ai_summary,
            )
            for e in entries
        ],
    )


@router.get("/stream/{instrument_id}")
@inject
async def stream_dashboard_updates(
    instrument_id: int,
    # Note: typically we would depend on token here, but SSE from browsers sometimes
    # doesn't easily send auth headers natively without query params.
    # Assuming basic access for now, or token passed in query.
    event_bus: EventBus = Depends(Provide[ApplicationContainer.event_bus]),
):
    """
    Server-Sent Events (SSE) endpoint that streams dashboard updates live
    when the continuous monitoring service detects new lines in log files.
    """

    async def event_generator():
        topic = str(instrument_id)
        queue = await event_bus.subscribe(topic)
        try:
            while True:
                # Wait for a new dashboard result from the continuous monitoring service
                dashboard_result = await queue.get()

                # Format the result as a dict matching LogDashboardResponse schema
                data = {
                    "instrument_id": dashboard_result.instrument_id,
                    "instrument_name": dashboard_result.instrument_name,
                    "critical_incidents": dashboard_result.critical_incidents,
                    "warnings": dashboard_result.warnings,
                    "errors": dashboard_result.errors,
                    "healthy_apps": dashboard_result.healthy_apps,
                    "overall_status": dashboard_result.overall_status,
                    "files_analyzed": dashboard_result.files_analyzed,
                    "daily_summary_bullets": [
                        {
                            "text": b.text,
                            "severity": b.severity,
                            "confidence_score": b.confidence_score,
                            "possible_root_causes": b.possible_root_causes,
                            "pattern_name": b.pattern_name,
                        }
                        for b in dashboard_result.daily_summary_bullets
                    ],
                    "analysis_status": dashboard_result.analysis_status,
                    "total_chunks": getattr(dashboard_result, "total_chunks", 1),
                    "successful_ai_chunks": getattr(dashboard_result, "successful_ai_chunks", 1),
                    "fallback_chunks": getattr(dashboard_result, "fallback_chunks", 0),
                    "failed_chunks": getattr(dashboard_result, "failed_chunks", 0),
                    "original_line_count": getattr(dashboard_result, "original_line_count", None),
                    "analyzed_line_count": getattr(dashboard_result, "analyzed_line_count", None),
                    "was_log_reduced": getattr(dashboard_result, "was_log_reduced", False),
                    "coverage_mode": getattr(dashboard_result, "coverage_mode", "exhaustive"),
                    "complete_findings": [
                        {
                            "filename": finding.filename,
                            "line_number": finding.line_number,
                            "snippet": finding.snippet,
                            "severity": finding.severity,
                            "explanation": finding.explanation,
                            "detected_by": finding.detected_by,
                            "kb_article": getattr(finding, "kb_article", None),
                            "simple_summary": getattr(finding, "simple_summary", None),
                            "pre_incident_summary": getattr(finding, "pre_incident_summary", None),
                            "pre_incident_pattern": getattr(finding, "pre_incident_pattern", None),
                            "pre_incident_events": getattr(finding, "pre_incident_events", None),
                            "major_events": getattr(finding, "major_events", None),
                            "system_changes": getattr(finding, "system_changes", None),
                            "grounding_citations": getattr(finding, "grounding_citations", None),
                            "confidence_score": getattr(finding, "confidence_score", None),
                            "suggested_search_query": getattr(finding, "suggested_search_query", None),
                        }
                        for finding in getattr(dashboard_result, "complete_findings", [])
                    ],

                }

                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            # Client disconnected
            pass
        finally:
            await event_bus.unsubscribe(topic, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/feedback", response_model=AiLearningFeedbackResponseSchema)
@inject
async def submit_ai_learning_feedback(
    payload: AiLearningFeedbackSubmitSchema,
    token: str = Depends(get_current_user_token),
    feedback_repository: AiLearningFeedbackRepository = Depends(
        Provide[ApplicationContainer.ai_learning_feedback_repository]
    ),
):
    """
    Submit user verification feedback for an AI log analysis result.
    This data is saved to be used as few-shot training examples for the AI.
    """
    feedback = AiLearningFeedback(
        id=0,
        pattern_number=payload.pattern_number,
        ai_recommendation=payload.ai_recommendation,
        actual_action=payload.actual_action,
        result=payload.result,
        helpful_points=payload.helpful_points,
    )
    saved = await feedback_repository.save(feedback)

    return AiLearningFeedbackResponseSchema(
        id=saved.id,
        pattern_number=saved.pattern_number,
        ai_recommendation=saved.ai_recommendation,
        actual_action=saved.actual_action,
        result=saved.result,
        helpful_points=saved.helpful_points,
        created_at=saved.created_at.isoformat() if saved.created_at else "",
    )


@router.post("/search-finding-kb", response_model=FindingKbSearchResponse)
@inject
async def search_finding_kb(
    payload: FindingKbSearchRequest,
    token: str = Depends(get_current_user_token),
    retrieval_service: HybridArticleRetrievalService = Depends(
        Provide[ApplicationContainer.hybrid_retrieval_service]
    ),
):
    """
    On-demand search for Waters Knowledge Base articles matching a specific detected finding.
    Triggered only when the user explicitly clicks the 'Search Knowledge Base Article' button.
    """
    candidates = []
    if payload.search_query and payload.search_query.strip():
        candidates.append(payload.search_query.strip())
    if payload.explanation and payload.explanation.strip() and payload.explanation.strip() not in candidates:
        candidates.append(payload.explanation.strip())
    if payload.snippet and payload.snippet.strip() and payload.snippet.strip() not in candidates:
        candidates.append(payload.snippet.strip())

    if not candidates:
        return FindingKbSearchResponse(kb_article=None, search_query="", found=False)

    search_query = candidates[0]
    for query in candidates:
        try:
            matches = await retrieval_service.retrieve_relevant_articles(
                query, payload.instrument_name, limit=1
            )
            if matches:
                top = matches[0]
                content = top.article.searchable_content or ""
                snippet = content[:280].strip() + ("..." if len(content) > 280 else "")
                article = KeywordArticleSchema(
                    id=str(top.article.id),
                    database_id=top.article.database_id,
                    article_number=top.article.article_number,
                    title=top.article.title,
                    url=top.article.url or f"/article/{top.article.article_number}",
                    summary=snippet,
                    relevance_score=round(float(top.combined_relevance_score), 2),
                    retrieval_reason=top.retrieval_reason or "Matched finding from log analysis",
                )
                return FindingKbSearchResponse(kb_article=article, search_query=query, found=True)
        except Exception as e:
            logger.debug(f"KB search failed for query '{query}': {e}")
            continue

    return FindingKbSearchResponse(kb_article=None, search_query=search_query, found=False)


@router.post("/keywords/discover", response_model=DiscoverKeywordsResponse)
@inject
async def discover_failure_keywords(
    files: List[UploadFile] = File(...),
    token: str = Depends(get_current_user_token),
    use_case: DiscoverFailureKeywordsUseCase = Depends(
        Provide[ApplicationContainer.discover_failure_keywords_use_case]
    ),
):
    """
    Scan uploaded log file(s) or folder content to automatically discover candidate keywords
    and phrases that indicate instrument failures, faults, and anomalies for human review.
    """
    if not files:
        raise HTTPException(status_code=422, detail="No log files provided for keyword discovery")

    file_tuples: List[Tuple[str, str]] = []
    for f in files:
        raw_bytes = await f.read()
        text_content = raw_bytes.decode("utf-8", errors="replace")
        file_tuples.append((f.filename or "uploaded.log", text_content))

    return await use_case.execute(file_tuples)


@router.post("/keywords/accept", response_model=AcceptedKeywordSchema)
@inject
async def accept_discovered_keyword(
    payload: AcceptKeywordRequest,
    token: str = Depends(get_current_user_token),
    repository: LearnedKeywordRepository = Depends(
        Provide[ApplicationContainer.learned_keyword_repository]
    ),
):
    """
    Human acceptance of a discovered failure keyword with optional edits to severity, name, or notes.
    Persists the keyword into the learned keywords repository.
    """
    if not payload.keyword or not payload.keyword.strip():
        raise HTTPException(status_code=422, detail="Keyword cannot be empty")

    saved = await repository.accept_keyword(
        keyword=payload.keyword,
        severity=payload.severity or "warning",
        instrument_id=payload.instrument_id or 0,
        failure_indicator=payload.failure_indicator,
        sample_line=payload.sample_line,
        notes=payload.notes,
    )

    return AcceptedKeywordSchema(
        id=saved.id,
        instrument_id=saved.instrument_id,
        keyword=saved.keyword,
        severity=saved.severity,
        occurrence_count=saved.occurrence_count,
        failure_indicator=saved.failure_indicator,
        sample_line=saved.sample_line,
        notes=saved.notes,
        status=saved.status,
        first_seen_at=saved.first_seen_at.isoformat() if saved.first_seen_at else None,
        last_seen_at=saved.last_seen_at.isoformat() if saved.last_seen_at else None,
    )


@router.post("/keywords/reject")
@inject
async def reject_discovered_keyword(
    payload: RejectKeywordRequest,
    token: str = Depends(get_current_user_token),
    repository: LearnedKeywordRepository = Depends(
        Provide[ApplicationContainer.learned_keyword_repository]
    ),
):
    """
    Human rejection of a candidate keyword. Marks it as rejected so it won't be suggested.
    """
    if not payload.keyword or not payload.keyword.strip():
        raise HTTPException(status_code=422, detail="Keyword cannot be empty")

    await repository.reject_keyword(payload.keyword)
    return {"status": "rejected", "keyword": payload.keyword}


@router.get("/keywords/accepted", response_model=AcceptedKeywordsListResponse)
@inject
async def list_accepted_keywords(
    instrument_id: Optional[int] = None,
    token: str = Depends(get_current_user_token),
    repository: LearnedKeywordRepository = Depends(
        Provide[ApplicationContainer.learned_keyword_repository]
    ),
):
    """
    List all human-accepted failure keywords in the system.
    """
    keywords = await repository.list_accepted_keywords(instrument_id=instrument_id)
    return AcceptedKeywordsListResponse(
        keywords=[
            AcceptedKeywordSchema(
                id=k.id,
                instrument_id=k.instrument_id,
                keyword=k.keyword,
                severity=k.severity,
                occurrence_count=k.occurrence_count,
                failure_indicator=k.failure_indicator,
                sample_line=k.sample_line,
                notes=k.notes,
                status=k.status,
                first_seen_at=k.first_seen_at.isoformat() if k.first_seen_at else None,
                last_seen_at=k.last_seen_at.isoformat() if k.last_seen_at else None,
            )
            for k in keywords
        ],
        total=len(keywords),
    )


@router.delete("/keywords/accepted/{keyword_id}")
@inject
async def delete_accepted_keyword(
    keyword_id: int,
    token: str = Depends(get_current_user_token),
    repository: LearnedKeywordRepository = Depends(
        Provide[ApplicationContainer.learned_keyword_repository]
    ),
):
    """
    Delete an accepted keyword by ID.
    """
    success = await repository.delete_accepted_keyword(keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="Accepted keyword not found")
    return {"status": "deleted", "id": keyword_id}

