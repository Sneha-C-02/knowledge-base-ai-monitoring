from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DashboardSummaryBullet:
    text: str
    severity: Optional[str] = None


@dataclass
class LogDashboardResult:
    """Structured result matching the AI Log Operations Dashboard format."""
    instrument_id: int
    instrument_name: str
    critical_incidents: int
    warnings: int
    errors: int
    healthy_apps: int
    files_analyzed: int
    daily_summary_bullets: List[DashboardSummaryBullet] = field(default_factory=list)
    overall_status: str = "OK"
    analysis_status: str = "FULL_AI_ANALYSIS"
    total_chunks: int = 1
    successful_ai_chunks: int = 1
    fallback_chunks: int = 0
    failed_chunks: int = 0
    original_line_count: Optional[int] = None
    analyzed_line_count: Optional[int] = None
    was_log_reduced: bool = False
