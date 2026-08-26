from typing import Protocol, Optional
from src.knowledge_base_backend.domain.entities.monitored_log_file import MonitoredLogFile


class MonitoredLogFileRepository(Protocol):
    async def save(self, entry: MonitoredLogFile) -> MonitoredLogFile: ...
    async def update(self, entry: MonitoredLogFile) -> MonitoredLogFile: ...
    async def find_by_instrument_and_filename(
        self, instrument_id: int, filename: str
    ) -> Optional[MonitoredLogFile]: ...
