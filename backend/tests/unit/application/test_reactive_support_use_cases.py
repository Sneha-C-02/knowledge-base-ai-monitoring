import pytest
from unittest.mock import AsyncMock, MagicMock

from src.knowledge_base_backend.application.use_cases.investigate_log_incident import InvestigateLogIncidentUseCase
from src.knowledge_base_backend.application.use_cases.submit_support_feedback import SubmitSupportFeedbackUseCase
from src.knowledge_base_backend.application.use_cases.search_kb_for_incident import SearchKbForIncidentUseCase
from src.knowledge_base_backend.domain.value_objects.reactive_support_models import (
    IncidentInvestigationResult,
    SupportFeedback,
)
from src.knowledge_base_backend.domain.services.log_incident_investigation_service import LogIncidentInvestigationService
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError
from src.knowledge_base_backend.domain.entities.knowledge_base_article import KnowledgeBaseArticle
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GeneratedSupportAnswer


@pytest.mark.asyncio
async def test_investigate_log_incident_use_case_success():
    service = LogIncidentInvestigationService()
    mock_feedback_repo = AsyncMock()
    mock_feedback_repo.get_pattern_weights.return_value = {"pressure": 2.0}

    use_case = InvestigateLogIncidentUseCase(
        investigation_service=service,
        feedback_repository=mock_feedback_repo,
    )

    files = [
        (
            "run1.log",
            b"Oct 20 10:00:00 [INFO] System running\nOct 20 10:05:00 [ERROR] Pump pressure exceeded 5000 psi\n",
        )
    ]

    result = await use_case.execute(files, "Pump pressure error")

    assert result.found is True
    assert result.log_file == "run1.log"
    assert result.line_number == 2
    assert "pressure exceeded" in result.matched_line
    mock_feedback_repo.get_pattern_weights.assert_awaited_once()


@pytest.mark.asyncio
async def test_investigate_log_incident_empty_query_raises_validation_error():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    with pytest.raises(ValidationError):
        await use_case.execute([], "   ")


@pytest.mark.asyncio
async def test_investigate_log_incident_empty_files_raises_validation_error():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    with pytest.raises(ValidationError) as exc_info:
        await use_case.execute([], "Pump pressure exceeded")
    assert "log file or folder" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_investigate_log_incident_empty_content_raises_validation_error():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    with pytest.raises(ValidationError) as exc_info:
        await use_case.execute([("empty.log", b"   \n\t  ")], "Pump pressure exceeded")
    assert "empty" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_investigate_log_incident_only_ignored_files_raises_validation_error():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    with pytest.raises(ValidationError) as exc_info:
        await use_case.execute(
            [(".DS_Store", b"\x00\x00\x01"), ("image.png", b"\x89PNG\r\n\x1a\n")],
            "Pump pressure exceeded"
        )
    assert "no valid log files" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_investigate_log_incident_empty_filename_raises_validation_error():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    with pytest.raises(ValidationError) as exc_info:
        await use_case.execute(
            [("", b"Oct 20 [ERROR] Pump issue"), ("   ", b"Oct 20 [ERROR] Pump issue")],
            "Pump issue"
        )
    assert "no valid log files" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_investigate_log_incident_pure_binary_without_null_bytes_raises_validation_error():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    # 1000 bytes consisting solely of control characters < 32 (excluding \t, \n, \r)
    binary_content = bytes([1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 14, 15] * 80)
    with pytest.raises(ValidationError) as exc_info:
        await use_case.execute(
            [("fake.log", binary_content)],
            "Pump issue"
        )
    assert "no valid log files" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_investigate_log_incident_mixed_valid_and_empty_files_succeeds():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    files = [
        ("empty.log", b""),
        ("whitespace.log", b"   \n\t  "),
        ("real.log", b"Oct 20 10:00:00 [ERROR] Pump pressure exceeded 5000 psi\n"),
    ]
    result = await use_case.execute(files, "Pump pressure error")
    assert result.found is True
    assert result.log_file == "real.log"
    assert result.files_scanned == 1



@pytest.mark.asyncio
async def test_submit_support_feedback_use_case_saves_and_learns():
    mock_repo = AsyncMock()
    saved_feedback = SupportFeedback(
        id=42,
        problem_description="Lost communication",
        is_correct=True,
        log_file="comm.log",
        line_number=10,
        detected_pattern="Socket Timeout",
        feedback_notes="Worked perfectly",
    )
    mock_repo.save.return_value = saved_feedback

    mock_coordinator = AsyncMock()

    use_case = SubmitSupportFeedbackUseCase(
        feedback_repository=mock_repo,
        keyword_learning_coordinator=mock_coordinator,
    )

    result = await use_case.execute(
        problem_description="Lost communication",
        is_correct=True,
        log_file="comm.log",
        line_number=10,
        detected_pattern="Socket Timeout",
        feedback_notes="Worked perfectly",
    )

    assert result.id == 42
    assert result.is_correct is True
    mock_repo.save.assert_awaited_once()
    mock_coordinator.learn_from_text.assert_awaited_once_with(
        log_content="Lost communication Socket Timeout",
        instrument_id=0,
    )


