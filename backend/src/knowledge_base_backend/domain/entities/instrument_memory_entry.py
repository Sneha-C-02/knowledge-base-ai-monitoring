from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class InstrumentMemoryEntry:
    id: int
    instrument_id: int
    instrument_name: str
    analysis_timestamp: datetime
    log_filename: str
    critical_incidents: int
    warnings: int
    errors: int
    healthy_apps: int
    ai_summary: str
    raw_issues_json: Optional[str] = None
