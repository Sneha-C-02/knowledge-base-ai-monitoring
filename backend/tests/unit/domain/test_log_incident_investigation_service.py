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


# ===========================================================================
# Broad Error Intent & Error Situation Taxonomy Unit Tests
# ===========================================================================

def test_broad_error_query_matches_critical_without_word_error():
    service = LogIncidentInvestigationService()
    file_logs = (
        "instrument.log",
        """Oct 20 11:20:00 AM [INFO] Routine batch run in progress.
Oct 20 11:30:00 AM [CRITICAL] Safety interlock tripped on Pump high pressure
Oct 20 11:31:00 AM [INFO] System entering safe shutdown.
"""
    )

    result = service.investigate(
        files=[file_logs],
        problem_description="is there any error"
    )

    assert result.found is True
    assert result.log_file == "instrument.log"
    assert result.line_number == 2
    assert result.severity == "CRITICAL"
    assert "Safety interlock tripped on Pump high pressure" in result.matched_line
    # Verifies key incident line does not need the literal word "error"
    assert "error" not in result.matched_line.lower()


def test_broad_error_query_matches_fatal_without_word_error():
    service = LogIncidentInvestigationService()
    file_logs = (
        "network.log",
        """2026-09-18 14:00:00 [INFO] Connecting to remote host 10.0.0.5...
2026-09-18 14:00:15 [FATAL] Connection timed out after 3 retries, socket unreachable
2026-09-18 14:00:20 [INFO] Session terminated.
"""
    )

    result = service.investigate(
        files=[file_logs],
        problem_description="did an error occur"
    )

    assert result.found is True
    assert result.log_file == "network.log"
    assert result.line_number == 2
    assert result.severity == "CRITICAL"
    assert "Connection timed out after 3 retries" in result.matched_line
    assert "error" not in result.matched_line.lower()


def test_broad_error_query_matches_failed_without_word_error():
    service = LogIncidentInvestigationService()
    file_logs = (
        "column.log",
        """Oct 20 14:00:00 [INFO] Column oven self-calibration initiated.
Oct 20 14:00:05 [ALERT] Column heater thermal sensor FAILED self-test
Oct 20 14:00:10 [INFO] Calibration aborted.
"""
    )

    result = service.investigate(
        files=[file_logs],
        problem_description="check for errors in log"
    )

    assert result.found is True
    assert result.log_file == "column.log"
    assert result.line_number == 2
    assert "FAILED" in result.matched_line
    assert "error" not in result.matched_line.lower()


def test_broad_error_query_matches_exception_without_word_error():
    service = LogIncidentInvestigationService()
    file_logs = (
        "autosampler.log",
        """Oct 20 15:30:00 [INFO] Preparing sample tray carousel.
Oct 20 15:30:05 [ALERT] Unhandled NullPointer EXCEPTION in autosampler injector thread
Oct 20 15:30:10 [INFO] Injector idle.
"""
    )

    result = service.investigate(
        files=[file_logs],
        problem_description="what error occurred"
    )

    assert result.found is True
    assert result.log_file == "autosampler.log"
    assert result.line_number == 2
    assert "EXCEPTION" in result.matched_line
    assert "error" not in result.matched_line.lower()


def test_broad_error_query_matches_timeout_without_word_error():
    service = LogIncidentInvestigationService()
    file_logs = (
        "comm.log",
        """Oct 20 16:45:00 [INFO] Socket keepalive ping sent.
Oct 20 16:45:05 [WARN] Socket ping TIMEOUT after 5000ms, communication dropped
Oct 20 16:45:10 [INFO] Retrying link.
"""
    )

    result = service.investigate(
        files=[file_logs],
        problem_description="any failure reported"
    )

    assert result.found is True
    assert result.log_file == "comm.log"
    assert result.line_number == 2
    assert "TIMEOUT" in result.matched_line
    assert "error" not in result.matched_line.lower()


def test_component_plus_error_specificity_matches_detector_without_word_error():
    service = LogIncidentInvestigationService()
    file_logs = (
        "multi_subsystem.log",
        """Oct 20 09:00:00 [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!
Oct 20 11:20:00 [INFO] Detector diagnostic check started.
Oct 20 11:22:00 [WARNING] Optical baseline drift detected: 15.2 uAU/min
Oct 20 11:25:00 [WARNING] Detector optical baseline noise exceeds acquisition limit
Oct 20 11:30:00 [INFO] Diagnostic finished.
"""
    )

    # When user asks for "detector error", system must pinpoint detector line, NOT pump emergency stop
    result = service.investigate(
        files=[file_logs],
        problem_description="detector error"
    )

    assert result.found is True
    assert result.line_number in (3, 4)
    assert "Pump" not in result.matched_line
    assert "error" not in result.matched_line.lower()
    assert any(term in result.matched_line.lower() for term in ("detector", "optical", "drift", "noise"))


