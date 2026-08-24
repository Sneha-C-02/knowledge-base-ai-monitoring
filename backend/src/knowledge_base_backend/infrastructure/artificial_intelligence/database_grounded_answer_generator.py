from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GroundedAnswerGenerationService, GeneratedSupportAnswer

class DatabaseGroundedAnswerGenerator(GroundedAnswerGenerationService):
    async def generate_grounded_support_answer(self, query: str, context: str) -> GeneratedSupportAnswer:
        # Simple extraction instead of AI model
        return GeneratedSupportAnswer(
            answer="Based on the retrieved articles, please consult the knowledge base for specific guidance.",
            related_article_number=None,
            related_article_url=None,
            confidence_score=0.5
        )
