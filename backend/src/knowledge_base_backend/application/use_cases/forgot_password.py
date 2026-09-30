import hashlib
import uuid
from src.knowledge_base_backend.domain.repositories.user_repository import UserRepository
from src.knowledge_base_backend.domain.repositories.activity_repository import ActivityRepository
from src.knowledge_base_backend.domain.services.authentication_token_service import AuthenticationTokenService
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import (
    UserNotFoundError,
    InactiveUserError,
)
from src.knowledge_base_backend.domain.entities.system_activity import SystemActivity
from src.knowledge_base_backend.application.models.authentication_models import ForgotPasswordResult
from src.knowledge_base_backend.configuration.application_settings import settings

class ForgotPasswordUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        token_service: AuthenticationTokenService,
        activity_repository: ActivityRepository,
        date_time_provider: DateTimeProvider,
    ) -> None:
        self.user_repository = user_repository
        self.token_service = token_service
        self.activity_repository = activity_repository
        self.date_time_provider = date_time_provider

    async def execute(self, username: str) -> ForgotPasswordResult:
        normalized_username = username.strip() if username else ""
        if not normalized_username:
            raise UserNotFoundError("Username must not be empty.")

        user = await self.user_repository.get_by_username(normalized_username)
        if not user:
            raise UserNotFoundError(f"User '{normalized_username}' not found.")

        if not user.is_active:
            raise InactiveUserError(f"User account '{normalized_username}' is disabled.")

        # Fingerprint current password hash to tie token uniquely to current password state
        pwh_fingerprint = hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()[:16]
        expiration_minutes = settings.jwt_password_reset_token_expiration_minutes

        token = self.token_service.create_password_reset_token(
            subject=user.username,
            token_hash_salt=pwh_fingerprint,
            expires_delta_minutes=expiration_minutes,
        )

        await self.activity_repository.save(
            SystemActivity(
                id=0,
                activity_identifier=uuid.uuid4().hex,
                activity_type="system",
                message=f"Password reset requested for user {user.username}",
                username=user.username,
                severity="INFO",
                metadata={"action": "FORGOT_PASSWORD_REQUESTED"},
                created_at=self.date_time_provider.get_current_utc_time(),
            )
        )

        return ForgotPasswordResult(
            username=user.username,
            reset_token=token,
            expires_in_minutes=expiration_minutes,
            message="Password reset token generated successfully. Use this token to reset your password.",
        )
