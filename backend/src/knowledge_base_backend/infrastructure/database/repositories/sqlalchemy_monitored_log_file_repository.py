from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.knowledge_base_backend.domain.repositories.monitored_log_file_repository import MonitoredLogFileRepository
from src.knowledge_base_backend.domain.entities.monitored_log_file import MonitoredLogFile
from src.knowledge_base_backend.infrastructure.database.models.monitored_log_file_model import MonitoredLogFileModel


class SqlAlchemyMonitoredLogFileRepository(MonitoredLogFileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, entry: MonitoredLogFile) -> MonitoredLogFile:
        model = MonitoredLogFileModel(
            instrument_id=entry.instrument_id,
            filename=entry.filename,
            total_lines_analyzed=entry.total_lines_analyzed,
            full_context_summary=entry.full_context_summary,
            created_at=entry.created_at,
            updated_at=entry.updated_at
        )
        self.session.add(model)
        await self.session.flush()
        entry.id = model.id
        return entry

    async def update(self, entry: MonitoredLogFile) -> MonitoredLogFile:
        query = select(MonitoredLogFileModel).where(MonitoredLogFileModel.id == entry.id)
        result = await self.session.execute(query)
        model = result.scalar_one()
        model.total_lines_analyzed = entry.total_lines_analyzed
        model.full_context_summary = entry.full_context_summary
        model.updated_at = entry.updated_at
        await self.session.flush()
        return entry

    async def find_by_instrument_and_filename(
        self, instrument_id: int, filename: str
    ) -> Optional[MonitoredLogFile]:
        query = (
            select(MonitoredLogFileModel)
            .where(MonitoredLogFileModel.instrument_id == instrument_id)
            .where(MonitoredLogFileModel.filename == filename)
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: MonitoredLogFileModel) -> MonitoredLogFile:
        return MonitoredLogFile(
            id=model.id,
            instrument_id=model.instrument_id,
            filename=model.filename,
            total_lines_analyzed=model.total_lines_analyzed,
            full_context_summary=model.full_context_summary,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
