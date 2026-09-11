from src.knowledge_base_backend.domain.services.log_keyword_extractor import LogKeywordExtractor
from src.knowledge_base_backend.domain.services.log_keyword_learning_service import LogKeywordLearningService


def test_learns_only_from_error_and_warning_lines() -> None:
    extractor = LogKeywordExtractor()
    learner = LogKeywordLearningService()

    log_text = "\n".join(
        [
            "Mon Oct 20 11:32:42 AM GMT Summer Time: (EngineerServer): Connection timeout while reading detector",
            "Mon Oct 20 11:32:43 AM GMT Summer Time: (EngineerServer): Acquisition started successfully",
            "Mon Oct 20 11:32:44 AM GMT Summer Time: (EngineerServer): Fatal error in pump controller",
        ]
    )

    events = extractor.extract_from_text(log_text)
    candidates = learner.extract_candidates(events)

    keywords = {c.keyword for c in candidates}
    assert "timeout" in keywords
    assert "fatal" in keywords or "error" in keywords
    # The purely informational "Acquisition started successfully" line must never
    # contribute a keyword candidate.
    assert "acquisition" not in keywords
    assert all(c.severity in {"critical", "warning"} for c in candidates)


def test_rio_status_produces_stable_label_not_variable_status_code() -> None:
    extractor = LogKeywordExtractor()
    learner = LogKeywordLearningService()

    events = extractor.extract_from_text("(EPC): RioStatus => -3 while setting voltage")
    candidates = learner.extract_candidates(events)

    keywords = [c.keyword for c in candidates]
    assert "riostatus error" in keywords
    assert not any("-3" in keyword for keyword in keywords)


def test_normal_operational_lines_produce_no_candidates() -> None:
    extractor = LogKeywordExtractor()
    learner = LogKeywordLearningService()

    events = extractor.extract_from_text("(EPC): status is healthy, all systems nominal")
    candidates = learner.extract_candidates(events)

    assert candidates == []
