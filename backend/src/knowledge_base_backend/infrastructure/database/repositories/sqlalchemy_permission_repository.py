from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.knowledge_base_backend.domain.entities.permission import Permission
from src.knowledge_base_backend.domain.repositories.permission_repository import PermissionRepository
from src.knowledge_base_backend.infrastructure.database.models.permission_model import PermissionModel
from src.knowledge_base_backend.infrastructure.database.models.group_permission_model import GroupPermissionModel


class SqlAlchemyPermissionRepository(PermissionRepository):

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_group_id(self, group_id: int) -> list[Permission]:
        query = (
            select(PermissionModel)
            .join(
                GroupPermissionModel,
                PermissionModel.id == GroupPermissionModel.permission_id
            )
            .where(GroupPermissionModel.group_id == group_id)
        )

        result = await self.session.execute(query)

        return [
            Permission(
                id=model.id,
                name=model.name,
                description=model.description
            )
            for model in result.scalars().all()
        ]