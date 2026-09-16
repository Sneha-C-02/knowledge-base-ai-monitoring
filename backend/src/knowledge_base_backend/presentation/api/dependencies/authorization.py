from fastapi import HTTPException, status

from src.knowledge_base_backend.application.services.authorization_service import (
    AuthorizationService,
)


async def require_permission(
    authorization_service: AuthorizationService,
    group_id: int | None,
    permission_name: str,
) -> None:
    allowed = await authorization_service.has_permission(
        group_id, permission_name
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this module.",
        )