def test_component_plus_error_specificity_matches_pump():
    service = LogIncidentInvestigationService()
    file_logs = (
        "multi_subsystem.log",
        """Oct 20 09:00:00 [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!
Oct 20 11:20:00 [INFO] Detector diagnostic check started.
Oct 20 11:22:00 [WARNING] Optical baseline drift detected: 15.2 uAU/min
Oct 20 11:25:00 [WARNING] Detector optical baseline noise exceeds acquisition limit
Oct 20 11:30:00 [INFO] Diagnostic finished.
"""
    )

    result = service.investigate(
        files=[file_logs],
        problem_description="pump error"
    )

    assert result.found is True
    assert result.line_number == 1
    assert "Pump" in result.matched_line


def test_error_around_timestamp_specificity():
    service = LogIncidentInvestigationService()
    file_logs = (
        "timeline.log",
        """Oct 20 09:15:00 [ERROR] Early morning communication drop on socket 5000
Oct 20 11:28:57 [CRITICAL] Safety interlock tripped on Pump high pressure
Oct 20 15:40:00 [ERROR] Late afternoon solvent degasser warning
"""
    )

    result = service.investigate(
        files=[file_logs],
        problem_description="error around 11:28"
    )

    assert result.found is True
    assert result.line_number == 2
    assert "11:28:57" in result.matched_line


def test_clean_logs_return_not_found_for_broad_error_queries():
    service = LogIncidentInvestigationService()
    clean_logs = (
        "clean_run.log",
        """Oct 20 10:00:01 AM [INFO] System initialized normally.
Oct 20 10:05:00 AM [INFO] Flow rate stable at 1.00 mL/min.
Oct 20 10:10:00 AM [INFO] Temperature stable at 35.0 C.
Oct 20 10:15:00 AM [INFO] Sample acquisition completed successfully.
"""
    )

    queries = [
        "did any error occur",
        "is there any error",
        "check for errors in log",
        "what error occurred",
        "were there any failures",
        "check log for faults",
    ]

    for q in queries:
        res = service.investigate(files=[clean_logs], problem_description=q)
        assert res.found is False, f"Expected found=False for clean log with query '{q}'"
        assert res.log_file is None
        assert res.line_number is None
        assert "not found" in res.pre_incident_summary.lower()


def test_clean_logs_with_benign_negations_refuse_to_hallucinate():
    service = LogIncidentInvestigationService()
    benign_logs = (
        "diagnostic.log",
        """Oct 20 10:00:00 [INFO] System self-test: 0 errors detected.
Oct 20 10:01:00 [INFO] Error handling subsystem initialized and active.
Oct 20 10:02:00 [INFO] Normal disconnect of idle socket upon batch end.
Oct 20 10:03:00 [INFO] Leak sensor test status OK: no error.
Oct 20 10:04:00 [INFO] Alarm indicator check passed: 0 alarms active.
"""
    )

    queries = [
        "did any error occur",
        "check for errors",
        "is there an error",
        "any issues found",
    ]

    for q in queries:
        res = service.investigate(files=[benign_logs], problem_description=q)
        assert res.found is False, f"Expected found=False for benign negation log with query '{q}'"
        assert res.log_file is None
        assert res.line_number is None
        assert "not found" in res.pre_incident_summary.lower()


def test_error_synonyms_expand_intent_correctly():
    service = LogIncidentInvestigationService()
    file_logs = (
        "incident.log",
        """Oct 20 10:00:00 [INFO] System running normally.
Oct 20 10:10:00 [ALERT] Hardware malfunction: autosampler plunger motor stall
Oct 20 10:15:00 [INFO] Safe mode engaged.
"""
    )

    # Test "issue" (not discarded as stop word)
    res_issue = service.investigate(files=[file_logs], problem_description="what is the issue")
    assert res_issue.found is True
    assert res_issue.line_number == 2

    # Test "problem" (not discarded as stop word)
    res_prob = service.investigate(files=[file_logs], problem_description="check log for problems")
    assert res_prob.found is True
    assert res_prob.line_number == 2

    # Test "fault"
    res_fault = service.investigate(files=[file_logs], problem_description="did any fault occur")
    assert res_fault.found is True
    assert res_fault.line_number == 2

    # Test "breakdown"
    res_break = service.investigate(files=[file_logs], problem_description="was there a breakdown")
    assert res_break.found is True
    assert res_break.line_number == 2


