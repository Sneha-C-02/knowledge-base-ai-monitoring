from src.knowledge_base_backend.domain.repositories.notification_repository import NotificationRepository
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.domain.value_objects.pagination_result import PaginationResult
from src.knowledge_base_backend.domain.entities.system_notification import SystemNotification
from typing import Optional

class ListNotificationsUseCase:
    def __init__(self, notification_repository: NotificationRepository) -> None:
        self.notification_repository = notification_repository

    async def execute(
        self, pagination: PaginationRequest, notification_type: Optional[str] = None, is_read: Optional[bool] = None
    ) -> PaginationResult[SystemNotification]:
        return await self.notification_repository.get_paginated_notifications(pagination, notification_type, is_read)
