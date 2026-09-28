import pytest
from src.knowledge_base_backend.domain.services.log_incident_investigation_service import LogIncidentInvestigationService


def test_investigate_pinpoints_file_and_line():
    service = LogIncidentInvestigationService()

    file1 = (
        "system_monitor.log",
        """Oct 20 10:00:01 AM [INFO] System initialized normally.
Oct 20 10:05:00 AM [INFO] Flow rate stable at 1.00 mL/min.
Oct 20 10:10:00 AM [INFO] Temperature stable at 35.0 C.
"""
    )
    file2 = (
        "acquity_uplc_errors.log",
        """Oct 20 11:20:00 AM [INFO] Batch sequence started.
Oct 20 11:25:00 AM [WARNING] Pump pressure fluctuation detected: 2500 psi.
Oct 20 11:26:00 AM [WARNING] Pressure rising rapidly: 4200 psi.
Oct 20 11:27:00 AM [WARNING] Pressure approaching upper limit: 5100 psi.
Oct 20 11:28:57 AM [ERROR] Component: Pump - Pressure limit exceeded 5500 psi (Error 1205)
Oct 20 11:29:00 AM [ERROR] Sample acquisition aborted due to overpressure.
Oct 20 11:29:05 AM [ERROR] Pump stopped. Status=FAULT.
"""
    )

    result = service.investigate(
        files=[file1, file2],
        problem_description="Pump pressure limit exceeded error 1205"
    )

    assert result.found is True
    assert result.log_file == "acquity_uplc_errors.log"
    assert result.line_number == 5
    assert "Pressure limit exceeded 5500 psi (Error 1205)" in result.matched_line
    assert result.severity == "ERROR"

    # Pre-incident pattern verification
    assert "Pressure Escalation" in result.pre_incident_pattern
    assert "escalated" in result.pre_incident_summary.lower() or "pressure" in result.pre_incident_summary.lower()

    # System changes verification
    assert len(result.system_changes) >= 2
    err_change = next(c for c in result.system_changes if "Frequency" in c.aspect)
    assert "error" in err_change.change_summary.lower()

    # Grounding evidence (Anti-hallucination)
    assert len(result.grounding_citations) >= 2
    assert result.grounding_citations[0].line_number == 5
    assert result.grounding_citations[0].log_file == "acquity_uplc_errors.log"
    assert result.confidence_score >= 0.8


def test_major_events_mentioned_only_if_matching_problem():
    service = LogIncidentInvestigationService()

    file_logs = (
        "waters_empower.log",
        """2026-09-18 08:00:00 [INFO] System boot.
2026-09-18 09:15:00 [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!
2026-09-18 10:00:00 [INFO] Resumed maintenance.
2026-09-19 14:00:00 [CRITICAL] DATABASE CONNECTION LOST: Disk full on remote server 10.0.0.5.
2026-09-18 09:14:00 [WARNING] Pump pressure oscillating wildly.
2026-09-18 09:14:50 [ERROR] Pump pressure spike 6000 psi causing emergency stop
"""
    )

    # Problem matching Pump overpressure: should match Emergency Stop on Pump, but NOT Database Connection Lost on another day
    result = service.investigate(
        files=[file_logs],
        problem_description="Pump emergency stop due to high pressure"
    )

    assert result.found is True
    assert len(result.major_events) == 1
    assert result.major_events[0].event_type == "Emergency Safety Stop"
    assert "Pump" in result.major_events[0].description
    # Ensure database disk full event was NOT included because it does not match pump problem!
    assert not any("DATABASE" in ev.description for ev in result.major_events)


def test_feedback_weights_influence_ranking():
    service = LogIncidentInvestigationService()

    log_content = (
        "comm.log",
        """Oct 20 12:00:00 [WARNING] Socket ping timeout.
Oct 20 12:00:05 [ERROR] Socket connection failed on port 8080.
Oct 20 12:00:10 [ERROR] Detector lamp energy low.
"""
    )

    # When "socket" is penalized because a user previously marked it as wrong:
    penalized_weights = {"socket": -10.0, "detector": 10.0}
    result = service.investigate(
        files=[log_content],
        problem_description="Device communication warning and detector low",
        pattern_weights=penalized_weights
    )

    assert result.found is True
    # Detector lamp should win because socket was penalized by user feedback
    assert result.line_number == 3
    assert "Detector lamp" in result.matched_line


