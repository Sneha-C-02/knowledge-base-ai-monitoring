import pytest
import io
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from src.knowledge_base_backend.main import app
from src.knowledge_base_backend.presentation.api.dependencies.authentication_dependencies import get_current_user_token
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from src.knowledge_base_backend.domain.entities.knowledge_base_article import KnowledgeBaseArticle
from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GeneratedSupportAnswer
from src.knowledge_base_backend.domain.value_objects.reactive_support_models import SupportFeedback


@pytest.fixture
def override_auth():
    app.dependency_overrides[get_current_user_token] = lambda: "test-token"
    yield
    app.dependency_overrides.pop(get_current_user_token, None)


@pytest.fixture
def mock_feedback_repo():
    repo = AsyncMock()
    repo.get_pattern_weights.return_value = {}

    def fake_save(feedback):
        return SupportFeedback(
            id=1,
            problem_description=feedback.problem_description,
            is_correct=feedback.is_correct,
            log_file=feedback.log_file,
            line_number=feedback.line_number,
            detected_pattern=feedback.detected_pattern,
            feedback_notes=feedback.feedback_notes,
        )

    repo.save.side_effect = fake_save
    repo.get_recent_feedback.return_value = [
        SupportFeedback(
            id=1,
            problem_description="Lost communication with pump",
            is_correct=True,
            log_file="waters.log",
            line_number=3,
            detected_pattern="Socket Timeout Cascade",
            feedback_notes="Accurate match",
        )
    ]
    with app.container.support_feedback_repository.override(repo):
        yield repo


