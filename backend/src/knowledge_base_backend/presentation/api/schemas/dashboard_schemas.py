from pydantic import BaseModel
from typing import List, Optional


class InstrumentSchema(BaseModel):
    id: int
    name: str


class DashboardSummaryBulletSchema(BaseModel):
    text: str
    severity: Optional[str] = None


class LogDashboardResponse(BaseModel):
    instrument_id: int
    instrument_name: str
    critical_incidents: int
    warnings: int
    errors: int
    healthy_apps: int
    overall_status: str
    files_analyzed: int
    daily_summary_bullets: List[DashboardSummaryBulletSchema]
    analysis_status: str = "FULL_AI_ANALYSIS"
    total_chunks: int = 1
    successful_ai_chunks: int = 1
    fallback_chunks: int = 0
    failed_chunks: int = 0
    original_line_count: Optional[int] = None
    analyzed_line_count: Optional[int] = None
    was_log_reduced: bool = False


class InstrumentMemoryEntrySchema(BaseModel):
    id: int
    instrument_id: int
    instrument_name: str
    analysis_timestamp: str
    log_filename: str
    critical_incidents: int
    warnings: int
    errors: int
    healthy_apps: int
    ai_summary: str


class InstrumentMemoryResponse(BaseModel):
    instrument_id: int
    instrument_name: str
    total_analyses: int
    history: List[InstrumentMemoryEntrySchema]