def test_conversational_broad_error_queries_on_clean_logs_refuse_to_hallucinate():
    """Verify that natural phrasing like 'can you check if any error occurred' or 'did anything fail' correctly return found=False."""
    service = LogIncidentInvestigationService()
    clean_logs = (
        "system_idle.log",
        """Oct 20 10:00:00 [INFO] System initialized.
Oct 20 10:01:00 [INFO] Normal disconnect of idle socket upon batch end.
Oct 20 10:02:00 [INFO] Self-test complete: 0 warnings.
Oct 20 10:03:00 [INFO] Idle standby status OK.
"""
    )

    conversational_queries = [
        "can you check if any error occurred",
        "did anything fail",
        "were there any errors today",
        "what went wrong",
        "look for errors in log",
        "review log for errors",
        "check whether any error occurred",
        "did something crash",
        "is any error present in the log",
    ]

    for q in conversational_queries:
        res = service.investigate(files=[clean_logs], problem_description=q)
        assert res.found is False, f"Expected found=False for query '{q}' on clean log with disconnect line"
        assert res.log_file is None
        assert res.line_number is None
        assert "not found" in res.pre_incident_summary.lower()


def test_clean_component_logs_refuse_to_hallucinate_on_component_error_query():
    """Verify that 'detector error' on a clean detector log with only normal INFO passed lines returns found=False."""
    service = LogIncidentInvestigationService()
    clean_detector_logs = (
        "detector_normal.log",
        """Oct 20 10:00:00 [INFO] System initialized.
Oct 20 10:01:00 [INFO] Detector diagnostic check started.
Oct 20 10:02:00 [INFO] Detector baseline calibration passed.
Oct 20 10:03:00 [INFO] Diagnostic complete.
"""
    )

    res = service.investigate(files=[clean_detector_logs], problem_description="detector error")
    assert res.found is False, "Expected found=False when detector log has only normal INFO lines"
    assert res.log_file is None
    assert res.line_number is None
    assert "not found" in res.pre_incident_summary.lower()


def test_subsystem_isolation_prevents_competing_component_hijacking():
    """Verify that pump emergency stops do not hijack specific degasser or comm error queries."""
    service = LogIncidentInvestigationService()
    multi_log = (
        "instrument_faults.log",
        """Oct 20 09:00:00 [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!
Oct 20 10:00:00 [ERROR] Solvent degasser vacuum decay rate exceeded
Oct 20 10:05:00 [ERROR] Communication timeout on socket port 8080
Oct 20 10:10:00 [WARNING] Minor solvent leak detected at seal
"""
    )

    # Degasser query pinpoints degasser line
    res_degasser = service.investigate(files=[multi_log], problem_description="degasser error")
    assert res_degasser.found is True
    assert res_degasser.line_number == 2
    assert "degasser" in res_degasser.matched_line.lower()

    # Comm query pinpoints comm line
    res_comm = service.investigate(files=[multi_log], problem_description="comm error")
    assert res_comm.found is True
    assert res_comm.line_number == 3
    assert "communication" in res_comm.matched_line.lower()

    # Leak query pinpoints leak line
    res_leak = service.investigate(files=[multi_log], problem_description="leak error")
    assert res_leak.found is True
    assert res_leak.line_number == 4
    assert "leak" in res_leak.matched_line.lower()


def test_multiple_simultaneous_critical_failures_tie_breaking():
    """Verify deterministic resolution when multiple critical failures occur in the log."""
    service = LogIncidentInvestigationService()
    log_content = (
        "simultaneous.log",
        """Oct 20 10:00:00 [CRITICAL] EMERGENCY STOP: Safety interlock tripped on Pump high pressure!
Oct 20 10:00:00 [CRITICAL] Hardware malfunction: Autosampler plunger motor stall
"""
    )

    # Broad query picks the highest ranked critical incident deterministically
    res_broad = service.investigate(files=[log_content], problem_description="did an error occur")
    assert res_broad.found is True
    assert res_broad.severity == "CRITICAL"
    assert res_broad.line_number in (1, 2)

    # Subsystem specific query breaks tie accurately
    res_pump = service.investigate(files=[log_content], problem_description="pump error")
    assert res_pump.found is True
    assert res_pump.line_number == 1

    res_autosampler = service.investigate(files=[log_content], problem_description="autosampler error")
    assert res_autosampler.found is True
    assert res_autosampler.line_number == 2


