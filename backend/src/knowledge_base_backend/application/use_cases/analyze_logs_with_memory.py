import datetime
import json
import logging
import re
import uuid
from datetime import datetime as dt
from typing import BinaryIO, List, Optional, Tuple

import aiofiles

from src.knowledge_base_backend.application.services.keyword_learning_coordinator import KeywordLearningCoordinator
from src.knowledge_base_backend.domain.entities.instrument_memory_entry import InstrumentMemoryEntry
from src.knowledge_base_backend.domain.entities.monitored_log_file import MonitoredLogFile
from src.knowledge_base_backend.domain.entities.system_notification import SystemNotification
from src.knowledge_base_backend.domain.repositories.instrument_memory_repository import InstrumentMemoryRepository
from src.knowledge_base_backend.domain.repositories.instrument_repository import InstrumentRepository
from src.knowledge_base_backend.domain.repositories.monitored_log_file_repository import MonitoredLogFileRepository
from src.knowledge_base_backend.domain.repositories.notification_repository import NotificationRepository
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
from src.knowledge_base_backend.domain.services.log_file_validator import LogFileValidator
from src.knowledge_base_backend.domain.services.persistent_file_storage import PersistentFileStorage
from src.knowledge_base_backend.domain.value_objects.log_dashboard_result import (
    DashboardFinding,
    DashboardSummaryBullet,
    LogDashboardResult,
)
from src.knowledge_base_backend.domain.services.log_date_filter import LogDateFilter
from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.domain.services.log_incident_investigation_service import LogIncidentInvestigationService
from src.knowledge_base_backend.infrastructure.artificial_intelligence.groq_dashboard_analysis_service import (
    GroqDashboardAnalysisService,
)


logger = logging.getLogger(__name__)


