from typing import Optional
from src.knowledge_base_backend.domain.value_objects.reactive_support_models import SupportFeedback
from src.knowledge_base_backend.domain.repositories.support_feedback_repository import SupportFeedbackRepository
from src.knowledge_base_backend.application.services.keyword_learning_coordinator import KeywordLearningCoordinator
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError


class SubmitSupportFeedbackUseCase:
    """
    Saves user verification feedback (correct/wrong) for an AI incident analysis.
    Stores feedback to improve newer searches (updating pattern weights and learned keywords).
    """

    def __init__(
        self,
        feedback_repository: SupportFeedbackRepository,
        keyword_learning_coordinator: Optional[KeywordLearningCoordinator] = None,
    ) -> None:
        self.feedback_repository = feedback_repository
        self.keyword_learning_coordinator = keyword_learning_coordinator

    async def execute(
        self,
        problem_description: str,
        is_correct: bool,
        log_file: Optional[str] = None,
        line_number: Optional[int] = None,
        detected_pattern: Optional[str] = None,
        feedback_notes: Optional[str] = None,
    ) -> SupportFeedback:
        if not problem_description or not problem_description.strip():
            raise ValidationError("Problem description is required to record feedback")

        feedback = SupportFeedback(
            id=0,
            problem_description=problem_description.strip(),
            is_correct=is_correct,
            log_file=log_file,
            line_number=line_number,
            detected_pattern=detected_pattern,
            feedback_notes=feedback_notes.strip() if feedback_notes else None,
        )

        saved = await self.feedback_repository.save(feedback)

        # If user confirmed the analysis as correct, feed relevant error terms into keyword coordinator
        if is_correct and self.keyword_learning_coordinator and detected_pattern:
            try:
                await self.keyword_learning_coordinator.learn_from_text(
                    log_content=f"{problem_description} {detected_pattern}",
                    instrument_id=0,
                )
            except Exception:
                pass

        return saved
