import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.knowledge_base_backend.application.services.continuous_monitoring_service import (
    ContinuousMonitoringService,
)
from src.knowledge_base_backend.domain.value_objects.log_dashboard_result import (
    DashboardFinding,
    DashboardSummaryBullet,
    LogDashboardResult,
)
from src.knowledge_base_backend.application.use_cases.analyze_logs_with_memory import (
    AnalyzeLogsWithMemoryUseCase,
)


@pytest.mark.asyncio
async def test_continuous_monitoring_calls_process_single_file_with_fast_mode() -> None:
    """Verify ContinuousMonitoringService calls _process_single_file with analysis_mode='fast' and publishes to event bus."""
    # Mock monitored file model
    monitored_model = MagicMock()
    monitored_model.instrument_id = 42
    monitored_model.filename = "instrument.log"
    monitored_model.total_lines_analyzed = 10

    # Mock instrument model
    instrument_model = MagicMock()
    instrument_model.id = 42
    instrument_model.name = "Test ACQUITY UPLC"

    # Mock storage
    mock_storage = MagicMock()
    mock_storage.get_file_path = AsyncMock(return_value="/tmp/test_file.log")

    # Mock file content with 15 lines (5 new lines)
    file_content = "\n".join([f"Line {i}" for i in range(15)])

    # Mock use case
    mock_use_case = MagicMock()
    dummy_result = LogDashboardResult(
        instrument_id=42,
        instrument_name="Test ACQUITY UPLC",
        critical_incidents=1,
        warnings=0,
        errors=1,
        healthy_apps=5,
        files_analyzed=1,
        daily_summary_bullets=[DashboardSummaryBullet(text="Test bullet", severity="critical")],
        complete_findings=[
            DashboardFinding(
                filename="instrument.log",
                line_number=12,
                snippet="Line 12: RioStatus => -1",
                severity="critical",
                explanation="Hardware bus error",
                simple_summary="The low-level FPGA/RIO hardware controller reported a hardware bus error.",
            )
        ],
    )
    mock_use_case._process_single_file = AsyncMock(return_value=dummy_result)

    # Mock event bus
    mock_event_bus = MagicMock()
    mock_event_bus.publish = AsyncMock()

    # Mock session
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    # Session execute returns:
    # 1. monitored files query
    # 2. memory entries query
    # 3. instrument query
    scalar_result_monitored = MagicMock()
    scalar_result_monitored.scalars().all.return_value = [monitored_model]

    scalar_result_mem = MagicMock()
    scalar_result_mem.scalars().all.return_value = []

    scalar_result_inst = MagicMock()
    scalar_result_inst.scalar_one.return_value = instrument_model

    mock_session.execute.side_effect = [
        scalar_result_monitored,
        scalar_result_mem,
        scalar_result_inst,
    ]
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    # Session factory context manager
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=session_cm)

    service = ContinuousMonitoringService(
        session_factory=mock_session_factory,
        storage=mock_storage,
        analyze_use_case_factory=lambda: mock_use_case,
        event_bus=mock_event_bus,
        polling_interval_seconds=10,
    )

    with patch("os.path.exists", return_value=True), \
         patch("aiofiles.open", create=True) as mock_aiofiles:
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_aiofiles.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_aiofiles.return_value.__aexit__ = AsyncMock(return_value=None)

        await service._check_files()

    # Assert _process_single_file was called with analysis_mode='fast'
    mock_use_case._process_single_file.assert_awaited_once_with(
        path="/tmp/test_file.log",
        filename="instrument.log",
        instrument_id=42,
        instrument_name="Test ACQUITY UPLC",
        memory_entries=[],
        analysis_mode="fast",
    )

    # Assert event was published to the correct topic
    mock_event_bus.publish.assert_awaited_once_with("42", dummy_result)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_continuous_monitoring_rollbacks_on_failure() -> None:
    """Verify ContinuousMonitoringService catches file exceptions, rolls back session, and stays resilient."""
    monitored_model = MagicMock()
    monitored_model.instrument_id = 99
    monitored_model.filename = "broken.log"
    monitored_model.total_lines_analyzed = 5

    mock_storage = MagicMock()
    mock_storage.get_file_path = AsyncMock(return_value="/tmp/broken.log")

    mock_session = AsyncMock()
    scalar_result_monitored = MagicMock()
    scalar_result_monitored.scalars().all.return_value = [monitored_model]
    mock_session.execute = AsyncMock(return_value=scalar_result_monitored)
    mock_session.rollback = AsyncMock()

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=session_cm)

    service = ContinuousMonitoringService(
        session_factory=mock_session_factory,
        storage=mock_storage,
        analyze_use_case_factory=MagicMock(),
        event_bus=MagicMock(),
        polling_interval_seconds=10,
    )

    with patch("os.path.exists", return_value=True), \
         patch("aiofiles.open", side_effect=IOError("Corrupt disk block")):
        # Must not raise unhandled exception
        await service._check_files()

    mock_session.rollback.assert_awaited_once()


def test_simple_ai_summary_generation() -> None:
    """Verify _generate_simple_ai_summary converts technical diagnostic logs to technician plain English."""
    # Socket / comms timeout
    comm_summary = AnalyzeLogsWithMemoryUseCase._generate_simple_ai_summary(
        "Oct 20 11:32:00 [EPC]: Socket timeout while communicating with detector module", "critical"
    )
    assert "network or communication timeout" in comm_summary.lower()

    # Pressure limit exceeded
    pressure_summary = AnalyzeLogsWithMemoryUseCase._generate_simple_ai_summary(
        "Oct 20 11:35:10 [EPC]: Pressure limit exceeded on pump A (exceeded max pressure 6000 psi)", "critical"
    )
    assert "pressure exceeded the safe operating limit" in pressure_summary.lower()

    # Fluidic leak
    leak_summary = AnalyzeLogsWithMemoryUseCase._generate_simple_ai_summary(
        "Oct 20 11:36:00 [EPC]: Leak detected around column compartment tray", "critical"
    )
    assert "leak or sudden loss of mobile phase pressure" in leak_summary.lower()

    # Vacuum fault
    vacuum_summary = AnalyzeLogsWithMemoryUseCase._generate_simple_ai_summary(
        "Oct 20 11:37:00 [EPC]: Turbo pump vacuum error reading 1.2e-4 mbar", "critical"
    )
    assert "vacuum level degraded" in vacuum_summary.lower()

    # Autosampler needle stall
    needle_summary = AnalyzeLogsWithMemoryUseCase._generate_simple_ai_summary(
        "Oct 20 11:38:00 [EPC]: Autosampler needle drive stall at vial position 12", "critical"
    )
    assert "autosampler mechanism encountered a mechanical obstruction" in needle_summary.lower()

    # Lamp ignition failure
    lamp_summary = AnalyzeLogsWithMemoryUseCase._generate_simple_ai_summary(
        "Oct 20 11:39:00 [EPC]: Deuterium lamp ignition failed after 3 retries", "error"
    )
    assert "lamp failed to ignite" in lamp_summary.lower()

    # RIO status bus error
    rio_summary = AnalyzeLogsWithMemoryUseCase._generate_simple_ai_summary(
        "Oct 20 11:40:00 [EPC]: RioStatus => -1 error writing register", "critical"
    )
    assert "rio hardware controller reported a hardware bus error" in rio_summary.lower()
