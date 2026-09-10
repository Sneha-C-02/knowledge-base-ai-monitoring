import uuid
from typing import Optional
from src.knowledge_base_backend.domain.repositories.user_repository import UserRepository
from src.knowledge_base_backend.domain.repositories.activity_repository import ActivityRepository
from src.knowledge_base_backend.domain.services.password_hashing_service import PasswordHashingService
from src.knowledge_base_backend.domain.services.password_validator import PasswordValidator
from src.knowledge_base_backend.domain.services.authentication_token_service import AuthenticationTokenService
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import UserAlreadyExistsError
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError
from src.knowledge_base_backend.application.models.authentication_models import AuthenticationResult
from src.knowledge_base_backend.domain.entities.user_account import UserAccount
from src.knowledge_base_backend.domain.entities.system_activity import SystemActivity

class RegisterUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hashing_service: PasswordHashingService,
        password_validator: PasswordValidator,
        token_service: AuthenticationTokenService,
        activity_repository: ActivityRepository,
        date_time_provider: DateTimeProvider,
    ) -> None:
        self.user_repository = user_repository
        self.password_hashing_service = password_hashing_service
        self.password_validator = password_validator
        self.token_service = token_service
        self.activity_repository = activity_repository
        self.date_time_provider = date_time_provider

    async def execute(
        self,
        username: str,
        password: str,
        confirm_password: str,
        display_name: Optional[str] = None
    ) -> AuthenticationResult:
        cleaned_username = (username or "").strip()
        if not cleaned_username or len(cleaned_username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")

        if not cleaned_username.replace("_", "").isalnum():
            raise ValidationError("Username may only contain letters, numbers, and underscores.")

        if password != confirm_password:
            raise ValidationError("Passwords do not match.")

        # Validate password policy (minimum 8 chars, 1 letter, 1 number)
        self.password_validator.validate(password)

        # Check for existing user
        existing_user = await self.user_repository.get_by_username(cleaned_username)
        if existing_user:
            raise UserAlreadyExistsError(f"Username '{cleaned_username}' is already taken.")

        # Hash password and create user
        password_hash = self.password_hashing_service.hash_password(password)
        now = self.date_time_provider.get_current_utc_time()
        final_display_name = (display_name or "").strip() or cleaned_username

        user = UserAccount(
            id=0,
            username=cleaned_username,
            display_name=final_display_name,
            password_hash=password_hash,
            is_active=True,
            created_at=now,
            updated_at=now
        )

        saved_user = await self.user_repository.save(user)
        token = self.token_service.create_access_token(saved_user.username)

        # Record registration activity
        await self.activity_repository.save(
            SystemActivity(
                id=0,
                activity_identifier=uuid.uuid4().hex,
                activity_type="system",
                message=f"New user registered: {saved_user.username}",
                username=saved_user.username,
                severity="INFO",
                metadata={"display_name": saved_user.display_name},
                created_at=now,
            )
        )

        return AuthenticationResult(token=token, user=saved_user)
