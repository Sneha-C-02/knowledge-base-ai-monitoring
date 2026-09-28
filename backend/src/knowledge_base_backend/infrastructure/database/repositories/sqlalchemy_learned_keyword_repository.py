from datetime import datetime, timezone
from typing import List

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, UniqueConstraint, or_, select
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

    async def record_occurrences(self, instrument_id: int, candidates: List[LearnedKeywordCandidate]) -> None:
        if not candidates:
            return

        await self._schema_ensurer.ensure_table_exists(self.session, LearnedKeywordModel.__table__)

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
        await self._schema_ensurer.ensure_table_exists(self.session, LearnedKeywordModel.__table__)

        query = select(LearnedKeywordModel)
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
        )
