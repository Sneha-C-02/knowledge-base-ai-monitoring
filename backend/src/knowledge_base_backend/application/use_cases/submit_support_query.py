from src.knowledge_base_backend.application.models.support_models import SupportQueryResponse, RelatedArticleDto
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
        
        if len(articles) == 0:
            return SupportQueryResponse(
                answer="No sufficiently relevant knowledge-base article was found for this query.",
                related_articles=[]
            )

        context = self.context_builder.build_context(articles)
        
        answer = await self.answer_generator.generate_grounded_support_answer(query, context)
        
        related_dtos = []
        for match in articles:
            snippet = match.article.searchable_content[:200] + "..." if len(match.article.searchable_content) > 200 else match.article.searchable_content
            dto = RelatedArticleDto(
                article_number=match.article.article_number,
                title=match.article.title,
                article_url=match.article.url,
                snippet=snippet,
                retrieval_reason=match.retrieval_reason,
                relevance_score=float(match.combined_relevance_score)
            )
            related_dtos.append(dto)
        
        return SupportQueryResponse(
            answer=answer.answer,
            related_articles=related_dtos
        )
