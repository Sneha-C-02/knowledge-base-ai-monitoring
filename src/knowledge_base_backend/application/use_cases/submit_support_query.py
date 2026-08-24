from src.knowledge_base_backend.application.models.support_models import SupportQueryResponse
from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GroundedAnswerGenerationService
from src.knowledge_base_backend.domain.services.grounding_context_builder import GroundingContextBuilder
from src.knowledge_base_backend.domain.services.instrument_recognition_service import InstrumentRecognitionService
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError

class SubmitSupportQueryUseCase:
    def __init__(
        self,
        retrieval_service: HybridArticleRetrievalService,
        answer_generator: GroundedAnswerGenerationService,
        context_builder: GroundingContextBuilder,
        instrument_recognition: InstrumentRecognitionService
    ) -> None:
        self.retrieval_service = retrieval_service
        self.answer_generator = answer_generator
        self.context_builder = context_builder
        self.instrument_recognition = instrument_recognition

    async def execute(self, query: str) -> SupportQueryResponse:
        if not query or len(query.strip()) == 0:
            raise ValidationError("Support query cannot be empty")
        
        if len(query) > 1000:
            raise ValidationError("Support query exceeds maximum length")
            
        instrument_name = await self.instrument_recognition.detect_instrument_name(query)
        
        articles = await self.retrieval_service.retrieve_relevant_articles(query, instrument_name, limit=5)
        
        context = self.context_builder.build_context(articles)
        
        answer = await self.answer_generator.generate_grounded_support_answer(query, context)
        
        return SupportQueryResponse(
            answer=answer.answer,
            related_article=answer.related_article_number,
            related_article_url=answer.related_article_url,
            confidence_score=answer.confidence_score
        )
