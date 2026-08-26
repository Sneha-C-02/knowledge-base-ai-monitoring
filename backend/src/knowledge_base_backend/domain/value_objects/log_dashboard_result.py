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
    daily_summary_bullets: List[DashboardSummaryBullet] = field(default_factory=list)
    overall_status: str = "OK"
    files_analyzed: int = 0
