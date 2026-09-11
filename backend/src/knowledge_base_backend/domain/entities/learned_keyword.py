from dataclasses import dataclass
from datetime import datetime


@dataclass
class LearnedKeyword:
    """
    A search keyword the system has learned from analyzing error/warning lines
    in uploaded log files. Frequency accumulates across analysis runs so the
    most consistently error-related terms rise to the top of future suggestions.
    """

    id: int
    instrument_id: int  # 0 means "global", not tied to one instrument
    keyword: str
    severity: str  # "critical" | "warning" — the highest severity ever observed for this term
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime
