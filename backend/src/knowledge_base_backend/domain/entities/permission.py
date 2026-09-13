from dataclasses import dataclass


@dataclass
class Permission:
    id: int
    name: str
    description: str | None