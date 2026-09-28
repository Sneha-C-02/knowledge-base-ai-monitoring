from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, UniqueConstraint, delete, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.knowledge_base_backend.domain.entities.learned_keyword import LearnedKeyword
from src.knowledge_base_backend.domain.repositories.learned_keyword_repository import LearnedKeywordRepository
from src.knowledge_base_backend.domain.services.log_keyword_learning_service import LearnedKeywordCandidate
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base
from src.knowledge_base_backend.infrastructure.database.table_schema_ensurer import TableSchemaEnsurer

# Severities are ranked so repeated learning never downgrades a keyword that
# was once observed at "critical" back down to "warning".
_SEVERITY_RANK = {"warning": 1, "critical": 2}


class LearnedKeywordModel(Base):
    __tablename__ = "learned_keywords"
    __table_args__ = (UniqueConstraint("instrument_id", "keyword", name="uq_learned_keywords_instrument_keyword"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # 0 == global / not tied to a specific instrument (matches LogEventVectorRecord convention)
    instrument_id = Column(BigInteger, nullable=False, default=0, index=True)
    keyword = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False, default="warning")
    occurrence_count = Column(Integer, nullable=False, default=1, index=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default="accepted")
    failure_indicator = Column(Text, nullable=True)
    sample_line = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)



