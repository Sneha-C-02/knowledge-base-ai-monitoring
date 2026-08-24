from typing import Protocol, Optional
from src.knowledge_base_backend.domain.entities.system_notification import SystemNotification
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.domain.value_objects.pagination_result import PaginationResult

class NotificationRepository(Protocol):
    async def save(self, notification: SystemNotification) -> SystemNotification: ...
    async def get_by_identifier(self, identifier: str) -> Optional[SystemNotification]: ...
    async def get_paginated_notifications(
        self, pagination: PaginationRequest, notification_type: Optional[str] = None, is_read: Optional[bool] = None
    ) -> PaginationResult[SystemNotification]: ...
