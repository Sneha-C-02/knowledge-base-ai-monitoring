import hashlib
import uuid
from typing import Optional
from src.knowledge_base_backend.domain.repositories.user_repository import UserRepository
from src.knowledge_base_backend.domain.repositories.activity_repository import ActivityRepository
from src.knowledge_base_backend.domain.services.password_hashing_service import PasswordHashingService
from src.knowledge_base_backend.domain.services.authentication_token_service import AuthenticationTokenService
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import (
    UserNotFoundError,
    InactiveUserError,
    InvalidResetTokenError,
    PasswordValidationError,
)
from src.knowledge_base_backend.domain.entities.system_activity import SystemActivity
from src.knowledge_base_backend.application.models.authentication_models import ResetPasswordResult

class ResetPasswordUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hashing_service: PasswordHashingService,
        token_service: AuthenticationTokenService,
        activity_repository: ActivityRepository,
        date_time_provider: DateTimeProvider,
    ) -> None:
        self.user_repository = user_repository
        self.password_hashing_service = password_hashing_service
        self.token_service = token_service
        self.activity_repository = activity_repository
        self.date_time_provider = date_time_provider

    async def execute(
        self, reset_token: str, new_password: str, username: Optional[str] = None
    ) -> ResetPasswordResult:
        if not reset_token or not reset_token.strip():
            raise InvalidResetTokenError("Reset token is required.")

        if not new_password or len(new_password.strip()) < 6:
            raise PasswordValidationError("Password must be at least 6 characters long.")

        payload = self.token_service.validate_password_reset_token(reset_token.strip())
        token_subject = payload.get("sub")
        token_pwh = payload.get("pwh", "")

        if username and username.strip().lower() != token_subject.lower():
            raise InvalidResetTokenError("Reset token was not issued for this user.")

        user = await self.user_repository.get_by_username(token_subject)
        if not user:
            raise UserNotFoundError(f"User '{token_subject}' not found.")

        if not user.is_active:
            raise InactiveUserError(f"User account '{token_subject}' is disabled.")

        current_pwh = hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()[:16]
        if not token_pwh or token_pwh != current_pwh:
            raise InvalidResetTokenError("This password reset token has already been used or has been invalidated.")

        # Hash new password (preserve exact user password without stripping away intentional characters)
        new_password_hash = self.password_hashing_service.hash_password(new_password)
        user.password_hash = new_password_hash
        user.updated_at = self.date_time_provider.get_current_utc_time()

        await self.user_repository.save(user)

        await self.activity_repository.save(
            SystemActivity(
                id=0,
                activity_identifier=uuid.uuid4().hex,
                activity_type="system",
                message=f"Password successfully reset for user {user.username}",
                username=user.username,
                severity="INFO",
                metadata={"action": "PASSWORD_RESET_COMPLETED"},
                created_at=self.date_time_provider.get_current_utc_time(),
            )
        )

        return ResetPasswordResult(
            username=user.username,
            success=True,
            message="Password has been reset successfully. You can now log in with your new password.",
        )