def test_all_20_error_synonyms_trigger_error_intent_and_find_incident():
    """Verify all 20 error terms specified in the taxonomy trigger error intent and pinpoint non-literal incident lines."""
    service = LogIncidentInvestigationService()
    log_content = (
        "system_incident.log",
        """Oct 20 10:00:00 [INFO] System initialized normally.
Oct 20 10:10:00 [ALERT] Safety interlock tripped on Pump high pressure!
Oct 20 10:15:00 [INFO] Safe shutdown complete.
"""
    )

    all_20_terms = [
        "error", "errors", "failure", "failed", "fail", "fault", "faults",
        "exception", "exceptions", "crash", "crashed", "alarm", "alarms",
        "breakdown", "abort", "aborted", "timeout", "timed out",
        "malfunction", "problem", "issue"
    ]

    for term in all_20_terms:
        # Test broad inquiry formulation with the term
        query = f"did any {term} occur" if not term.endswith("ed") else f"did the system get {term}"
        res = service.investigate(files=[log_content], problem_description=query)
        assert res.found is True, f"Failed for error term '{term}' with query '{query}'"
        assert res.line_number == 2, f"Failed to pinpoint line 2 for term '{term}'"
        assert res.log_file == "system_incident.log"
        assert "interlock tripped" in res.matched_line.lower()


def test_all_26_error_situation_indicators_in_logs_detected_by_broad_query():
    """Verify that every one of the 26 error-situation indicators is recognized by a broad query even when logged under INFO."""
    service = LogIncidentInvestigationService()

    all_26_indicators = [
        "error", "fail", "failed", "failure", "exception", "critical", "fatal", "panic",
        "emergency", "abort", "aborted", "timeout", "timed out", "alarm", "interlock",
        "tripped", "disconnect", "disconnected", "lost", "offline", "unreachable",
        "refused", "corrupt", "corruption", "leak", "overpressure", "stalled"
    ]

    for ind in all_26_indicators:
        log_content = (
            f"test_{ind}.log",
            f"""Oct 20 10:00:00 [INFO] Calibration routine started.
Oct 20 10:05:00 [INFO] Subsystem: {ind} event recorded during run.
Oct 20 10:10:00 [INFO] Diagnostic mode ended.
"""
        )

        res = service.investigate(files=[log_content], problem_description="did an error occur")
        assert res.found is True, f"Failed to detect indicator '{ind}' with broad error query"
        assert res.line_number == 2, f"Failed to pinpoint line 2 for indicator '{ind}'"
        assert ind in res.matched_line.lower()


def test_multi_file_investigation_with_clean_and_incident_files():
    """Verify that multi-file log investigation correctly isolates the error file and ignores clean files."""
    service = LogIncidentInvestigationService()

    clean_file1 = (
        "routine_monitor.log",
        """Oct 20 08:00:00 [INFO] System monitoring thread started.
Oct 20 08:30:00 [INFO] All instrument telemetry normal.
Oct 20 09:00:00 [INFO] Routine heartbeat ok.
"""
    )
    clean_file2 = (
        "sample_queue.log",
        """Oct 20 08:00:00 [INFO] Queue processor active.
Oct 20 08:15:00 [INFO] Vial tray 1 loaded: 96 samples ready.
Oct 20 08:30:00 [INFO] Batch progression normal.
"""
    )
    incident_file = (
        "comm_bus.log",
        """Oct 20 08:00:00 [INFO] Ethernet comm channel opened.
Oct 20 08:45:00 [CRITICAL] Remote socket unreachable: connection refused by controller
Oct 20 08:45:05 [INFO] Channel closed.
"""
    )

    # Broad error inquiry correctly identifies comm_bus.log line 2
    res = service.investigate(
        files=[clean_file1, clean_file2, incident_file],
        problem_description="is there any error"
    )

    assert res.found is True
    assert res.log_file == "comm_bus.log"
    assert res.line_number == 2
    assert "unreachable" in res.matched_line.lower() or "refused" in res.matched_line.lower()
    assert res.severity == "CRITICAL"


