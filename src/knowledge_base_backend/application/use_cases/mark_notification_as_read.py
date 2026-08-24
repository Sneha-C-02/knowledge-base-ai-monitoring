from src.knowledge_base_backend.domain.repositories.notification_repository import NotificationRepository
from src.knowledge_base_backend.domain.entities.system_notification import SystemNotification
from typing import Optional

class MarkNotificationAsReadUseCase:
    def __init__(self, notification_repository: NotificationRepository) -> None:
        self.notification_repository = notification_repository

    async def execute(self, identifier: str) -> Optional[SystemNotification]:
        notification = await self.notification_repository.get_by_identifier(identifier)
        if notification:
            notification.is_read = True
            await self.notification_repository.save(notification)
        return notification
