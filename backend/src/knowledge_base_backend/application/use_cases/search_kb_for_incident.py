from typing import Optional, List, Any
from src.knowledge_base_backend.application.models.support_models import SupportQueryResponse, RelatedArticleDto
from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GroundedAnswerGenerationService
from src.knowledge_base_backend.domain.services.grounding_context_builder import GroundingContextBuilder
from src.knowledge_base_backend.domain.services.instrument_recognition_service import InstrumentRecognitionService
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError


class SearchKbForIncidentUseCase:
    """
    Dedicated use case to search Knowledge Base articles for an investigated incident.
    Invoked strictly upon user clicking the 'Search KB Article' button.
    Learns from past feedback to improve newer searches.
    """

    def __init__(
        self,
        retrieval_service: HybridArticleRetrievalService,
        answer_generator: GroundedAnswerGenerationService,
        context_builder: GroundingContextBuilder,
        instrument_recognition: InstrumentRecognitionService,
        feedback_repository: Optional[Any] = None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.answer_generator = answer_generator
        self.context_builder = context_builder
        self.instrument_recognition = instrument_recognition
        self.feedback_repository = feedback_repository

    async def execute(
        self,
        query: str,
        matched_log_file: Optional[str] = None,
        incident_pattern: Optional[str] = None,
        instrument_name: Optional[str] = None,
    ) -> SupportQueryResponse:
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")

        clean_query = query.strip()
        detected_inst = instrument_name or await self.instrument_recognition.detect_instrument_name(clean_query)

        # Check feedback repository to improve search if available
        disallowed_patterns = set()
        if self.feedback_repository:
            try:
                past_feedback = await self.feedback_repository.get_feedback_for_problem(clean_query)
                for fb in past_feedback:
                    if not fb.is_correct and fb.detected_pattern:
                        disallowed_patterns.add(fb.detected_pattern.lower())
            except Exception:
                pass

        # Enhance query with pattern for higher relevance if available and not rejected by past feedback
        search_query = clean_query
        if incident_pattern and incident_pattern.lower() not in search_query.lower():
            if incident_pattern.lower() not in disallowed_patterns:
                search_query = f"{search_query} {incident_pattern}"

        articles = await self.retrieval_service.retrieve_relevant_articles(search_query, detected_inst, limit=5)

        if not articles:
            return SupportQueryResponse(
                answer="No matching knowledge-base article was found for this specific log incident. Please verify the component details or contact Waters support.",
                related_articles=[],
            )

        context = self.context_builder.build_context(articles)
        answer = await self.answer_generator.generate_grounded_support_answer(search_query, context)

        related_dtos: List[RelatedArticleDto] = []
        for match in articles:
            snippet = (
                match.article.searchable_content[:220] + "..."
                if len(match.article.searchable_content) > 220
                else match.article.searchable_content
            )
            dto = RelatedArticleDto(
                article_number=match.article.article_number,
                title=match.article.title,
                article_url=match.article.url or f"/article/{match.article.article_number}",
                snippet=snippet,
                retrieval_reason=match.retrieval_reason,
                relevance_score=float(match.combined_relevance_score),
            )
            related_dtos.append(dto)

        return SupportQueryResponse(
            answer=answer.answer,
            related_articles=related_dtos,
        )