@pytest.mark.asyncio
async def test_investigate_endpoint(override_auth, mock_feedback_repo):
    sample_log = (
        b"Oct 20 10:00:00 [INFO] System initialized\n"
        b"Oct 20 10:01:00 [WARNING] Socket retry 1/5 timed out\n"
        b"Oct 20 10:02:00 [ERROR] Lost communication with pump on port 8080\n"
        b"Oct 20 10:02:05 [ERROR] Communication channel closed\n"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "Lost communication with pump"},
            files=[("logs", ("waters.log", io.BytesIO(sample_log), "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["log_file"] == "waters.log"
        assert data["line_number"] == 3
        assert "Lost communication with pump" in data["matched_line"]
        assert "Communication Retry" in data["pre_incident_pattern"]
        assert len(data["system_changes"]) >= 2
        assert len(data["grounding_citations"]) >= 1
        assert data["confidence_score"] >= 0.7


@pytest.mark.asyncio
async def test_investigate_endpoint_broad_error_query(override_auth, mock_feedback_repo):
    sample_log = (
        b"Oct 20 10:00:00 [INFO] System initialized\n"
        b"Oct 20 10:15:00 [CRITICAL] Safety interlock tripped on Pump high pressure\n"
        b"Oct 20 10:16:00 [INFO] System halted in safe state\n"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "is there any error"},
            files=[("logs", ("waters.log", io.BytesIO(sample_log), "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["log_file"] == "waters.log"
        assert data["line_number"] == 2
        assert data["severity"] == "CRITICAL"
        assert "Safety interlock tripped on Pump high pressure" in data["matched_line"]
        assert "error" not in data["matched_line"].lower()


@pytest.mark.asyncio
async def test_investigate_endpoint_clean_log_broad_error_returns_not_found(override_auth, mock_feedback_repo):
    sample_log = (
        b"Oct 20 10:00:00 [INFO] System initialized normally\n"
        b"Oct 20 10:05:00 [INFO] Flow rate stable at 1.00 mL/min\n"
        b"Oct 20 10:10:00 [INFO] Temperature stable at 35.0 C\n"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "did an error occur"},
            files=[("logs", ("clean.log", io.BytesIO(sample_log), "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False
        assert data["log_file"] is None
        assert data["line_number"] is None
        assert "not found" in data["pre_incident_summary"].lower()


@pytest.mark.asyncio
async def test_investigate_endpoint_component_specificity(override_auth, mock_feedback_repo):
    sample_log = (
        b"Oct 20 09:00:00 [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!\n"
        b"Oct 20 11:20:00 [INFO] Detector diagnostic check started\n"
        b"Oct 20 11:25:00 [WARNING] Detector optical baseline noise exceeds acquisition limit\n"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "detector error"},
            files=[("logs", ("system.log", io.BytesIO(sample_log), "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["line_number"] == 3
        assert "Detector" in data["matched_line"]
        assert "Pump" not in data["matched_line"]


@pytest.mark.asyncio
async def test_investigate_endpoint_unformatted_error_detected(override_auth, mock_feedback_repo):
    sample_log = (
        b"Oct 20 10:00:00 System initialized normally\n"
        b"Oct 20 10:05:00 Ethernet link disconnected\n"
        b"Oct 20 10:10:00 Standby mode active\n"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "is there any error"},
            files=[("logs", ("comm.log", io.BytesIO(sample_log), "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["line_number"] == 2
        assert "disconnected" in data["matched_line"].lower()


@pytest.mark.asyncio
async def test_investigate_endpoint_clean_log_with_installed_words_returns_not_found(override_auth, mock_feedback_repo):
    sample_log = (
        b"Oct 20 10:00:00 [INFO] System boot sequence started\n"
        b"Oct 20 10:05:00 [INFO] Pump seal reinstalled successfully\n"
        b"Oct 20 10:10:00 [INFO] Loading default configuration\n"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "pump error"},
            files=[("logs", ("maintenance.log", io.BytesIO(sample_log), "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False
        assert data["line_number"] is None



@pytest.mark.asyncio
async def test_investigate_endpoint_without_files_raises_validation_error(override_auth, mock_feedback_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "Lost communication with pump"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "log file or folder" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_investigate_endpoint_with_empty_files_raises_validation_error(override_auth, mock_feedback_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "Lost communication with pump"},
            files=[("logs", ("empty.log", io.BytesIO(b""), "text/plain"))],
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "empty" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_investigate_endpoint_with_only_empty_filename_raises_validation_error(override_auth, mock_feedback_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "Lost communication with pump"},
            files=[("logs", ("", io.BytesIO(b"log content here"), "text/plain"))],
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "log file or folder" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_investigate_endpoint_with_whitespace_content_raises_validation_error(override_auth, mock_feedback_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/investigate",
            data={"problem_description": "Lost communication with pump"},
            files=[("logs", ("spaces.log", io.BytesIO(b"   \n\t  "), "text/plain"))],
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "empty" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_support_query_endpoint_without_logs_raises_validation_error(override_auth):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/query",
            json={"query": "Lost communication with pump"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "log file or folder" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_kb_solution_endpoint(override_auth):
    mock_retrieval = AsyncMock()
    article = KnowledgeBaseArticle(
        id="WKB999",
        database_id=99,
        article_number="WKB999",
        title="Pump Communication Lost Troubleshooting",
        searchable_content="Power cycle the module and check ethernet cable connections.",
        url="/article/WKB999",
    )
    mock_retrieval.retrieve_relevant_articles.return_value = [
        RelevantArticleMatch(
            article=article,
            matched_instruments=["ACQUITY UPLC"],
            full_text_score=0.9,
            vector_similarity_score=0.92,
            combined_relevance_score=0.91,
            retrieval_method="hybrid",
            retrieval_reason="Communication match",
        )
    ]

    mock_answer_gen = AsyncMock()
    mock_answer_gen.generate_grounded_support_answer.return_value = GeneratedSupportAnswer(
        answer="Power cycle the pump module and verify cable continuity.",
        related_article_number="WKB999",
        related_article_url="/article/WKB999",
        confidence_score=0.92,
    )

    mock_inst_rec = AsyncMock()
    mock_inst_rec.detect_instrument_name.return_value = "ACQUITY UPLC"

    with app.container.hybrid_retrieval_service.override(mock_retrieval), \
         app.container.answer_generation_service.override(mock_answer_gen), \
         app.container.instrument_recognition_service.override(mock_inst_rec):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/support/kb-solution",
                json={
                    "query": "Lost communication with pump",
                    "matched_log_file": "waters.log",
                    "line_number": 3,
                    "incident_pattern": "Socket Timeout",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "Power cycle the pump" in data["answer"]
            assert len(data["related_articles"]) == 1
            assert data["related_articles"][0]["article_number"] == "WKB999"


@pytest.mark.asyncio
async def test_feedback_submission_endpoint(override_auth, mock_feedback_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/support/feedback",
            json={
                "problem_description": "Lost communication with pump",
                "is_correct": True,
                "log_file": "waters.log",
                "line_number": 3,
                "detected_pattern": "Socket Timeout Cascade",
                "feedback_notes": "Identified exact line accurately",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["is_correct"] is True
        assert "feedback_id" in data


@pytest.mark.asyncio
async def test_recent_feedback_endpoint(override_auth, mock_feedback_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/support/feedback/recent")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["detected_pattern"] == "Socket Timeout Cascade"
