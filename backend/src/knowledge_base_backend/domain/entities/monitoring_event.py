from dataclasses import dataclass
from datetime import datetime

@dataclass
class MonitoringEvent:
    timestamp: datetime
    level: str
    message: str
