from src.knowledge_base_backend.domain.repositories.permission_repository import PermissionRepository


class AuthorizationService:

    def __init__(self, permission_repository: PermissionRepository) -> None:
        self.permission_repository = permission_repository

    async def has_permission(self, group_id: int | None, permission_name: str) -> bool:
        if group_id is None:
            return False

        permissions = await self.permission_repository.get_by_group_id(group_id)

        return any(permission.name == permission_name for permission in permissions)