import pytest

from src.knowledge_base_backend.application.use_cases.discover_failure_keywords import (
    DiscoverFailureKeywordsUseCase,
)


@pytest.mark.asyncio
async def test_discover_failure_keywords_with_patterns_and_indicators() -> None:
    use_case = DiscoverFailureKeywordsUseCase()

    log_content = (
        "Oct 20 11:28:50 [EPC]: Initializing instrument run\n"
        "Oct 20 11:28:55 [EPC]: Pressure limit exceeded on pump module A (pressure=5200 psi)\n"
        "Oct 20 11:29:01 [EPC]: Socket timeout while communicating with detector\n"
        "Oct 20 11:29:10 [EPC]: Needle drive stall detected at carousel position 4\n"
        "Oct 20 11:29:15 [EPC]: Fluidic leak detected around seal wash line\n"
        "Oct 20 11:29:20 [EPC]: Error 0x4B2 occurred in board controller\n"
    )

    result = await use_case.execute([("instrument.log", log_content)])

    assert result.files_scanned == 1
    assert result.total_discovered >= 4

    kw_names = [k.keyword for k in result.keywords]
    assert "pressure limit exceeded" in kw_names
    assert "communication timeout" in kw_names
    assert "needle drive stall" in kw_names
    assert "fluidic leak" in kw_names

    # Check sample lines and indicators
    press_kw = next(k for k in result.keywords if k.keyword == "pressure limit exceeded")
    assert press_kw.severity == "critical"
    assert "pressure" in press_kw.failure_indicator.lower()
    assert press_kw.sample_file == "instrument.log"
    assert press_kw.sample_line_number == 2
    assert "5200 psi" in press_kw.sample_line


@pytest.mark.asyncio
async def test_discover_failure_keywords_empty_and_benign() -> None:
    use_case = DiscoverFailureKeywordsUseCase()

    # Empty files list
    empty_result = await use_case.execute([])
    assert empty_result.total_discovered == 0
    assert empty_result.files_scanned == 0

    # Benign logs without failures
    benign_content = (
        "Oct 20 10:00:00 [EPC]: System online\n"
        "Oct 20 10:01:00 [EPC]: Normal acquisition started\n"
        "Oct 20 10:02:00 [EPC]: Run completed successfully\n"
    )
    benign_result = await use_case.execute([("benign.log", benign_content)])
    assert benign_result.files_scanned == 1
    assert benign_result.total_discovered == 0


class _MockLearnedKeywordRepository:
    def __init__(self, reviewed_keywords: list[str]) -> None:
        self._reviewed = reviewed_keywords

    async def get_reviewed_keywords(self, instrument_id: int = 0) -> list[str]:
        return [k.lower() for k in self._reviewed]

    async def list_accepted_keywords(self, instrument_id: int = 0) -> list:
        return []


@pytest.mark.asyncio
async def test_discover_failure_keywords_filters_reviewed_keywords() -> None:
    # "pressure limit exceeded" and "needle drive stall" are already reviewed (accepted or rejected)
    mock_repo = _MockLearnedKeywordRepository(["pressure limit exceeded", "needle drive stall"])
    use_case = DiscoverFailureKeywordsUseCase(learned_keyword_repository=mock_repo)

    log_content = (
        "Oct 20 11:28:55 [EPC]: Pressure limit exceeded on pump module A (pressure=5200 psi)\n"
        "Oct 20 11:29:01 [EPC]: Socket timeout while communicating with detector\n"
        "Oct 20 11:29:10 [EPC]: Needle drive stall detected at carousel position 4\n"
        "Oct 20 11:29:15 [EPC]: Fluidic leak detected around seal wash line\n"
    )

    result = await use_case.execute([("instrument.log", log_content)])

    kw_names = [k.keyword for k in result.keywords]
    # Filtered out:
    assert "pressure limit exceeded" not in kw_names
    assert "needle drive stall" not in kw_names
    # Kept:
    assert "communication timeout" in kw_names
    assert "fluidic leak" in kw_names

