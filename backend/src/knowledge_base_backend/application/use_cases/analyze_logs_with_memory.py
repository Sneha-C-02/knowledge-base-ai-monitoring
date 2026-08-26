from typing import List, BinaryIO, Tuple
import datetime
import json
import aiofiles

from src.knowledge_base_backend.domain.services.log_file_validator import LogFileValidator
from src.knowledge_base_backend.domain.services.persistent_file_storage import PersistentFileStorage
from src.knowledge_base_backend.domain.repositories.instrument_memory_repository import InstrumentMemoryRepository
from src.knowledge_base_backend.domain.repositories.instrument_repository import InstrumentRepository
from src.knowledge_base_backend.domain.repositories.notification_repository import NotificationRepository
from src.knowledge_base_backend.domain.repositories.monitored_log_file_repository import MonitoredLogFileRepository
from src.knowledge_base_backend.domain.entities.instrument_memory_entry import InstrumentMemoryEntry
from src.knowledge_base_backend.domain.entities.monitored_log_file import MonitoredLogFile
from src.knowledge_base_backend.domain.entities.system_notification import SystemNotification
from src.knowledge_base_backend.domain.value_objects.log_dashboard_result import LogDashboardResult, DashboardSummaryBullet
from src.knowledge_base_backend.infrastructure.artificial_intelligence.groq_dashboard_analysis_service import GroqDashboardAnalysisService
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
import uuid


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
        date_time_provider: DateTimeProvider
    ) -> None:
        self.validator = validator
        self.storage = storage
        self.ai_service = ai_service
        self.memory_repository = memory_repository
        self.instrument_repository = instrument_repository
        self.notification_repository = notification_repository
        self.monitored_file_repository = monitored_file_repository
        self.date_time_provider = date_time_provider

    async def execute(
        self,
        instrument_id: int,
        files: List[Tuple[str, BinaryIO]]
    ) -> LogDashboardResult:
        if not files:
            raise ValueError("No files provided for analysis")

        if len(files) > 10:
            raise ValueError("Maximum 10 files allowed per analysis run")

        # --- Step 1: Validate instrument exists ---
        instrument = await self.instrument_repository.get_by_id(instrument_id)
        if instrument is None:
            raise ValueError(f"Instrument with ID {instrument_id} not found")

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
            files_analyzed=0
        )

        for path, filename in zip(stored_paths, filenames):
            result = await self._process_single_file(
                path=path,
                filename=filename,
                instrument_id=instrument_id,
                instrument_name=instrument.name,
                memory_entries=memory_entries
            )

            # Aggregate results across multiple files
            aggregated_result.critical_incidents += result.critical_incidents
            aggregated_result.warnings += result.warnings
            aggregated_result.errors += result.errors
            aggregated_result.healthy_apps = max(aggregated_result.healthy_apps, result.healthy_apps)
            aggregated_result.daily_summary_bullets.extend(result.daily_summary_bullets)
            aggregated_result.files_analyzed += 1

            if result.overall_status == "CRITICAL":
                aggregated_result.overall_status = "CRITICAL"
            elif result.overall_status == "WARNING" and aggregated_result.overall_status != "CRITICAL":
                aggregated_result.overall_status = "WARNING"

        # --- Step 5: Create dashboard notification ---
        await self._create_dashboard_notification(aggregated_result)

        return aggregated_result

    async def _process_single_file(
        self,
        path: str,
        filename: str,
        instrument_id: int,
        instrument_name: str,
        memory_entries: list
    ) -> LogDashboardResult:
        """
        Process a single log file. Determines whether this is an initial mapping
        or an incremental update based on whether a MonitoredLogFile record exists.
        """
        current_time = self.date_time_provider.get_current_utc_time()

        # Read the FULL file content
        async with aiofiles.open(path, 'r', encoding='utf-8', errors='replace') as f:
            full_content = await f.read()

        all_lines = full_content.split("\n")
        total_lines = len(all_lines)

        # Check if this file has been monitored before
        monitored = await self.monitored_file_repository.find_by_instrument_and_filename(
            instrument_id, filename
        )

        if monitored is None:
            # ============================================
            # INITIAL MAPPING: First time this file is added
            # ============================================
            result = await self.ai_service.analyze_full_log_with_memory(
                log_content=full_content,
                log_filename=filename,
                instrument_id=instrument_id,
                instrument_name=instrument_name,
                memory_entries=memory_entries
            )

            # Generate a context summary for storage
            context_summary = await self.ai_service.generate_context_summary(
                log_content=full_content,
                existing_summary=None,
                log_filename=filename,
                instrument_name=instrument_name
            )

            # Save the MonitoredLogFile record
            monitored = MonitoredLogFile(
                id=0,
                instrument_id=instrument_id,
                filename=filename,
                total_lines_analyzed=total_lines,
                full_context_summary=context_summary,
                created_at=current_time,
                updated_at=current_time
            )
            await self.monitored_file_repository.save(monitored)

        else:
            # ============================================
            # INCREMENTAL: File has been monitored before
            # ============================================
            previously_analyzed = monitored.total_lines_analyzed

            if total_lines <= previously_analyzed:
                # No new lines — return a clean status based on stored context
                result = LogDashboardResult(
                    instrument_id=instrument_id,
                    instrument_name=instrument_name,
                    critical_incidents=0,
                    warnings=0,
                    errors=0,
                    healthy_apps=0,
                    daily_summary_bullets=[
                        DashboardSummaryBullet(
                            text=f"No new content since last analysis ({previously_analyzed} lines analyzed)",
                            severity="info"
                        )
                    ],
                    overall_status="OK",
                    files_analyzed=1
                )
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
                    memory_entries=memory_entries
                )

                # Update the context summary to include new content
                updated_summary = await self.ai_service.generate_context_summary(
                    log_content=new_content,
                    existing_summary=monitored.full_context_summary,
                    log_filename=filename,
                    instrument_name=instrument_name
                )

                # Update the MonitoredLogFile record
                monitored.total_lines_analyzed = total_lines
                monitored.full_context_summary = updated_summary
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
            raw_issues_json=json.dumps([
                {"text": b.text, "severity": b.severity}
                for b in result.daily_summary_bullets
            ])
        )
        await self.memory_repository.save_memory_entry(memory_entry)

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

        notif_type = "error" if result.overall_status == "CRITICAL" else (
            "warning" if result.overall_status == "WARNING" else "info"
        )

        notification = SystemNotification(
            id=0,
            notification_identifier=f"DASH-{uuid.uuid4().hex[:8]}",
            title=f"AI Log Dashboard: {result.instrument_name}",
            message=message,
            notification_type=notif_type,
            is_read=False,
            created_at=datetime.datetime.utcnow()
        )
        await self.notification_repository.save(notification)
