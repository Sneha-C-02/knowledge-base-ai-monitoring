from dataclasses import dataclass
from datetime import datetime

@dataclass
class SystemNotification:
    id: int
    notification_identifier: str
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
