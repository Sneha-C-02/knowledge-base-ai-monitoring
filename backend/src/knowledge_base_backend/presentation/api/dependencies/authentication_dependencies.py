from fastapi import Depends, Request
from src.knowledge_base_backend.presentation.security.bearer_token_dependency import bearer_scheme
from fastapi.security import HTTPAuthorizationCredentials
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import AuthenticationError

async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    if not credentials:
        raise AuthenticationError("Missing authentication token")
    return credentials.credentials
