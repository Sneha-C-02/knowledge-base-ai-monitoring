from src.knowledge_base_backend.domain.repositories.activity_repository import ActivityRepository
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.domain.value_objects.pagination_result import PaginationResult
from src.knowledge_base_backend.domain.entities.system_activity import SystemActivity
from typing import Optional

class ListActivitiesUseCase:
    def __init__(self, activity_repository: ActivityRepository) -> None:
        self.activity_repository = activity_repository

    async def execute(
        self, pagination: PaginationRequest, activity_type: Optional[str] = None
    ) -> PaginationResult[SystemActivity]:
        return await self.activity_repository.get_paginated_activities(pagination, activity_type)
