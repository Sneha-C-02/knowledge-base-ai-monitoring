from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List
import json
import asyncio
from dependency_injector.wiring import inject, Provide

from src.knowledge_base_backend.presentation.api.schemas.dashboard_schemas import (
    LogDashboardResponse,
    DashboardSummaryBulletSchema,
    InstrumentMemoryResponse,
    InstrumentMemoryEntrySchema,
    InstrumentSchema
)
from src.knowledge_base_backend.application.use_cases.analyze_logs_with_memory import AnalyzeLogsWithMemoryUseCase
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import get_current_user_token
from src.knowledge_base_backend.domain.repositories.instrument_memory_repository import InstrumentMemoryRepository
from src.knowledge_base_backend.domain.repositories.instrument_repository import InstrumentRepository
from src.knowledge_base_backend.infrastructure.events.event_bus import EventBus


router = APIRouter(prefix="/monitoring/dashboard", tags=["Log Dashboard"])


@router.get("/instruments", response_model=List[InstrumentSchema])
@inject
async def list_instruments(
    token: str = Depends(get_current_user_token),
    instrument_repository: InstrumentRepository = Depends(
        Provide[ApplicationContainer.instrument_repository]
    )
):
    """
    List all available instruments for the monitoring dropdown.
    """
    instruments = await instrument_repository.get_all()
    return [
        InstrumentSchema(id=inst.id, name=inst.name)
        for inst in instruments
    ]


@router.post("/analyze", response_model=LogDashboardResponse)
@inject
async def analyze_logs_with_dashboard(
    logs: List[UploadFile] = File(...),
    token: str = Depends(get_current_user_token),
    use_case: AnalyzeLogsWithMemoryUseCase = Depends(
        Provide[ApplicationContainer.analyze_logs_with_memory_use_case]
    )
):
    """
    Upload one or more log files for an instrument.
    
    FIRST UPLOAD: The system reads ALL content, builds a full AI context map,
    and stores the analysis position + context summary.
    
    RE-UPLOAD: The system detects previously-analyzed lines, analyzes ONLY
    new content using the stored context, and updates the memory.
    """
    files = [(log.filename, log.file) for log in logs]
    result = await use_case.execute(files=files)

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
            DashboardSummaryBulletSchema(text=b.text, severity=b.severity)
            for b in result.daily_summary_bullets
        ],
        analysis_status=result.analysis_status,
        total_chunks=result.total_chunks,
        successful_ai_chunks=result.successful_ai_chunks,
        fallback_chunks=result.fallback_chunks,
        failed_chunks=result.failed_chunks,
        original_line_count=result.original_line_count,
        analyzed_line_count=result.analyzed_line_count,
        was_log_reduced=result.was_log_reduced
    )


@router.get("/memory/{instrument_id}", response_model=InstrumentMemoryResponse)
@inject
async def get_instrument_memory(
    instrument_id: int,
    token: str = Depends(get_current_user_token),
    memory_repository: InstrumentMemoryRepository = Depends(
        Provide[ApplicationContainer.instrument_memory_repository]
    )
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
                ai_summary=e.ai_summary
            )
            for e in entries
        ]
    )

@router.get("/stream/{instrument_id}")
@inject
async def stream_dashboard_updates(
    instrument_id: int,
    # Note: typically we would depend on token here, but SSE from browsers sometimes 
    # doesn't easily send auth headers natively without query params.
    # Assuming basic access for now, or token passed in query.
    event_bus: EventBus = Depends(Provide[ApplicationContainer.event_bus])
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
                        {"text": b.text, "severity": b.severity}
                        for b in dashboard_result.daily_summary_bullets
                    ],
                    "analysis_status": dashboard_result.analysis_status,
                    "total_chunks": getattr(dashboard_result, 'total_chunks', 1),
                    "successful_ai_chunks": getattr(dashboard_result, 'successful_ai_chunks', 1),
                    "fallback_chunks": getattr(dashboard_result, 'fallback_chunks', 0),
                    "failed_chunks": getattr(dashboard_result, 'failed_chunks', 0),
                    "original_line_count": getattr(dashboard_result, 'original_line_count', None),
                    "analyzed_line_count": getattr(dashboard_result, 'analyzed_line_count', None),
                    "was_log_reduced": getattr(dashboard_result, 'was_log_reduced', False)
                }
                
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            # Client disconnected
            pass
        finally:
            await event_bus.unsubscribe(topic, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