class AnalyzeLogsWithMemoryUseCase:
    """
    Orchestrates the full AI log monitoring pipeline with initial context mapping
    and incremental monitoring.

    FIRST UPLOAD of a file:
        1. Read ALL content
        2. AI analyzes the complete file (initial context mapping)
        3. AI generates a compressed context summary
        4. Store MonitoredLogFile record with line count + context summary
        5. Store analysis snapshot in instrument_memory

    RE-UPLOAD of same file (more lines added):
        1. Read ALL content but skip already-analyzed lines
        2. AI analyzes ONLY new lines, using the stored context summary
        3. AI updates the context summary
        4. Update MonitoredLogFile record with new line count + updated context
        5. Store analysis snapshot in instrument_memory

    Both paths produce a structured dashboard result and system notification.
    """

    def __init__(
        self,
        validator: LogFileValidator,
        storage: PersistentFileStorage,
        ai_service: GroqDashboardAnalysisService,
        memory_repository: InstrumentMemoryRepository,
        instrument_repository: InstrumentRepository,
        notification_repository: NotificationRepository,
        monitored_file_repository: MonitoredLogFileRepository,
        date_time_provider: DateTimeProvider,
        keyword_learning_coordinator: KeywordLearningCoordinator,
        retrieval_service: Optional[HybridArticleRetrievalService] = None,
    ) -> None:
        self.validator = validator
        self.storage = storage
        self.ai_service = ai_service
        self.memory_repository = memory_repository
        self.instrument_repository = instrument_repository
        self.notification_repository = notification_repository
        self.monitored_file_repository = monitored_file_repository
        self.date_time_provider = date_time_provider
        self.keyword_learning_coordinator = keyword_learning_coordinator
        self.retrieval_service = retrieval_service
        self.date_filter = LogDateFilter()

    async def _extract_instrument_name(self, stream: BinaryIO) -> str:
        pos = stream.tell()
        stream.seek(0)

        # Read the first few lines to find the instrument tag
        lines = []
        for _ in range(10):
            line = stream.readline()
            if not line:
                break
            lines.append(line.decode("utf-8", errors="ignore"))

        stream.seek(pos)  # Reset stream position

        # Look for the first bracketed text after the timestamp colon
        # Example: "Mon Oct 20 11:32:42 AM GMT Summer Time: [EPC]"
        for line in lines:
            match = re.search(r":\s+\[(.*?)\]", line)
            if match:
                name = match.group(1).strip()
                if name:
                    return name

        return "Unknown Instrument"

    async def execute(
        self,
        files: List[Tuple[str, BinaryIO]],
        analysis_mode: str = "exhaustive",
        date_from: Optional[dt] = None,
        date_to: Optional[dt] = None,
    ) -> LogDashboardResult:
        if not files:
            raise ValueError("No files provided for analysis")

        if len(files) > 10:
            raise ValueError("Maximum 10 files allowed per analysis run")

        # --- Step 1: Detect instrument from the first file ---
        first_filename, first_stream = files[0]
        instrument_name = await self._extract_instrument_name(first_stream)

        instrument = await self.instrument_repository.get_by_name(instrument_name)
        if instrument is None:
            # Create the instrument dynamically if it doesn't exist
            instrument = await self.instrument_repository.create(instrument_name)

        instrument_id = instrument.id

        # --- Step 2: Store uploaded files temporarily ---
        stored_paths = []
        filenames = []
        for filename, stream in files:
            self.validator.validate_uploaded_log_file(filename, stream)
            path = await self.storage.store_persistent_file(instrument_id, filename, stream)
            stored_paths.append(path)
            filenames.append(filename)

        # --- Step 3: Fetch instrument memory (past analyses) ---
        memory_entries = await self.memory_repository.get_memory_for_instrument(instrument_id)

        # --- Step 4: Process each file with initial/incremental logic ---
        aggregated_result = LogDashboardResult(
            instrument_id=instrument_id,
            instrument_name=instrument.name,
            critical_incidents=0,
            warnings=0,
            errors=0,
            healthy_apps=0,
            daily_summary_bullets=[],
            overall_status="OK",
            files_analyzed=0,
        )

        for path, filename in zip(stored_paths, filenames):
            result = await self._process_single_file(
                path=path,
                filename=filename,
                instrument_id=instrument_id,
                instrument_name=instrument.name,
                memory_entries=memory_entries,
                analysis_mode=analysis_mode,
                date_from=date_from,
                date_to=date_to,
            )

            # Aggregate results across multiple files
            aggregated_result.critical_incidents += result.critical_incidents
            aggregated_result.warnings += result.warnings
            aggregated_result.errors += result.errors
            aggregated_result.healthy_apps = max(aggregated_result.healthy_apps, result.healthy_apps)
            aggregated_result.daily_summary_bullets.extend(result.daily_summary_bullets)
            aggregated_result.complete_findings.extend(result.complete_findings)
            aggregated_result.files_analyzed += 1
            if hasattr(result, "monitored_files") and result.monitored_files:
                aggregated_result.monitored_files.extend(result.monitored_files)

            # Aggregate analysis status and chunks
            if not hasattr(aggregated_result, "total_chunks"):
                aggregated_result.total_chunks = 0
                aggregated_result.successful_ai_chunks = 0
                aggregated_result.fallback_chunks = 0
                aggregated_result.failed_chunks = 0

            # If aggregated_result was just initialized, its total_chunks is 1 by default, let's reset it on first real file
            if aggregated_result.files_analyzed == 1:
                aggregated_result.total_chunks = result.total_chunks
                aggregated_result.successful_ai_chunks = result.successful_ai_chunks
                aggregated_result.fallback_chunks = getattr(result, "fallback_chunks", 0)
                aggregated_result.failed_chunks = getattr(result, "failed_chunks", 0)
                aggregated_result.analysis_status = result.analysis_status
                aggregated_result.original_line_count = result.original_line_count
                aggregated_result.analyzed_line_count = result.analyzed_line_count
                aggregated_result.was_log_reduced = result.was_log_reduced
                aggregated_result.coverage_mode = result.coverage_mode
            else:
                aggregated_result.total_chunks += getattr(result, "total_chunks", 1)
                aggregated_result.successful_ai_chunks += getattr(result, "successful_ai_chunks", 1)
                aggregated_result.fallback_chunks += getattr(result, "fallback_chunks", 0)
                aggregated_result.failed_chunks += getattr(result, "failed_chunks", 0)
                if result.original_line_count:
                    aggregated_result.original_line_count = (
                        aggregated_result.original_line_count or 0
                    ) + result.original_line_count
                if result.analyzed_line_count:
                    aggregated_result.analyzed_line_count = (
                        aggregated_result.analyzed_line_count or 0
                    ) + result.analyzed_line_count
                if result.was_log_reduced:
                    aggregated_result.was_log_reduced = True

                # Downgrade status if any file had a partial or failed status
                if result.analysis_status == "AI_ANALYSIS_FAILED":
                    aggregated_result.analysis_status = "AI_ANALYSIS_FAILED"
                elif (
                    result.analysis_status == "DETERMINISTIC_FALLBACK"
                    and aggregated_result.analysis_status != "AI_ANALYSIS_FAILED"
                ):
                    aggregated_result.analysis_status = "DETERMINISTIC_FALLBACK"
                elif result.analysis_status == "PARTIAL_AI_ANALYSIS" and aggregated_result.analysis_status not in [
                    "AI_ANALYSIS_FAILED",
                    "DETERMINISTIC_FALLBACK",
                ]:
                    aggregated_result.analysis_status = "PARTIAL_AI_ANALYSIS"

            if result.overall_status == "CRITICAL":
                aggregated_result.overall_status = "CRITICAL"
            elif result.overall_status == "WARNING" and aggregated_result.overall_status != "CRITICAL":
                aggregated_result.overall_status = "WARNING"

        # --- Step 5: Ensure KB articles are NOT auto-fetched in advance (on-demand only) ---
        for finding in aggregated_result.complete_findings:
            finding.kb_article = None


        # --- Step 6: Create dashboard notification ---
        await self._create_dashboard_notification(aggregated_result)

        return aggregated_result

    async def _process_single_file(
        self,
        path: str,
        filename: str,
        instrument_id: int,
        instrument_name: str,
        memory_entries: list,
        analysis_mode: str = "exhaustive",
        date_from: Optional[dt] = None,
        date_to: Optional[dt] = None,
    ) -> LogDashboardResult:
        """
        Process a single log file. Determines whether this is an initial mapping
        or an incremental update based on whether a MonitoredLogFile record exists.
        """
        current_time = self.date_time_provider.get_current_utc_time()

        # Read the FULL file content
        async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as f:
            full_content = await f.read()

        all_lines = full_content.split("\n")

        # Apply date range filter if specified
        if date_from or date_to:
            filtered_lines = self.date_filter.filter_lines(all_lines, date_from, date_to)
            logger.info(
                "Date filter applied: %d → %d lines (from=%s, to=%s)",
                len(all_lines), len(filtered_lines), date_from, date_to,
            )
            analysis_content = "\n".join(filtered_lines)
            total_lines = len(filtered_lines)
        else:
            analysis_content = full_content
            total_lines = len(all_lines)

        # Learn error-related keywords from this file's critical/warning lines,
        # so future keyword searches can suggest terms grounded in real errors.
        await self.keyword_learning_coordinator.learn_from_text(full_content, instrument_id)

        # Check if this file has been monitored before
        monitored = await self.monitored_file_repository.find_by_instrument_and_filename(instrument_id, filename)

        if monitored is None:
            # ============================================
            # INITIAL MAPPING: First time this file is added
            # ============================================
            result = await self.ai_service.analyze_full_log_with_memory(
                log_content=analysis_content,
                log_filename=filename,
                instrument_id=instrument_id,
                instrument_name=instrument_name,
                memory_entries=memory_entries,
                analysis_mode=analysis_mode,
            )

            # Generate a context summary for storage
            context_summary = await self.ai_service.generate_context_summary(
                log_content=analysis_content,
                existing_summary=None,
                log_filename=filename,
                instrument_name=instrument_name,
                instrument_id=instrument_id,
            )

            # Save the MonitoredLogFile record
            monitored = MonitoredLogFile(
                id=0,
                instrument_id=instrument_id,
                filename=filename,
                total_lines_analyzed=total_lines,
                full_context_summary=context_summary,
                created_at=current_time,
                updated_at=current_time,
                status="MONITORING",
            )
            await self.monitored_file_repository.save(monitored)

        else:
            # ============================================
            # INCREMENTAL: File has been monitored before
            # ============================================
            previously_analyzed = monitored.total_lines_analyzed

            if total_lines <= previously_analyzed or analysis_mode == "exhaustive":
                # Exhaustive mode always revisits the complete file. A fast sampled re-upload
                # without new lines also receives a fresh result rather than silent zeros.
                result = await self.ai_service.analyze_full_log_with_memory(
                    log_content=analysis_content,
                    log_filename=filename,
                    instrument_id=instrument_id,
                    instrument_name=instrument_name,
                    memory_entries=memory_entries,
                    analysis_mode=analysis_mode,
                )
                # Update the context summary to stay current
                context_summary = await self.ai_service.generate_context_summary(
                    log_content=analysis_content,
                    existing_summary=monitored.full_context_summary,
                    log_filename=filename,
                    instrument_name=instrument_name,
                    instrument_id=instrument_id,
                )
                monitored.full_context_summary = context_summary
                monitored.total_lines_analyzed = total_lines
                monitored.status = "MONITORING"
                monitored.updated_at = current_time
                await self.monitored_file_repository.update(monitored)
            else:
                # Extract only the NEW lines
                new_lines = all_lines[previously_analyzed:]
                new_content = "\n".join(new_lines)

                result = await self.ai_service.analyze_incremental_log(
                    new_lines_content=new_content,
                    stored_context_summary=monitored.full_context_summary,
                    log_filename=filename,
                    instrument_id=instrument_id,
                    instrument_name=instrument_name,
                    memory_entries=memory_entries,
                    analysis_mode=analysis_mode,
                )

                # Offset line numbers of incremental findings to match the full file position
                for finding in result.complete_findings:
                    finding.line_number += previously_analyzed

                # Update the context summary to include new content
                updated_summary = await self.ai_service.generate_context_summary(
                    log_content=new_content,
                    existing_summary=monitored.full_context_summary,
                    log_filename=filename,
                    instrument_name=instrument_name,
                    instrument_id=instrument_id,
                )

                # Update the MonitoredLogFile record
                monitored.total_lines_analyzed = total_lines
                monitored.full_context_summary = updated_summary
                monitored.status = "MONITORING"
                monitored.updated_at = current_time
                await self.monitored_file_repository.update(monitored)

        # Save this analysis as a new instrument memory entry
        summary_text = " | ".join([b.text for b in result.daily_summary_bullets])
        memory_entry = InstrumentMemoryEntry(
            id=0,
            instrument_id=instrument_id,
            instrument_name=instrument_name,
            analysis_timestamp=current_time,
            log_filename=filename,
            critical_incidents=result.critical_incidents,
            warnings=result.warnings,
            errors=result.errors,
            healthy_apps=result.healthy_apps,
            ai_summary=summary_text,
            raw_issues_json=json.dumps(
                [{"text": b.text, "severity": b.severity} for b in result.daily_summary_bullets]
            ),
        )
        await self.memory_repository.save_memory_entry(memory_entry)

        # Enrich findings with deep forensic features and plain-English simple AI explanation
        self._enrich_findings_with_forensics(result.complete_findings, all_lines, filename)

        result.monitoring_status = "MONITORING"
        result.monitored_files = [
            {
                "filename": filename,
                "status": getattr(monitored, "status", "MONITORING") or "MONITORING",
                "total_lines_analyzed": monitored.total_lines_analyzed,
                "updated_at": monitored.updated_at.isoformat() if hasattr(monitored.updated_at, "isoformat") else str(monitored.updated_at),
            }
        ]

        return result


    async def _create_dashboard_notification(self, result: LogDashboardResult) -> None:
        """Create a system notification with the formatted dashboard content."""
        bullet_text = "\n".join([f"• {b.text}" for b in result.daily_summary_bullets])

        message = (
            f"AI Log Operations Dashboard — {result.instrument_name}\n\n"
            f"Critical Incidents: {result.critical_incidents} | "
            f"Warnings: {result.warnings} | "
            f"Errors: {result.errors} | "
            f"Healthy Apps: {result.healthy_apps}\n\n"
            f"AI Generated Daily Summary:\n{bullet_text}"
        )

        notif_type = (
            "error"
            if result.overall_status == "CRITICAL"
            else ("warning" if result.overall_status == "WARNING" else "info")
        )

        notification = SystemNotification(
            id=0,
            notification_identifier=f"DASH-{uuid.uuid4().hex[:8]}",
            title=f"AI Log Dashboard: {result.instrument_name}",
            message=message,
            notification_type=notif_type,
            is_read=False,
            created_at=datetime.datetime.utcnow(),
        )
        await self.notification_repository.save(notification)

    async def _attach_kb_articles(
        self, result: LogDashboardResult, instrument_name: str
    ) -> None:
        """Enrich each complete_finding with the best-matching KB article."""
        for finding in result.complete_findings:
            try:
                candidates: List[str] = []
                for cand in (finding.explanation, finding.snippet):
                    if cand and isinstance(cand, str) and len(cand.strip()) >= 5 and cand.strip() not in candidates:
                        candidates.append(cand.strip())
                
                matches = []
                for query in candidates:
                    try:
                        matches = await self.retrieval_service.retrieve_relevant_articles(
                            query, instrument_name, limit=1
                        )
                        if matches:
                            break
                    except Exception:
                        continue

                if matches:
                    top = matches[0]
                    content = top.article.searchable_content or ""
                    snippet = content[:280].strip() + ("..." if len(content) > 280 else "")
                    finding.kb_article = {
                        "id": str(top.article.id),
                        "database_id": top.article.database_id,
                        "article_number": top.article.article_number,
                        "title": top.article.title,
                        "url": top.article.url or f"/article/{top.article.article_number}",
                        "summary": snippet,
                        "relevance_score": round(float(top.combined_relevance_score), 2),
                        "retrieval_reason": top.retrieval_reason or "Matched finding from log analysis",
                    }
            except Exception:
                logger.debug("KB article lookup failed for finding line %d", finding.line_number)
                finding.kb_article = None

    def _enrich_findings_with_forensics(
        self, findings: List[DashboardFinding], all_lines: List[str], filename: str
    ) -> None:
        """Enrich detected findings with deep forensic context and simple plain-English AI explanations."""
        investigation_service = LogIncidentInvestigationService()
        for finding in findings:
            finding.kb_article = None  # KB search is strictly on-demand
            target_line = finding.line_number
            target_idx = max(0, min(len(all_lines) - 1, target_line - 1))

            # 1. Simple AI plain-language summary
            finding.simple_summary = self._generate_simple_ai_summary(finding.snippet, finding.severity)

            # 2. Pre-incident events window (up to 35 lines)
            pre_start = max(0, target_idx - 35)
            pre_lines = all_lines[pre_start:target_idx]
            pre_records = [
                {
                    "file": filename,
                    "line": pre_start + i + 1,
                    "text": line.strip(),
                    "lower": line.strip().lower(),
                    "timestamp": investigation_service.detect_timestamp(line),
                    "severity": investigation_service.detect_severity(line),
                }
                for i, line in enumerate(pre_lines)
                if line.strip()
            ]

            incident_record = {
                "file": filename,
                "line": target_line,
                "text": finding.snippet,
                "lower": finding.snippet.lower(),
                "timestamp": investigation_service.detect_timestamp(finding.snippet),
                "severity": finding.severity.upper() if finding.severity else "ERROR",
            }

            post_end = min(len(all_lines), target_idx + 26)
            post_lines = all_lines[target_idx + 1:post_end]
            post_records = [
                {
                    "file": filename,
                    "line": target_idx + 1 + i + 1,
                    "text": line.strip(),
                    "lower": line.strip().lower(),
                    "timestamp": investigation_service.detect_timestamp(line),
                    "severity": investigation_service.detect_severity(line),
                }
                for i, line in enumerate(post_lines)
                if line.strip()
            ]

            pattern_name, pre_summary, pre_events = investigation_service._analyze_pre_incident(
                pre_records, incident_record, finding.explanation or finding.snippet
            )
            finding.pre_incident_pattern = pattern_name
            finding.pre_incident_summary = pre_summary
            finding.pre_incident_events = pre_events

            parsed_files = {filename: pre_records + [incident_record] + post_records}
            major_events = investigation_service._detect_matching_major_events(
                parsed_files, incident_record, finding.explanation or finding.snippet
            )
            finding.major_events = [
                {
                    "timestamp": ev.timestamp,
                    "event_type": ev.event_type,
                    "description": ev.description,
                    "match_reason": ev.match_reason,
                    "line_number": ev.line_number,
                    "log_file": ev.log_file,
                }
                for ev in major_events
            ]

            system_changes = investigation_service._analyze_system_changes(
                pre_records, incident_record, post_records
            )
            finding.system_changes = [
                {
                    "aspect": sc.aspect,
                    "before_incident": sc.before_incident,
                    "after_incident": sc.after_incident,
                    "change_summary": sc.change_summary,
                }
                for sc in system_changes
            ]

            problem_keywords = investigation_service.extract_keywords(finding.explanation or finding.snippet)
            citations, score = investigation_service._validate_grounding(
                filename, target_line, finding.snippet, pre_records, major_events, problem_keywords
            )
            finding.grounding_citations = [
                {
                    "log_file": c.log_file,
                    "line_number": c.line_number,
                    "snippet": c.snippet,
                    "relevance_reason": c.relevance_reason,
                }
                for c in citations
            ]
            finding.confidence_score = score
            finding.suggested_search_query = investigation_service._generate_suggested_kb_query(
                finding.explanation or finding.snippet, incident_record, pattern_name
            )

    @staticmethod
    def _generate_simple_ai_summary(snippet: str, severity: str) -> str:
        lower = snippet.lower()
        if any(k in lower for k in ("comm", "socket", "disconnect", "timeout", "packet", "handshake", "unreachable")):
            return "The system experienced a network or communication timeout while communicating with the instrument controller or module."
        if "pressure" in lower and any(k in lower for k in ("exceed", "high", "limit", "max")):
            return "The fluid pump pressure exceeded the safe operating limit, halting fluid flow to prevent column or tubing damage."
        if any(k in lower for k in ("leak", "pressure drop", "loss of pressure", "seal")):
            return "A fluid leak or sudden loss of mobile phase pressure was detected in the fluidic system."
        if "vacuum" in lower:
            return "The mass spectrometer vacuum level degraded or the vacuum pump encountered an operational fault."
        if any(k in lower for k in ("needle", "vial", "autosampler", "carousel", "tray", "pierce", "motor stall")):
            return "The autosampler mechanism encountered a mechanical obstruction or trouble accessing the sample vial."
        if "lamp" in lower:
            return "The detector UV/Vis lamp failed to ignite or its light intensity dropped below the operating threshold."
        if any(k in lower for k in ("temp", "heater", "cooler", "thermal")):
            return "The temperature control system failed to maintain the required heating or cooling target."
        if any(k in lower for k in ("write", "cannot set", "unable to set")):
            return "The system failed to write a hardware configuration setting or register value to the instrument."
        if "riostatus" in lower:
            return "The low-level FPGA/RIO hardware controller reported a hardware bus error."
        if any(k in lower for k in ("memory", "buffer", "overflow", "oom")):
            return "The acquisition software ran out of buffer memory to process incoming instrument data."
        if any(k in lower for k in ("interlock", "emergency stop", "safety")):
            return "A hardware safety interlock tripped or an emergency stop was triggered to protect the instrument."
        if any(k in lower for k in ("abort", "crash", "panic", "fatal")):
            return "The sample acquisition was aborted due to an unrecoverable system exception."

        clean = re.sub(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[^:]+:\s*(\[[^\]]+\]\s*)?", "", snippet).strip()
        clean = re.sub(r"^\(\w+\):\s*", "", clean).strip()
        return f"Operational anomaly observed: {clean[:140]}"

