from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GroundedAnswerGenerationService, GeneratedSupportAnswer

class DisabledAnswerGenerationService(GroundedAnswerGenerationService):
    async def generate_grounded_support_answer(self, query: str, context: str) -> GeneratedSupportAnswer:
        return GeneratedSupportAnswer(
            answer="AI Answer Generation is currently disabled. Please review the provided articles for help.",
            related_article_number=None,
            related_article_url=None,
            confidence_score=0.0
        )
