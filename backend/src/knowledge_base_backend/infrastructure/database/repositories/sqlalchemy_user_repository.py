from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from src.knowledge_base_backend.domain.repositories.user_repository import UserRepository
from src.knowledge_base_backend.domain.entities.user_account import UserAccount
from src.knowledge_base_backend.infrastructure.database.models.user_model import UserModel

class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        
    def _map_to_domain(self, model: UserModel) -> UserAccount:
        return UserAccount(
            id=model.id,
            username=model.username,
            display_name=model.display_name,
            password_hash=model.password_hash,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    async def get_by_username(self, username: str) -> Optional[UserAccount]:
        query = select(UserModel).where(UserModel.username == username)
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model:
            return self._map_to_domain(model)
        return None
        
    async def get_by_id(self, id: int) -> Optional[UserAccount]:
        model = await self.session.get(UserModel, id)
        if model:
            return self._map_to_domain(model)
        return None
        
    async def save(self, user: UserAccount) -> UserAccount:
        if user.id == 0:
            model = UserModel(
                username=user.username,
                display_name=user.display_name,
                password_hash=user.password_hash,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            self.session.add(model)
            await self.session.flush()
            user.id = model.id
        else:
            model = await self.session.get(UserModel, user.id)
            if model:
                model.username = user.username
                model.display_name = user.display_name
                model.password_hash = user.password_hash
                model.is_active = user.is_active
                model.updated_at = user.updated_at
                await self.session.flush()
        return user
