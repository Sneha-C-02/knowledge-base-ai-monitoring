from datetime import datetime, timezone
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider

class UtcDateTimeProvider(DateTimeProvider):
    def get_current_utc_time(self) -> datetime:
        return datetime.now(timezone.utc)
