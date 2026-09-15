from io import BytesIO

import pytest

from src.knowledge_base_backend.application.use_cases.search_log_keywords import SearchLogKeywordsUseCase
from src.knowledge_base_backend.infrastructure.artificial_intelligence.groq_dashboard_analysis_service import GroqDashboardAnalysisService


class AcceptingValidator:
    def validate_uploaded_log_file(self, filename: str, file_stream: BytesIO) -> None:
        assert filename.endswith((".log", ".txt"))


class ClassifyingService:
    async def classify_keyword_findings(self, findings: list[dict]) -> list[dict]:
        return [
            {
                "is_error": True,
                "rationale": "Test classification",
                "confidence_score": 91,
                "classification_source": "ai",
            }
            for _ in findings
        ]


@pytest.mark.asyncio
async def test_searches_only_requested_terms_with_phrase_boundaries_and_inflections() -> None:
    use_case = SearchLogKeywordsUseCase(AcceptingValidator(), ClassifyingService())

    result = await use_case.execute(
        files=[("instrument.log", b"errors occurred\nmyerror must not match\nconnection lost\n")],
        keywords=["error", "connection lost", "ERROR"],
    )

    assert result.keywords == ["error", "connection lost"]
    assert [(item["keyword"], item["line_number"], item["matched_text"].lower()) for item in result.findings] == [
        ("error", 1, "errors"),
        ("connection lost", 3, "connection lost"),
    ]
    assert all(item["is_error"] for item in result.findings)


@pytest.mark.asyncio
async def test_keyword_classification_uses_deterministic_fallback_when_ai_fails() -> None:
    service = object.__new__(GroqDashboardAnalysisService)

    async def failing_call(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    service._call_groq = failing_call
    classifications = await service.classify_keyword_findings([
        {"keyword": "timeout", "matched_text": "timeout", "context": ["ERROR request timeout"]},
        {"keyword": "status", "matched_text": "status", "context": ["status is healthy"]},
    ])

    assert [item["is_error"] for item in classifications] == [True, False]
    assert classifications[0]["error_type"] is not None
    assert classifications[0]["problem_summary"] is not None
    assert all(item["classification_source"] == "deterministic_fallback" for item in classifications)


class MockRetrievalService:
    async def retrieve_relevant_articles(self, query: str, instrument_name, limit: int = 1):
        from src.knowledge_base_backend.domain.entities.knowledge_base_article import KnowledgeBaseArticle
        from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch

        article = KnowledgeBaseArticle(
            id="kb-123",
            database_id=123,
            article_number="WKB114299",
            title="MassLynx Low Mass Resolution Fix",
            url="https://support.waters.com/kb/WKB114299",
            searchable_content="Resolution adjust error can be fixed by resetting RioStatus register.",
        )
        return [
            RelevantArticleMatch(
                article=article,
                matched_instruments=["ACQUITY"],
                full_text_score=0.92,
                vector_similarity_score=0.88,
                combined_relevance_score=0.90,
                retrieval_method="hybrid",
                retrieval_reason="Exact match for resolution setting error",
            )
        ]


@pytest.mark.asyncio
async def test_search_log_keywords_attaches_kb_article_and_problem_summary() -> None:
    class DetailedClassifyingService:
        async def classify_keyword_findings(self, findings: list[dict]) -> list[dict]:
            return [
                {
                    "is_error": True,
                    "error_type": "Low Mass Resolution Write Failure",
                    "problem_summary": "MS1 Setting failed to write 1024 with RioStatus => -1.",
                    "search_query": "Low Mass Resolution failed write RioStatus",
                    "recommended_action": "Check RioStatus interface connection.",
                    "rationale": "Surrounding lines indicate register write failure.",
                    "confidence_score": 95,
                    "classification_source": "ai",
                }
                for _ in findings
            ]

    use_case = SearchLogKeywordsUseCase(
        validator=AcceptingValidator(),
        ai_service=DetailedClassifyingService(),
        retrieval_service=MockRetrievalService(),
    )

    result = await use_case.execute(
        files=[("log1.txt", b"Line 1\nMS1 Setting failed to write 1024 with RioStatus => -1\nLine 3\n")],
        keywords=["failed"],
    )

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding["is_error"] is True
    assert finding["error_type"] == "Low Mass Resolution Write Failure"
    assert "RioStatus => -1" in finding["problem_summary"]
    assert finding["kb_article"] is not None
    assert finding["kb_article"]["article_number"] == "WKB114299"
    assert finding["kb_article"]["title"] == "MassLynx Low Mass Resolution Fix"
    assert finding["context_start_line"] == 1