class SqlAlchemyLearnedKeywordRepository(LearnedKeywordRepository):
    """
    Persists and retrieves learned keyword occurrence counts.

    Schema provisioning is delegated to `TableSchemaEnsurer` rather than
    implemented inline, so this class stays focused on reads/writes and the
    "has this table been auto-created yet?" state lives in one injectable
    collaborator instead of a hidden class attribute on the repository.
    """

    def __init__(self, session: AsyncSession, schema_ensurer: TableSchemaEnsurer) -> None:
        self.session = session
        self._schema_ensurer = schema_ensurer

    async def _ensure_schema(self) -> None:
        await self._schema_ensurer.ensure_table_exists(self.session, LearnedKeywordModel.__table__)
        try:
            for col, col_def in [
                ("status", "VARCHAR(32) DEFAULT 'accepted'"),
                ("failure_indicator", "TEXT"),
                ("sample_line", "TEXT"),
                ("notes", "TEXT"),
            ]:
                await self.session.execute(
                    text(f"ALTER TABLE learned_keywords ADD COLUMN IF NOT EXISTS {col} {col_def}")
                )
        except Exception:
            pass

    async def record_occurrences(self, instrument_id: int, candidates: List[LearnedKeywordCandidate]) -> None:
        if not candidates:
            return

        await self._ensure_schema()

        now = datetime.now(timezone.utc)

        # Aggregate duplicate terms within this single batch first so we issue
        # one upsert per distinct keyword instead of one per raw match.
        aggregated_severity: dict[str, str] = {}
        counts: dict[str, int] = {}
        for candidate in candidates:
            counts[candidate.keyword] = counts.get(candidate.keyword, 0) + 1
            existing_severity = aggregated_severity.get(candidate.keyword)
            if existing_severity is None or _SEVERITY_RANK[candidate.severity] > _SEVERITY_RANK[existing_severity]:
                aggregated_severity[candidate.keyword] = candidate.severity

        for keyword, severity in aggregated_severity.items():
            increment = counts[keyword]
            stmt = (
                pg_insert(LearnedKeywordModel)
                .values(
                    instrument_id=instrument_id,
                    keyword=keyword,
                    severity=severity,
                    occurrence_count=increment,
                    first_seen_at=now,
                    last_seen_at=now,
                    status="accepted",
                )
                .on_conflict_do_update(
                    index_elements=["instrument_id", "keyword"],
                    set_={
                        "occurrence_count": LearnedKeywordModel.occurrence_count + increment,
                        "last_seen_at": now,
                        "severity": severity if _SEVERITY_RANK[severity] == 2 else LearnedKeywordModel.severity,
                    },
                )
            )
            await self.session.execute(stmt)

        await self.session.flush()

    async def get_top_keywords(self, instrument_id: int = 0, limit: int = 10) -> List[LearnedKeyword]:
        await self._ensure_schema()

        query = select(LearnedKeywordModel).where(
            or_(
                LearnedKeywordModel.status == "accepted",
                LearnedKeywordModel.status.is_(None),
            )
        )
        if instrument_id:
            query = query.where(
                or_(
                    LearnedKeywordModel.instrument_id == instrument_id,
                    LearnedKeywordModel.instrument_id == 0,
                )
            )
        query = query.order_by(LearnedKeywordModel.occurrence_count.desc()).limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def accept_keyword(
        self,
        keyword: str,
        severity: str = "warning",
        instrument_id: int = 0,
        failure_indicator: Optional[str] = None,
        sample_line: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> LearnedKeyword:
        await self._ensure_schema()
        now = datetime.now(timezone.utc)
        clean_keyword = keyword.strip().lower()

        stmt = (
            pg_insert(LearnedKeywordModel)
            .values(
                instrument_id=instrument_id,
                keyword=clean_keyword,
                severity=severity,
                occurrence_count=1,
                first_seen_at=now,
                last_seen_at=now,
                status="accepted",
                failure_indicator=failure_indicator,
                sample_line=sample_line,
                notes=notes,
            )
            .on_conflict_do_update(
                index_elements=["instrument_id", "keyword"],
                set_={
                    "severity": severity,
                    "status": "accepted",
                    "failure_indicator": failure_indicator if failure_indicator else LearnedKeywordModel.failure_indicator,
                    "sample_line": sample_line if sample_line else LearnedKeywordModel.sample_line,
                    "notes": notes if notes else LearnedKeywordModel.notes,
                    "last_seen_at": now,
                },
            )
            .returning(LearnedKeywordModel)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        model = result.scalar_one()
        return self._to_entity(model)

    async def list_accepted_keywords(self, instrument_id: Optional[int] = None) -> List[LearnedKeyword]:
        await self._ensure_schema()
        query = select(LearnedKeywordModel).where(
            or_(
                LearnedKeywordModel.status == "accepted",
                LearnedKeywordModel.status.is_(None),
            )
        )
        if instrument_id is not None and instrument_id > 0:
            query = query.where(
                or_(
                    LearnedKeywordModel.instrument_id == instrument_id,
                    LearnedKeywordModel.instrument_id == 0,
                )
            )
        query = query.order_by(LearnedKeywordModel.occurrence_count.desc(), LearnedKeywordModel.id.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def delete_accepted_keyword(self, keyword_id: int) -> bool:
        await self._ensure_schema()
        stmt = delete(LearnedKeywordModel).where(LearnedKeywordModel.id == keyword_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return (result.rowcount or 0) > 0

    async def reject_keyword(self, keyword: str, instrument_id: int = 0) -> bool:
        await self._ensure_schema()
        now = datetime.now(timezone.utc)
        clean_keyword = keyword.strip().lower()
        stmt = (
            pg_insert(LearnedKeywordModel)
            .values(
                instrument_id=instrument_id,
                keyword=clean_keyword,
                severity="warning",
                occurrence_count=0,
                first_seen_at=now,
                last_seen_at=now,
                status="rejected",
            )
            .on_conflict_do_update(
                index_elements=["instrument_id", "keyword"],
                set_={
                    "status": "rejected",
                    "last_seen_at": now,
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return True

    async def get_reviewed_keywords(self, instrument_id: Optional[int] = None) -> List[str]:
        await self._ensure_schema()
        query = select(LearnedKeywordModel.keyword).where(
            LearnedKeywordModel.status.in_(["accepted", "rejected"])
        )
        if instrument_id is not None and instrument_id > 0:
            query = query.where(
                or_(
                    LearnedKeywordModel.instrument_id == instrument_id,
                    LearnedKeywordModel.instrument_id == 0,
                )
            )
        result = await self.session.execute(query)
        return [k.lower() for k in result.scalars().all()]

    @staticmethod
    def _to_entity(model: LearnedKeywordModel) -> LearnedKeyword:
        return LearnedKeyword(
            id=model.id,
            instrument_id=model.instrument_id,
            keyword=model.keyword,
            severity=model.severity,
            occurrence_count=model.occurrence_count,
            first_seen_at=model.first_seen_at,
            last_seen_at=model.last_seen_at,
            status=getattr(model, "status", "accepted") or "accepted",
            failure_indicator=getattr(model, "failure_indicator", None),
            sample_line=getattr(model, "sample_line", None),
            notes=getattr(model, "notes", None),
        )

