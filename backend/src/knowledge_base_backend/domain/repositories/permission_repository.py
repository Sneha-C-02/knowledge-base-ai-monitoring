from typing import Protocol

from src.knowledge_base_backend.domain.entities.permission import Permission


class PermissionRepository(Protocol):

    async def get_by_group_id(self, group_id: int) -> list[Permission]: ...