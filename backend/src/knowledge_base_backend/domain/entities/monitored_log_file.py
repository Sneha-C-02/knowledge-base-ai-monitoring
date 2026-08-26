from dataclasses import dataclass
from datetime import datetime


@dataclass
class MonitoredLogFile:
    """
    Tracks a log file that has been added for monitoring.
    Stores how far we've read and the AI's running context summary,
    so subsequent uploads only analyze NEW lines.
    """
    id: int
    instrument_id: int
    filename: str
    total_lines_analyzed: int
    full_context_summary: str
    created_at: datetime
    updated_at: datetime