def test_competing_subsystems_refuse_to_match_unrelated_component_errors():
    """Verify anti-hallucination: 'pump error' on logs that contain only detector baseline errors returns found=False."""
    service = LogIncidentInvestigationService()
    detector_only_logs = (
        "optical.log",
        """Oct 20 10:00:00 [INFO] Baseline calibration started.
Oct 20 10:05:00 [ERROR] Detector baseline noise exceeds acquisition threshold
Oct 20 10:10:00 [INFO] Acquisition halted.
"""
    )

    res = service.investigate(files=[detector_only_logs], problem_description="pump error")
    assert res.found is False, "Expected found=False when querying 'pump error' against detector-only errors"
    assert res.log_file is None
    assert res.line_number is None
    assert "not found" in res.pre_incident_summary.lower()


def test_clean_logs_with_words_containing_indicator_substrings_do_not_hallucinate():
    """Verify anti-hallucination: words like 'default', 'reinstalled', 'installed', 'stripped' do not falsely trigger error indicators."""
    service = LogIncidentInvestigationService()

    log_content = (
        "system_maintenance.log",
        """Oct 20 10:00:00 [INFO] System boot sequence started.
Oct 20 10:01:00 [INFO] Loading default configuration for pump.
Oct 20 10:02:00 [INFO] Pump seal reinstalled successfully.
Oct 20 10:03:00 [INFO] New column installed successfully.
Oct 20 10:04:00 [INFO] Stripped column fittings inspected and replaced.
Oct 20 10:05:00 [INFO] System operational and ready.
"""
    )

    queries_to_test = [
        "did an error occur",
        "is there any error",
        "check for errors",
        "what error occurred",
        "pump error",
        "column error",
        "was there any failure",
        "check if anything failed",
    ]

    for q in queries_to_test:
        res = service.investigate(files=[log_content], problem_description=q)
        assert res.found is False, f"Expected found=False for query '{q}' on clean log with 'default'/'reinstalled'/'installed'/'stripped' lines"
        assert res.log_file is None
        assert res.line_number is None


def test_unformatted_log_indicators_detected():
    """Verify error detection on raw unformatted log lines without structured bracketed level tags."""
    service = LogIncidentInvestigationService()

    unformatted_cases = [
        ("Ethernet link disconnected", "ERROR", "disconnect"),
        ("Connection timed out after 30s", "WARNING", "timed out"),
        ("Minor solvent leak detected at valve", "WARNING", "leak"),
        ("Remote socket unreachable by controller", "ERROR", "unreachable"),
        ("Plunger motor stalled at position 4", "ERROR", "stalled"),
        ("Connection refused on port 8080", "ERROR", "refused"),
        ("Communication lost with autosampler", "ERROR", "lost"),
    ]

    for line_text, expected_severity, expected_indicator in unformatted_cases:
        log_content = (
            "unformatted.log",
            f"""Oct 20 10:00:00 System initialized normally.
Oct 20 10:05:00 {line_text}
Oct 20 10:10:00 System halted.
"""
        )

        res = service.investigate(files=[log_content], problem_description="did an error occur")
        assert res.found is True, f"Failed to detect unformatted line '{line_text}'"
        assert res.line_number == 2, f"Failed to pinpoint line 2 for '{line_text}'"
        assert res.severity == expected_severity
        assert expected_indicator in res.matched_line.lower()


def test_query_with_attempt_triggers_broad_error_without_temp_hijacking():
    """Verify queries containing the word 'attempt' trigger broad error detection and do not falsely match component 'temp'."""
    service = LogIncidentInvestigationService()

    log_content = (
        "autosampler.log",
        """Oct 20 10:00:00 [INFO] System boot.
Oct 20 10:05:00 [ERROR] Autosampler vial mechanism stalled
Oct 20 10:10:00 [INFO] System halted.
"""
    )

    query = "an attempt was made to run the sequence but an error occurred"
    res = service.investigate(files=[log_content], problem_description=query)
    assert res.found is True
    assert res.line_number == 2
    assert "autosampler" in res.matched_line.lower()


def test_mixed_benign_negations_and_real_errors_in_same_log():
    """Verify that earlier benign negations (0 errors, normal disconnect) do not mask a genuine subsequent error."""
    service = LogIncidentInvestigationService()

    mixed_log = (
        "mixed_execution.log",
        """Oct 20 10:00:00 [INFO] System initialized.
Oct 20 10:01:00 [INFO] Self-test complete: 0 errors detected.
Oct 20 10:02:00 [INFO] Normal disconnect of idle socket upon batch end.
Oct 20 10:15:00 [INFO] Ethernet disconnected unexpectedly during run.
Oct 20 10:16:00 [INFO] System halted.
"""
    )

    res = service.investigate(files=[mixed_log], problem_description="did an error occur")
    assert res.found is True
    assert res.line_number == 4
    assert "unexpectedly" in res.matched_line.lower()
