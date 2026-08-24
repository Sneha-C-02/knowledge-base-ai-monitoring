from typing import List, BinaryIO, Tuple
from src.knowledge_base_backend.application.models.monitoring_models import MonitoringAnalysisResult, MonitoringIssueDto, MonitoringEventDto, FileInfo
from src.knowledge_base_backend.domain.services.log_file_validator import LogFileValidator
from src.knowledge_base_backend.domain.services.temporary_file_storage import TemporaryFileStorage
from src.knowledge_base_backend.domain.services.log_analysis_service import LogAnalysisService
from src.knowledge_base_backend.domain.repositories.monitoring_repository import MonitoringRepository
from src.knowledge_base_backend.domain.entities.monitoring_issue import MonitoringIssue
import datetime
import uuid

class AnalyzeUploadedLogsUseCase:
    def __init__(
        self,
        validator: LogFileValidator,
        storage: TemporaryFileStorage,
        analysis_service: LogAnalysisService,
        repository: MonitoringRepository
    ) -> None:
        self.validator = validator
        self.storage = storage
        self.analysis_service = analysis_service
        self.repository = repository

    async def execute(self, files: List[Tuple[str, BinaryIO]]) -> MonitoringAnalysisResult:
        if not files:
            raise ValueError("No files provided")
        
        if len(files) > 10:
            raise ValueError("Maximum 10 files allowed")

        # Fake implementation that uses the interfaces
        # In a real app this would store files, parse, search vectors, build issues
        
        # Here we just validate and clean up to prove structure
        stored_paths = []
        try:
            for filename, stream in files:
                self.validator.validate_uploaded_log_file(filename, stream)
                path = await self.storage.store_temporary_file(filename, stream)
                stored_paths.append(path)
            
            # Simulated analysis using domain service
            issues = []
            events = []
            status = "OK"
            if stored_paths:
                domain_issues, domain_events, run_status = await self.analysis_service.analyze_log_file_contents(stored_paths[0], 0)
                status = run_status
                
                for iss in domain_issues:
                    await self.repository.save_issue(iss)
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
        finally:
            for path in stored_paths:
                await self.storage.delete_temporary_file(path)

        return MonitoringAnalysisResult(
            status=status,
            file_status="ACCESSIBLE",
            file_info=FileInfo(size="Unknown", last_modified="Unknown"),
            issues=issues,
            recent_events=events
        )
