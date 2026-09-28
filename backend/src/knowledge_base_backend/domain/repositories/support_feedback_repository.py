from typing import List, Protocol, Optional, Dict
from src.knowledge_base_backend.domain.value_objects.reactive_support_models import SupportFeedback


class SupportFeedbackRepository(Protocol):
    async def save(self, feedback: SupportFeedback) -> SupportFeedback:
        """Saves a new user verification feedback entry."""
        ...

    async def get_feedback_for_problem(self, problem_description: str, limit: int = 10) -> List[SupportFeedback]:
        """Retrieves past feedback entries matching or related to the problem."""
        ...

    async def get_recent_feedback(self, limit: int = 50) -> List[SupportFeedback]:
        """Retrieves recent feedback entries."""
        ...

    async def get_pattern_weights(self) -> Dict[str, float]:
        """
        Returns a dictionary of pattern/keyword adjustments based on past feedback.
        Positive values indicate patterns verified as correct; negative values indicate
        patterns flagged as incorrect by users.
        """
        ...
