from typing import Protocol, Optional
from src.knowledge_base_backend.domain.entities.system_activity import SystemActivity
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.domain.value_objects.pagination_result import PaginationResult

class ActivityRepository(Protocol):
    async def save(self, activity: SystemActivity) -> SystemActivity: ...
    async def get_paginated_activities(
        self, pagination: PaginationRequest, activity_type: Optional[str] = None
    ) -> PaginationResult[SystemActivity]: ...
