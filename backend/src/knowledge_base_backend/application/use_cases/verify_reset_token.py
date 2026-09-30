import hashlib
from src.knowledge_base_backend.domain.repositories.user_repository import UserRepository
from src.knowledge_base_backend.domain.services.authentication_token_service import AuthenticationTokenService
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import (
    UserNotFoundError,
    InactiveUserError,
    InvalidResetTokenError,
)
from src.knowledge_base_backend.application.models.authentication_models import VerifyResetTokenResult

class VerifyResetTokenUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        token_service: AuthenticationTokenService,
    ) -> None:
        self.user_repository = user_repository
        self.token_service = token_service

    async def execute(self, reset_token: str) -> VerifyResetTokenResult:
        if not reset_token or not reset_token.strip():
            raise InvalidResetTokenError("Reset token is required.")

        payload = self.token_service.validate_password_reset_token(reset_token.strip())
        token_subject = payload.get("sub", "")
        token_pwh = payload.get("pwh", "")
        expires_at = payload.get("exp")

        user = await self.user_repository.get_by_username(token_subject)
        if not user:
            raise UserNotFoundError(f"User '{token_subject}' not found.")

        if not user.is_active:
            raise InactiveUserError(f"User account '{token_subject}' is disabled.")

        current_pwh = hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()[:16]
        if not token_pwh or token_pwh != current_pwh:
            raise InvalidResetTokenError("This password reset token has already been used or has been invalidated.")

        return VerifyResetTokenResult(
            username=user.username,
            valid=True,
            expires_at=expires_at,
            message="Reset token is valid.",
        )
