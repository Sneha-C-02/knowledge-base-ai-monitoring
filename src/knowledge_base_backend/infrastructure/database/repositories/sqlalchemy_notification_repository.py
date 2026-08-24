from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from src.knowledge_base_backend.domain.repositories.notification_repository import NotificationRepository
from src.knowledge_base_backend.domain.entities.system_notification import SystemNotification
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.domain.value_objects.pagination_result import PaginationResult
from src.knowledge_base_backend.infrastructure.database.models.notification_model import SystemNotificationModel

class SqlAlchemyNotificationRepository(NotificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        
    def _map_to_domain(self, model: SystemNotificationModel) -> SystemNotification:
        return SystemNotification(
            id=model.id,
            notification_identifier=model.notification_identifier,
            title=model.title,
            message=model.message,
            notification_type=model.notification_type,
            is_read=model.is_read,
            created_at=model.created_at
        )

    async def save(self, notification: SystemNotification) -> SystemNotification:
        if notification.id == 0:
            model = SystemNotificationModel(
                notification_identifier=notification.notification_identifier,
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type,
                is_read=notification.is_read,
                created_at=notification.created_at
            )
            self.session.add(model)
            await self.session.flush()
            notification.id = model.id
        else:
            model = await self.session.get(SystemNotificationModel, notification.id)
            if model:
                model.is_read = notification.is_read
                await self.session.flush()
                
        return notification

    async def get_by_identifier(self, identifier: str) -> Optional[SystemNotification]:
        query = select(SystemNotificationModel).where(SystemNotificationModel.notification_identifier == identifier)
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model:
            return self._map_to_domain(model)
        return None
        
    async def get_paginated_notifications(
        self, pagination: PaginationRequest, notification_type: Optional[str] = None, is_read: Optional[bool] = None
    ) -> PaginationResult[SystemNotification]:
        
        count_query = select(func.count(SystemNotificationModel.id))
        query = select(SystemNotificationModel)
        
        if notification_type:
            count_query = count_query.where(SystemNotificationModel.notification_type == notification_type)
            query = query.where(SystemNotificationModel.notification_type == notification_type)
            
        if is_read is not None:
            count_query = count_query.where(SystemNotificationModel.is_read == is_read)
            query = query.where(SystemNotificationModel.is_read == is_read)
            
        total_items_result = await self.session.execute(count_query)
        total_items = total_items_result.scalar() or 0
        
        query = query.order_by(desc(SystemNotificationModel.created_at)).limit(pagination.page_size).offset(pagination.offset)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        items = [self._map_to_domain(model) for model in models]
        
        return PaginationResult.create(
            items=items,
            current_page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items
        )
