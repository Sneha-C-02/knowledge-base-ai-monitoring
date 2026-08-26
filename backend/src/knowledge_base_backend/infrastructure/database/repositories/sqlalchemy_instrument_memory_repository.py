from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.knowledge_base_backend.domain.repositories.instrument_memory_repository import InstrumentMemoryRepository
from src.knowledge_base_backend.domain.entities.instrument_memory_entry import InstrumentMemoryEntry
from src.knowledge_base_backend.infrastructure.database.models.instrument_memory_model import InstrumentMemoryModel


class SqlAlchemyInstrumentMemoryRepository(InstrumentMemoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_memory_entry(self, entry: InstrumentMemoryEntry) -> InstrumentMemoryEntry:
        model = InstrumentMemoryModel(
            instrument_id=entry.instrument_id,
            instrument_name=entry.instrument_name,
            analysis_timestamp=entry.analysis_timestamp,
            log_filename=entry.log_filename,
            critical_incidents=entry.critical_incidents,
            warnings=entry.warnings,
            errors=entry.errors,
            healthy_apps=entry.healthy_apps,
            ai_summary=entry.ai_summary,
            raw_issues_json=entry.raw_issues_json
        )
        self.session.add(model)
        await self.session.flush()
        entry.id = model.id
        return entry

    async def get_memory_for_instrument(self, instrument_id: int, limit: int = 20) -> List[InstrumentMemoryEntry]:
        query = (
            select(InstrumentMemoryModel)
            .where(InstrumentMemoryModel.instrument_id == instrument_id)
            .order_by(desc(InstrumentMemoryModel.analysis_timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def get_all_latest_entries(self) -> List[InstrumentMemoryEntry]:
        """Get the most recent memory entry for each instrument."""
        from sqlalchemy import func
        subquery = (
            select(
                InstrumentMemoryModel.instrument_id,
                func.max(InstrumentMemoryModel.id).label("max_id")
            )
            .group_by(InstrumentMemoryModel.instrument_id)
            .subquery()
        )
        query = (
            select(InstrumentMemoryModel)
            .join(subquery, InstrumentMemoryModel.id == subquery.c.max_id)
            .order_by(desc(InstrumentMemoryModel.analysis_timestamp))
        )
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(model: InstrumentMemoryModel) -> InstrumentMemoryEntry:
        return InstrumentMemoryEntry(
            id=model.id,
            instrument_id=model.instrument_id,
            instrument_name=model.instrument_name,
            analysis_timestamp=model.analysis_timestamp,
            log_filename=model.log_filename,
            critical_incidents=model.critical_incidents,
            warnings=model.warnings,
            errors=model.errors,
            healthy_apps=model.healthy_apps,
            ai_summary=model.ai_summary,
            raw_issues_json=model.raw_issues_json
        )
