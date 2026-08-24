from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from src.knowledge_base_backend.domain.repositories.activity_repository import ActivityRepository
from src.knowledge_base_backend.domain.entities.system_activity import SystemActivity
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.domain.value_objects.pagination_result import PaginationResult
from src.knowledge_base_backend.infrastructure.database.models.activity_model import SystemActivityModel

class SqlAlchemyActivityRepository(ActivityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        
    def _map_to_domain(self, model: SystemActivityModel) -> SystemActivity:
        return SystemActivity(
            id=model.id,
            activity_identifier=model.activity_identifier,
            activity_type=model.activity_type,
            message=model.message,
            created_at=model.created_at,
            username=model.username,
            severity=model.severity,
            metadata=model.metadata_payload
        )

    async def save(self, activity: SystemActivity) -> SystemActivity:
        model = SystemActivityModel(
            activity_identifier=activity.activity_identifier,
            activity_type=activity.activity_type,
            message=activity.message,
            username=activity.username,
            created_at=activity.created_at,
            severity=activity.severity,
            metadata_payload=activity.metadata
        )
        self.session.add(model)
        await self.session.flush()
        activity.id = model.id
        return activity
        
    async def get_paginated_activities(
        self, pagination: PaginationRequest, activity_type: Optional[str] = None
    ) -> PaginationResult[SystemActivity]:
        
        count_query = select(func.count(SystemActivityModel.id))
        if activity_type:
            count_query = count_query.where(SystemActivityModel.activity_type == activity_type)
            
        total_items_result = await self.session.execute(count_query)
        total_items = total_items_result.scalar() or 0
        
        query = select(SystemActivityModel)
        if activity_type:
            query = query.where(SystemActivityModel.activity_type == activity_type)
            
        query = query.order_by(desc(SystemActivityModel.created_at)).limit(pagination.page_size).offset(pagination.offset)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        items = [self._map_to_domain(model) for model in models]
        
        return PaginationResult.create(
            items=items,
            current_page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items
        )
