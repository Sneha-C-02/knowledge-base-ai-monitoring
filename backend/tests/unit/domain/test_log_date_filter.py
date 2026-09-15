from datetime import datetime
from src.knowledge_base_backend.domain.services.log_date_filter import LogDateFilter


def test_filter_lines_without_dates_returns_all_lines() -> None:
    lines = ["line 1", "line 2", "line 3"]
    assert LogDateFilter.filter_lines(lines, None, None) == lines


def test_filter_lines_with_iso_timestamp() -> None:
    lines = [
        "2026-09-01 08:00:00 [INFO] Start",
        "2026-09-01 09:00:00 [INFO] Mid",
        "2026-09-01 10:00:00 [INFO] End",
    ]
    date_from = datetime(2026, 9, 1, 8, 30)
    date_to = datetime(2026, 9, 1, 9, 30)
    filtered = LogDateFilter.filter_lines(lines, date_from, date_to)
    assert filtered == ["2026-09-01 09:00:00 [INFO] Mid"]


def test_filter_lines_with_instrument_format_without_year() -> None:
    lines = [
        "Mon Oct 20 11:27:02 AM GMT Summer Time: Log file opened.",
        "Mon Oct 20 11:45:00 AM GMT Summer Time: MSInterface called.",
        "Mon Oct 20 12:15:00 PM GMT Summer Time: Run finished.",
    ]
    date_from = datetime(2026, 10, 20, 11, 30)
    date_to = datetime(2026, 10, 20, 12, 0)
    filtered = LogDateFilter.filter_lines(lines, date_from, date_to)
    assert filtered == ["Mon Oct 20 11:45:00 AM GMT Summer Time: MSInterface called."]


def test_lines_without_parseable_timestamp_are_preserved() -> None:
    lines = [
        "2026-09-01 08:00:00 [INFO] Start",
        "   at com.waters.acquisition.Engine.run(Engine.java:42)",
        "2026-09-01 10:00:00 [INFO] End",
    ]
    date_from = datetime(2026, 9, 1, 7, 30)
    date_to = datetime(2026, 9, 1, 8, 30)
    filtered = LogDateFilter.filter_lines(lines, date_from, date_to)
    assert "2026-09-01 08:00:00 [INFO] Start" in filtered
    assert "   at com.waters.acquisition.Engine.run(Engine.java:42)" in filtered
    assert "2026-09-01 10:00:00 [INFO] End" not in filtered
