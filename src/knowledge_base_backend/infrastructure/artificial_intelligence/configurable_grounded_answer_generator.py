from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GroundedAnswerGenerationService, GeneratedSupportAnswer
import httpx

class ConfigurableGroundedAnswerGenerator(GroundedAnswerGenerationService):
    def __init__(self, api_key: str, model_name: str, timeout: int) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def generate_grounded_support_answer(self, query: str, context: str) -> GeneratedSupportAnswer:
        return GeneratedSupportAnswer(
            answer="AI generated response from configurable provider.",
            related_article_number=None,
            related_article_url=None,
            confidence_score=0.8
        )