def test_unfound_problem_refuses_to_hallucinate():
    service = LogIncidentInvestigationService()

    file_logs = (
        "clean.log",
        """Oct 20 10:00:00 [INFO] System idle.
Oct 20 10:01:00 [INFO] Ready for sample.
"""
    )

    result = service.investigate(
        files=[file_logs],
        problem_description="Spectrometer laser exploded with error code 9999"
    )

    assert result.found is False
    assert result.log_file is None
    assert result.line_number is None
    assert "not found" in result.pre_incident_summary.lower()


def test_unfound_problem_with_unrelated_errors_refuses_to_hallucinate():
    service = LogIncidentInvestigationService()

    file_logs = (
        "system_errors.log",
        """Oct 20 10:00:00 [ERROR] License validation retry 1/3
Oct 20 10:01:00 [ERROR] Backup archiving scheduled task completed with warning code 10
Oct 20 10:05:00 [INFO] System operating in idle mode
"""
    )

    # Problem mentions an issue that has NOTHING to do with the errors in the log
    result = service.investigate(
        files=[file_logs],
        problem_description="Autosampler needle mechanism stall during vial injection"
    )

    # Anti-hallucination: MUST NOT falsely grab license or backup error!
    assert result.found is False
    assert result.log_file is None
    assert result.line_number is None
    assert "not found" in result.pre_incident_summary.lower()


def test_feedback_line_penalty_shifts_candidate_pinpoint():
    service = LogIncidentInvestigationService()

    file_logs = (
        "comm.log",
        """Oct 20 12:00:00 [INFO] Starting communication channel
Oct 20 12:00:05 [ERROR] Socket retry 1 of 5 timed out on port 5150
Oct 20 12:00:10 [INFO] Retrying socket connection
Oct 20 12:00:15 [ERROR] Component: Communication - Socket connection failed permanently (Error 5150)
"""
    )

    # Baseline: line 4 has permanent failure and line 2 is an earlier retry
    result_initial = service.investigate(
        files=[file_logs],
        problem_description="Socket timed out error 5150"
    )
    assert result_initial.found is True

    # Suppose user gave negative feedback on the previously selected line:
    wrong_line = result_initial.line_number
    weights = {f"comm.log:{wrong_line}": -100.0}

    result_penalized = service.investigate(
        files=[file_logs],
        problem_description="Socket timed out error 5150",
        pattern_weights=weights
    )

    assert result_penalized.found is True
    # The penalized line must NOT be selected
    assert result_penalized.line_number != wrong_line


def test_major_events_not_matched_if_unrelated_even_in_same_file():
    service = LogIncidentInvestigationService()

    file_logs = (
        "instrument.log",
        """Oct 20 09:00:00 [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!
Oct 20 11:20:00 [INFO] Detector diagnostic check started
Oct 20 11:22:00 [WARNING] Baseline drift detected: 15.2 uAU/min
Oct 20 11:25:00 [ERROR] Detector optical baseline noise exceeds acquisition limit
Oct 20 11:26:00 [INFO] Acquisition halted
"""
    )

    # User problem is about detector baseline drift: Pump emergency stop should NOT match!
    result = service.investigate(
        files=[file_logs],
        problem_description="Detector baseline drift and optical noise"
    )

    assert result.found is True
    assert result.line_number == 4
    # Major event must NOT match because it's for Pump overpressure, not Detector
    assert len(result.major_events) == 0


def test_waters_format_timestamp_same_day_matching():
    service = LogIncidentInvestigationService()

    file_logs = (
        "waters_empower.log",
        """Oct 20 09:15:00 AM [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!
Oct 20 11:28:57 AM [ERROR] Component: Pump - Pressure limit exceeded 5500 psi causing emergency stop
"""
    )

    # Incident is the pressure limit exceeded at 11:28; major event was the emergency stop at 09:15
    result = service.investigate(
        files=[file_logs],
        problem_description="Component Pump pressure limit exceeded 5500 psi"
    )

    assert result.found is True
    assert result.line_number == 2
    assert len(result.major_events) == 1
    assert result.major_events[0].event_type == "Emergency Safety Stop"
    assert result.major_events[0].line_number == 1
    assert "09:15:00" in result.major_events[0].timestamp