@pytest.mark.asyncio
async def test_investigate_log_incident_skips_binary_and_system_files():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    files = [
        (".DS_Store", b"\x00\x00\x00\x01Bud1"),
        ("image.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"),
        ("real_log.log", b"Oct 20 10:00:00 [ERROR] Pump pressure exceeded 5000 psi\n"),
    ]

    result = await use_case.execute(files, "Pump pressure error")

    assert result.found is True
    assert result.log_file == "real_log.log"
    assert result.files_scanned == 1



@pytest.mark.asyncio
async def test_search_kb_for_incident_use_case():
    retrieval_service = AsyncMock()
    article = KnowledgeBaseArticle(
        id="WKB1001",
        database_id=1,
        article_number="WKB1001",
        title="Pump Pressure Troubleshooting",
        searchable_content="Check solvent lines and purge valve for blockages.",
        url="https://waters.com/kb/1001",
    )
    match = RelevantArticleMatch(
        article=article,
        matched_instruments=["ACQUITY UPLC"],
        full_text_score=0.9,
        vector_similarity_score=0.95,
        combined_relevance_score=0.95,
        retrieval_method="hybrid",
        retrieval_reason="Exact match on pump pressure",
    )
    retrieval_service.retrieve_relevant_articles.return_value = [match]

    answer_gen = AsyncMock()
    answer_gen.generate_grounded_support_answer.return_value = GeneratedSupportAnswer(
        answer="Purge the pump lines and check for blockages.",
        related_article_number="WKB1001",
        related_article_url="https://waters.com/kb/1001",
        confidence_score=0.95,
    )

    context_builder = MagicMock()
    context_builder.build_context.return_value = "Context..."

    inst_recog = AsyncMock()
    inst_recog.detect_instrument_name.return_value = "ACQUITY UPLC"

    use_case = SearchKbForIncidentUseCase(
        retrieval_service=retrieval_service,
        answer_generator=answer_gen,
        context_builder=context_builder,
        instrument_recognition=inst_recog,
    )

    response = await use_case.execute(
        query="Pump pressure limit exceeded",
        matched_log_file="system.log",
        incident_pattern="Progressive Pressure Escalation",
    )

    assert "Purge the pump" in response.answer
    assert len(response.related_articles) == 1
    assert response.related_articles[0].article_number == "WKB1001"


@pytest.mark.asyncio
async def test_investigate_use_case_broad_error_query_matches_critical():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    files = [
        (
            "empower.log",
            b"Oct 20 10:00:00 [INFO] Starting run sequence\nOct 20 10:15:00 [CRITICAL] Safety interlock tripped on Pump high pressure\nOct 20 10:16:00 [INFO] System halted\n",
        )
    ]

    result = await use_case.execute(files, "did an error occur")

    assert result.found is True
    assert result.log_file == "empower.log"
    assert result.line_number == 2
    assert result.severity == "CRITICAL"
    assert "Safety interlock tripped on Pump high pressure" in result.matched_line


@pytest.mark.asyncio
async def test_investigate_use_case_broad_error_query_on_clean_logs_returns_not_found():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    files = [
        (
            "clean.log",
            b"Oct 20 10:00:00 [INFO] System initialized\nOct 20 10:05:00 [INFO] Calibration complete\nOct 20 10:10:00 [INFO] Standby mode active\n",
        )
    ]

    result = await use_case.execute(files, "is there any error")

    assert result.found is False
    assert result.log_file is None
    assert result.line_number is None
    assert "not found" in result.pre_incident_summary.lower()


@pytest.mark.asyncio
async def test_investigate_use_case_component_plus_error_specificity():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    files = [
        (
            "pump.log",
            b"Oct 20 09:00:00 [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!\n",
        ),
        (
            "detector.log",
            b"Oct 20 11:20:00 [INFO] Detector online\nOct 20 11:25:00 [WARNING] Detector optical baseline noise exceeds acquisition limit\n",
        ),
    ]

    result = await use_case.execute(files, "detector error")

    assert result.found is True
    assert result.log_file == "detector.log"
    assert result.line_number == 2
    assert "Detector" in result.matched_line
    assert "Pump" not in result.matched_line


@pytest.mark.asyncio
async def test_investigate_use_case_broad_error_with_info_level_failure():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    files = [
        (
            "comm.log",
            b"Oct 20 10:00:00 [INFO] System boot\nOct 20 10:05:00 [INFO] Ethernet disconnected unexpectedly during run\nOct 20 10:10:00 [INFO] Standby mode active\n",
        )
    ]

    result = await use_case.execute(files, "did an error occur")
    assert result.found is True
    assert result.log_file == "comm.log"
    assert result.line_number == 2
    assert "disconnected" in result.matched_line.lower()


@pytest.mark.asyncio
async def test_investigate_use_case_clean_log_with_installed_words_returns_not_found():
    service = LogIncidentInvestigationService()
    use_case = InvestigateLogIncidentUseCase(investigation_service=service)

    files = [
        (
            "maintenance.log",
            b"Oct 20 10:00:00 [INFO] System boot\nOct 20 10:05:00 [INFO] Pump seal reinstalled successfully\nOct 20 10:10:00 [INFO] Loading default configuration\n",
        )
    ]

    res_broad = await use_case.execute(files, "is there any error")
    assert res_broad.found is False
    assert res_broad.log_file is None

    res_pump = await use_case.execute(files, "pump error")
    assert res_pump.found is False
    assert res_pump.log_file is None


