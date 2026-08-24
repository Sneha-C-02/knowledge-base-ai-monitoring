from src.knowledge_base_backend.domain.repositories.user_repository import UserRepository
from src.knowledge_base_backend.domain.repositories.activity_repository import ActivityRepository
from src.knowledge_base_backend.domain.services.password_hashing_service import PasswordHashingService
from src.knowledge_base_backend.domain.services.authentication_token_service import AuthenticationTokenService
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import InvalidCredentialsError, InactiveUserError
from src.knowledge_base_backend.application.models.authentication_models import AuthenticationResult
from src.knowledge_base_backend.domain.entities.system_activity import SystemActivity

class AuthenticateUserUseCase:
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

    async def execute(self, username: str, password: str) -> AuthenticationResult:
        user = await self.user_repository.get_by_username(username)
        if not user:
            raise InvalidCredentialsError("Invalid credentials")

        if not self.password_hashing_service.verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")

        if not user.is_active:
            raise InactiveUserError("User is not active")

        token = self.token_service.create_access_token(user.username)
        
        await self.activity_repository.save(
            SystemActivity(
                id=0,
                activity_identifier=__import__('uuid').uuid4().hex,
                activity_type="system",
                message="User logged in",
                username=user.username,
                severity="INFO",
                metadata=None,
                created_at=self.date_time_provider.get_current_utc_time(),
            )
        )

        return AuthenticationResult(token=token, user=user)
