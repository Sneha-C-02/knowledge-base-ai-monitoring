import re
from typing import List, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base
from src.knowledge_base_backend.infrastructure.database.table_schema_ensurer import TableSchemaEnsurer
from src.knowledge_base_backend.domain.value_objects.reactive_support_models import SupportFeedback
from src.knowledge_base_backend.domain.repositories.support_feedback_repository import SupportFeedbackRepository


class ReactiveSupportFeedbackModel(Base):
    __tablename__ = "reactive_support_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_description = Column(Text, nullable=False)
    log_file = Column(String(255), nullable=True)
    line_number = Column(Integer, nullable=True)
    detected_pattern = Column(String(255), nullable=True)
    is_correct = Column(Boolean, nullable=False)
    feedback_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SqlAlchemySupportFeedbackRepository(SupportFeedbackRepository):
    def __init__(self, session: AsyncSession, schema_ensurer: Optional[TableSchemaEnsurer] = None) -> None:
        self.session = session
        self.schema_ensurer = schema_ensurer

    async def _ensure_table(self) -> None:
        if self.schema_ensurer is not None:
            await self.schema_ensurer.ensure_table_exists(self.session, ReactiveSupportFeedbackModel.__table__)

    async def save(self, feedback: SupportFeedback) -> SupportFeedback:
        await self._ensure_table()
        model = ReactiveSupportFeedbackModel(
            problem_description=feedback.problem_description,
            log_file=feedback.log_file,
            line_number=feedback.line_number,
            detected_pattern=feedback.detected_pattern,
            is_correct=feedback.is_correct,
            feedback_notes=feedback.feedback_notes,
        )
        self.session.add(model)
        await self.session.flush()

        feedback.id = model.id
        feedback.created_at = model.created_at
        return feedback

    async def get_feedback_for_problem(self, problem_description: str, limit: int = 10) -> List[SupportFeedback]:
        await self._ensure_table()
        terms = [t.lower() for t in problem_description.split() if len(t) > 3]
        stmt = (
            select(ReactiveSupportFeedbackModel)
            .order_by(desc(ReactiveSupportFeedbackModel.created_at))
            .limit(limit * 3)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        matched = []
        for m in models:
            m_text = (m.problem_description or "").lower()
            if any(term in m_text for term in terms):
                matched.append(
                    SupportFeedback(
                        id=m.id,
                        problem_description=m.problem_description,
                        log_file=m.log_file,
                        line_number=m.line_number,
                        detected_pattern=m.detected_pattern,
                        is_correct=m.is_correct,
                        feedback_notes=m.feedback_notes,
                        created_at=m.created_at,
                    )
                )
                if len(matched) >= limit:
                    break

        return matched

    async def get_recent_feedback(self, limit: int = 50) -> List[SupportFeedback]:
        await self._ensure_table()
        stmt = (
            select(ReactiveSupportFeedbackModel)
            .order_by(desc(ReactiveSupportFeedbackModel.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [
            SupportFeedback(
                id=m.id,
                problem_description=m.problem_description,
                log_file=m.log_file,
                line_number=m.line_number,
                detected_pattern=m.detected_pattern,
                is_correct=m.is_correct,
                feedback_notes=m.feedback_notes,
                created_at=m.created_at,
            )
            for m in models
        ]

    async def get_pattern_weights(self) -> Dict[str, float]:
        """
        Derive dynamic pattern weights and line-specific adjustments from verified feedback.
        - Boosts confirmed patterns, keywords, and specific (file, line) pairs.
        - Penalizes rejected patterns, misleading terms, and incorrect (file, line) pins.
        """
        await self._ensure_table()
        stmt = (
            select(ReactiveSupportFeedbackModel)
            .order_by(desc(ReactiveSupportFeedbackModel.created_at))
            .limit(200)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        weights: Dict[str, float] = {}
        stop_words = {
            "the", "is", "at", "which", "on", "and", "a", "an", "in", "to", "for", "with",
            "of", "by", "from", "as", "about", "my", "our", "their", "user", "chat", "issue",
            "problem", "mentioned", "system", "please", "why", "what", "when", "where", "how",
        }

        for m in models:
            delta = 1.0 if m.is_correct else -1.5

            # 1. Exact log line penalty or boost: "file:line"
            if m.log_file and m.line_number:
                line_key = f"{m.log_file}:{m.line_number}"
                weights[line_key] = weights.get(line_key, 0.0) + (15.0 if m.is_correct else -25.0)

            # 2. Detected pattern key and its constituent keywords
            if m.detected_pattern:
                pat_key = m.detected_pattern.strip().lower()
                weights[pat_key] = weights.get(pat_key, 0.0) + delta

                # Deconstruct into searchable keywords (e.g. 'timeout', 'pressure', 'socket')
                tokens = re.findall(r'[a-zA-Z0-9_\-]+', pat_key)
                for t in tokens:
                    if len(t) > 2 and t not in stop_words:
                        weights[t] = weights.get(t, 0.0) + (delta * 0.5)

            # 3. Problem description keywords
            if m.problem_description:
                prob_tokens = re.findall(r'[a-zA-Z0-9_\-]+', m.problem_description.lower())
                for t in prob_tokens:
                    if len(t) > 3 and t not in stop_words:
                        weights[t] = weights.get(t, 0.0) + (delta * 0.3)

        return weights
