from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from src.knowledge_base_backend.domain.repositories.monitored_log_file_repository import MonitoredLogFileRepository
from src.knowledge_base_backend.domain.entities.monitored_log_file import MonitoredLogFile
from src.knowledge_base_backend.infrastructure.database.models.monitored_log_file_model import MonitoredLogFileModel


class SqlAlchemyMonitoredLogFileRepository(MonitoredLogFileRepository):
    _column_ensured: bool = False

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _ensure_column_exists(self) -> None:
        """Defensive check to ensure status column exists in existing database tables."""
        if SqlAlchemyMonitoredLogFileRepository._column_ensured:
            return
        try:
            # For Postgres, execute safe column addition if missing
            await self.session.execute(
                text("ALTER TABLE monitored_log_files ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'MONITORING'")
            )
            SqlAlchemyMonitoredLogFileRepository._column_ensured = True
        except Exception:
            # SQLite or already handled; pass silently
            pass

    async def save(self, entry: MonitoredLogFile) -> MonitoredLogFile:
        await self._ensure_column_exists()
        model = MonitoredLogFileModel(
            instrument_id=entry.instrument_id,
            filename=entry.filename,
            total_lines_analyzed=entry.total_lines_analyzed,
            full_context_summary=entry.full_context_summary,
            status=entry.status or "MONITORING",
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        entry.id = model.id
        return entry

    async def update(self, entry: MonitoredLogFile) -> MonitoredLogFile:
        await self._ensure_column_exists()
        query = select(MonitoredLogFileModel).where(MonitoredLogFileModel.id == entry.id)
        result = await self.session.execute(query)
        model = result.scalar_one()
        model.total_lines_analyzed = entry.total_lines_analyzed
        model.full_context_summary = entry.full_context_summary
        model.status = entry.status or "MONITORING"
        model.updated_at = entry.updated_at
        await self.session.flush()
        return entry

    async def find_by_instrument_and_filename(
        self, instrument_id: int, filename: str
    ) -> Optional[MonitoredLogFile]:
        await self._ensure_column_exists()
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

    async def find_by_instrument_id(self, instrument_id: int) -> List[MonitoredLogFile]:
        await self._ensure_column_exists()
        query = (
            select(MonitoredLogFileModel)
            .where(MonitoredLogFileModel.instrument_id == instrument_id)
            .order_by(MonitoredLogFileModel.updated_at.desc())
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_all(self) -> List[MonitoredLogFile]:
        await self._ensure_column_exists()
        query = select(MonitoredLogFileModel).order_by(MonitoredLogFileModel.updated_at.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def update_status(
        self, instrument_id: int, filename: str, status: str
    ) -> Optional[MonitoredLogFile]:
        await self._ensure_column_exists()
        query = (
            select(MonitoredLogFileModel)
            .where(MonitoredLogFileModel.instrument_id == instrument_id)
            .where(MonitoredLogFileModel.filename == filename)
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.status = status
        model.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: MonitoredLogFileModel) -> MonitoredLogFile:
        return MonitoredLogFile(
            id=model.id,
            instrument_id=model.instrument_id,
            filename=model.filename,
            total_lines_analyzed=model.total_lines_analyzed,
            full_context_summary=model.full_context_summary,
            status=getattr(model, "status", "MONITORING") or "MONITORING",
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
