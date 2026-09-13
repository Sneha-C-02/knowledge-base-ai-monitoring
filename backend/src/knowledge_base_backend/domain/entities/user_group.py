from dataclasses import dataclass


@dataclass
class UserGroup:
    id: int
    name: str
    description: str
    is_active: bool