
from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide

from src.knowledge_base_backend.application.services.authorization_service import (
    AuthorizationService,
)
from src.knowledge_base_backend.presentation.api.dependencies.authorization import (
    require_permission,
)
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import (
    get_current_user_token,
)
from src.knowledge_base_backend.domain.repositories.user_repository import UserRepository
from src.knowledge_base_backend.domain.services.authentication_token_service import (
    AuthenticationTokenService,
)
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from pydantic import BaseModel


router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/management")
@inject
async def user_management(
    token: str = Depends(get_current_user_token),
    user_repository: UserRepository = Depends(
        Provide[ApplicationContainer.user_repository]
    ),
    token_service: AuthenticationTokenService = Depends(
        Provide[ApplicationContainer.token_service]
    ),
    authorization_service: AuthorizationService = Depends(
        Provide[ApplicationContainer.authorization_service]
    ),
):
    username = token_service.validate_access_token(token)

    user = await user_repository.get_by_username(username)

    if not user:
        return {"message": "User not found"}

    await require_permission(
        authorization_service,
        user.group_id,
        "user_management",
    )

    return {
        "message": "User management access granted",
        "username": user.username,
        "group_id": user.group_id,
    }

@router.get("/management/users")
@inject
async def get_all_users(
    token: str = Depends(get_current_user_token),
    user_repository: UserRepository = Depends(
        Provide[ApplicationContainer.user_repository]
    ),
    token_service: AuthenticationTokenService = Depends(
        Provide[ApplicationContainer.token_service]
    ),
    authorization_service: AuthorizationService = Depends(
        Provide[ApplicationContainer.authorization_service]
    ),
):
    username = token_service.validate_access_token(token)
    current_user = await user_repository.get_by_username(username)

    if not current_user:
        return {"message": "User not found"}

    await require_permission(
        authorization_service,
        current_user.group_id,
        "user_management",
    )

    users = await user_repository.get_all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "group_id": user.group_id,
        }
        for user in users
    ]

class ChangeGroupRequest(BaseModel):
    group_id: int


@router.put("/management/users/{user_id}/group")
@inject
async def change_user_group(
    user_id: int,
    request: ChangeGroupRequest,
    token: str = Depends(get_current_user_token),
    user_repository: UserRepository = Depends(
        Provide[ApplicationContainer.user_repository]
    ),
    token_service: AuthenticationTokenService = Depends(
        Provide[ApplicationContainer.token_service]
    ),
    authorization_service: AuthorizationService = Depends(
        Provide[ApplicationContainer.authorization_service]
    ),
):
    username = token_service.validate_access_token(token)
    current_user = await user_repository.get_by_username(username)

    if not current_user:
        return {"message": "User not found"}

    await require_permission(
        authorization_service,
        current_user.group_id,
        "user_management",
    )

    user = await user_repository.get_by_id(user_id)

    if not user:
        return {"message": "Target user not found"}

    user.group_id = request.group_id

    await user_repository.save(user)

    return {
        "message": "User group updated successfully",
        "user_id": user.id,
        "group_id": user.group_id,
    }