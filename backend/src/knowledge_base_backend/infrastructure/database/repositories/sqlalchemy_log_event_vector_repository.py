from typing import List
from sqlalchemy import Column, BigInteger, Text, DateTime, ARRAY, String, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone

from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base
from src.knowledge_base_backend.domain.repositories.log_event_vector_repository import (
    LogEventVectorRepository,
    LogEventVectorRecord,
    LogEventVectorMatch,
)


class LogEventVectorModel(Base):
    __tablename__ = "log_event_vectors"

    id               = Column(BigInteger, primary_key=True)
    instrument_id    = Column(BigInteger, nullable=False)
    log_filename     = Column(Text, nullable=False)
    severity         = Column(Text, nullable=False)
    component        = Column(Text, nullable=True)
    cleaned_text     = Column(Text, nullable=False)
    raw_log_line     = Column(Text, nullable=False)
    matched_patterns = Column(ARRAY(String), nullable=True)
    event_embedding  = Column(Vector(384), nullable=True)
    captured_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SqlAlchemyLogEventVectorRepository(LogEventVectorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_batch(self, records: List[LogEventVectorRecord]) -> int:
        if not records:
            return 0

        models = [
            LogEventVectorModel(
                instrument_id=r.instrument_id,
                log_filename=r.log_filename,
                severity=r.severity,
                component=r.component,
                cleaned_text=r.cleaned_text,
                raw_log_line=r.raw_log_line,
                matched_patterns=r.matched_patterns,
                event_embedding=r.event_embedding,
            )
            for r in records
        ]
        self.session.add_all(models)
        await self.session.flush()
        return len(models)

    async def search_by_vector(
        self,
        query_embedding: List[float],
        min_similarity: float = 0.6,
        limit: int = 5,
        instrument_id: int | None = None,
        severity_filter: str | None = None,
    ) -> List[LogEventVectorMatch]:
        # Build cosine-similarity expression: 1 - (embedding <=> query)
        embedding_col = LogEventVectorModel.event_embedding
        similarity_expr = (1 - embedding_col.op("<=>")(query_embedding)).label("similarity")

        stmt = (
            self.session.query(LogEventVectorModel, similarity_expr)
            .filter(LogEventVectorModel.event_embedding.isnot(None))
        )

        if instrument_id is not None:
            stmt = stmt.filter(LogEventVectorModel.instrument_id == instrument_id)
        if severity_filter is not None:
            stmt = stmt.filter(LogEventVectorModel.severity == severity_filter)

        stmt = (
            stmt
            .having(similarity_expr >= min_similarity)
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        rows = (await self.session.execute(stmt)).all()

        return [
            LogEventVectorMatch(
                id=model.id,
                instrument_id=model.instrument_id,
                log_filename=model.log_filename,
                severity=model.severity,
                component=model.component,
                cleaned_text=model.cleaned_text,
                raw_log_line=model.raw_log_line,
                matched_patterns=model.matched_patterns or [],
                similarity_score=float(sim),
                captured_at=model.captured_at,
            )
            for model, sim in rows
        ]
