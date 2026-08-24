from typing import Protocol, List, Dict, Any
from src.knowledge_base_backend.domain.entities.monitoring_issue import MonitoringIssue
from src.knowledge_base_backend.domain.entities.monitoring_event import MonitoringEvent

class LogAnalysisService(Protocol):
    async def analyze_log_file_contents(
        self, file_path: str, monitoring_run_id: int
    ) -> tuple[List[MonitoringIssue], List[MonitoringEvent], str]: ...
