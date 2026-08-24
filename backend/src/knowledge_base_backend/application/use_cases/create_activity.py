from src.knowledge_base_backend.domain.repositories.activity_repository import ActivityRepository
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
from src.knowledge_base_backend.domain.entities.system_activity import SystemActivity
import uuid

class CreateActivityUseCase:
    def __init__(
        self,
        activity_repository: ActivityRepository,
        date_time_provider: DateTimeProvider,
    ) -> None:
        self.activity_repository = activity_repository
        self.date_time_provider = date_time_provider

    async def execute(self, activity_type: str, message: str, username: str, severity: str = "INFO", metadata: dict = None) -> None:
        await self.activity_repository.save(
            SystemActivity(
                id=0,
                activity_identifier=uuid.uuid4().hex,
                activity_type=activity_type,
                message=message,
                username=username,
                severity=severity,
                metadata=metadata or {},
                created_at=self.date_time_provider.get_current_utc_time(),
            )
        )
