from typing import List
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base
from src.knowledge_base_backend.domain.repositories.ai_learning_feedback_repository import AiLearningFeedbackRepository, AiLearningFeedback
from datetime import datetime, timezone

class AiLearningFeedbackModel(Base):
    __tablename__ = "ai_learning_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_number = Column(String(255), nullable=False)
    ai_recommendation = Column(Text, nullable=False)
    actual_action = Column(Text, nullable=False)
    result = Column(Boolean, nullable=False)
    helpful_points = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class SqlAlchemyAiLearningFeedbackRepository(AiLearningFeedbackRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, feedback: AiLearningFeedback) -> AiLearningFeedback:
        model = AiLearningFeedbackModel(
            pattern_number=feedback.pattern_number,
            ai_recommendation=feedback.ai_recommendation,
            actual_action=feedback.actual_action,
            result=feedback.result,
            helpful_points=feedback.helpful_points
        )
        self.session.add(model)
        await self.session.flush()
        
        feedback.id = model.id
        feedback.created_at = model.created_at
        return feedback

    async def get_recent_successful_feedback(self, limit: int = 10) -> List[AiLearningFeedback]:
        stmt = (
            select(AiLearningFeedbackModel)
            .where(AiLearningFeedbackModel.result == True)
            .order_by(desc(AiLearningFeedbackModel.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [
            AiLearningFeedback(
                id=m.id,
                pattern_number=m.pattern_number,
                ai_recommendation=m.ai_recommendation,
                actual_action=m.actual_action,
                result=m.result,
                helpful_points=m.helpful_points,
                created_at=m.created_at
            ) for m in models
        ]
