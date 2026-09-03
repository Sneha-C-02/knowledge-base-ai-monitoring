from typing import List, Protocol
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class AiLearningFeedback:
    id: int
    pattern_number: str
    ai_recommendation: str
    actual_action: str
    result: bool
    helpful_points: Optional[str]
    created_at: Optional[datetime] = None

class AiLearningFeedbackRepository(Protocol):
    async def save(self, feedback: AiLearningFeedback) -> AiLearningFeedback:
        """Saves a new feedback entry."""
        ...

    async def get_recent_successful_feedback(self, limit: int = 10) -> List[AiLearningFeedback]:
        """Retrieves recent successful (result=True) feedback entries for few-shot learning."""
        ...
