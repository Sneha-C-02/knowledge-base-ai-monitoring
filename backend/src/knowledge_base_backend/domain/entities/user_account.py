from dataclasses import dataclass
from datetime import datetime

@dataclass
class UserAccount:
    id: int
    username: str
    display_name: str
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
