from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class SystemActivity:
    id: int
    activity_identifier: str
    activity_type: str
    message: str
    created_at: datetime
    username: Optional[str] = None
    severity: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
