from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class SystemActivity:
    id: int
    activity_identifier: str
    activity_type: str
    message: str
    created_at: datetime
    username: Optional[str] = None
