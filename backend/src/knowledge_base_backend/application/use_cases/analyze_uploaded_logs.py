from typing import List, BinaryIO, Tuple
from src.knowledge_base_backend.application.models.monitoring_models import MonitoringAnalysisResult, MonitoringIssueDto, MonitoringEventDto, FileInfo
from src.knowledge_base_backend.domain.services.log_file_validator import LogFileValidator
from src.knowledge_base_backend.domain.services.temporary_file_storage import TemporaryFileStorage
from src.knowledge_base_backend.domain.services.log_analysis_service import LogAnalysisService
from src.knowledge_base_backend.domain.services.log_keyword_extractor import LogKeywordExtractor
from src.knowledge_base_backend.domain.services.embedding_generation_service import EmbeddingGenerationService
from src.knowledge_base_backend.domain.repositories.monitoring_repository import MonitoringRepository
from src.knowledge_base_backend.domain.repositories.notification_repository import NotificationRepository
from src.knowledge_base_backend.domain.repositories.log_event_vector_repository import LogEventVectorRepository, LogEventVectorRecord
from src.knowledge_base_backend.domain.entities.system_notification import SystemNotification
from src.knowledge_base_backend.domain.entities.monitoring_issue import MonitoringIssue
import datetime
import uuid
import os
import logging

logger = logging.getLogger(__name__)


class AnalyzeUploadedLogsUseCase:
    def __init__(
        self,
        validator: LogFileValidator,
        storage: TemporaryFileStorage,
        analysis_service: LogAnalysisService,
        repository: MonitoringRepository,
        notification_repository: NotificationRepository,
        keyword_extractor: LogKeywordExtractor,
        embedding_service: EmbeddingGenerationService,
        log_event_vector_repository: LogEventVectorRepository,
    ) -> None:
        self.validator = validator
        self.storage = storage
        self.analysis_service = analysis_service
        self.repository = repository
        self.notification_repository = notification_repository
        self.keyword_extractor = keyword_extractor
        self.embedding_service = embedding_service
        self.log_event_vector_repository = log_event_vector_repository

    async def execute(self, files: List[Tuple[str, BinaryIO]], instrument_id: int | None = None) -> MonitoringAnalysisResult:
        if not files:
            raise ValueError("No files provided")

        if len(files) > 10:
            raise ValueError("Maximum 10 files allowed")

        stored_paths = []
        stored_filenames = []
        try:
            for filename, stream in files:
                self.validator.validate_uploaded_log_file(filename, stream)
                path = await self.storage.store_temporary_file(filename, stream)
                stored_paths.append(path)
                stored_filenames.append(filename)

            issues = []
            events = []
            status = "OK"

            total_size = 0
            latest_time = 0
            for path in stored_paths:
                if os.path.exists(path):
                    total_size += os.path.getsize(path)
                    mtime = os.path.getmtime(path)
                    if mtime > latest_time:
                        latest_time = mtime

            size_str = f"{total_size / 1024:.1f} KB" if total_size > 0 else "Unknown"
            time_str = datetime.datetime.fromtimestamp(latest_time).strftime('%Y-%m-%d %H:%M:%S') if latest_time > 0 else "Unknown"

            if stored_paths:
                for path, filename in zip(stored_paths, stored_filenames):
                    domain_issues, domain_events, run_status = await self.analysis_service.analyze_log_file_contents(path, None)
                    if run_status == "CRITICAL" or (run_status == "WARNING" and status == "OK"):
                        status = run_status

                    for iss in domain_issues:
                        await self.repository.save_issue(iss)

                        notif_type = "error" if iss.severity == "CRITICAL" else "warning"
                        notif_message = f"{iss.description}\n\nRecommended Action: {iss.recommended_action}"
                        if iss.related_article_number:
                            notif_message += f"\n\nRelated Article: {iss.related_article_number}"

                        notif = SystemNotification(
                            id=0,
                            notification_identifier=f"NOT-{uuid.uuid4().hex[:8]}",
                            title=f"New Issue Detected: {iss.pattern}",
                            message=notif_message,
                            notification_type=notif_type,
                            is_read=False,
                            created_at=iss.event_timestamp or datetime.datetime.utcnow()
                        )
                        await self.notification_repository.save(notif)

                        issues.append(MonitoringIssueDto(
                            id=iss.issue_identifier,
                            severity=iss.severity,
                            timestamp=iss.event_timestamp.isoformat() if iss.event_timestamp else None,
                            pattern=iss.pattern,
                            description=iss.description,
                            recommended_action=iss.recommended_action,
                            related_article=iss.related_article_number,
                            related_article_url=iss.related_article_url
                        ))

                    for ev in domain_events:
                        events.append(MonitoringEventDto(
                            timestamp=ev.timestamp.isoformat(),
                            level=ev.level,
                            message=ev.message
                        ))

                    # --- NEW: Keyword extraction & vectorization ---
                    await self._vectorize_log_keywords(path, filename, instrument_id)

        finally:
            for path in stored_paths:
                await self.storage.delete_temporary_file(path)

        return MonitoringAnalysisResult(
            status=status,
            file_status="ACCESSIBLE",
            file_info=FileInfo(size=size_str, last_modified=time_str),
            issues=issues,
            recent_events=events
        )

    async def _vectorize_log_keywords(
        self,
        file_path: str,
        filename: str,
        instrument_id: int | None,
    ) -> None:
        """
        Read the stored log file, extract keyword events, generate embeddings,
        and bulk-insert into log_event_vectors. Failures are logged but do NOT
        abort the main analysis result.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            keyword_events = self.keyword_extractor.extract_from_lines(lines)

            if not keyword_events:
                logger.info(f"No critical keywords found in '{filename}' — skipping vectorization.")
                return

            records: List[LogEventVectorRecord] = []
            for event in keyword_events:
                try:
                    embedding = await self.embedding_service.generate_text_embedding(event.cleaned_text)
                    records.append(LogEventVectorRecord(
                        instrument_id=instrument_id or 0,
                        log_filename=filename,
                        severity=event.severity,
                        component=event.component,
                        cleaned_text=event.cleaned_text,
                        raw_log_line=event.raw_line,
                        matched_patterns=event.matched_patterns,
                        event_embedding=embedding,
                    ))
                except Exception as embed_err:
                    logger.warning(f"Failed to embed log event: {embed_err}")

            if records:
                saved = await self.log_event_vector_repository.save_batch(records)
                logger.info(f"Vectorized {saved} log keyword events from '{filename}'")

        except Exception as e:
            logger.error(f"Keyword vectorization failed for '{filename}': {e}", exc_info=True)
