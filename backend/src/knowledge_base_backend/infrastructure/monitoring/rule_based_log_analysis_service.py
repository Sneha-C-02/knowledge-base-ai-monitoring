from typing import List, Tuple
from src.knowledge_base_backend.domain.services.log_analysis_service import LogAnalysisService
from src.knowledge_base_backend.domain.services.log_content_parser import LogContentParser
from src.knowledge_base_backend.domain.entities.monitoring_issue import MonitoringIssue
from src.knowledge_base_backend.domain.entities.monitoring_event import MonitoringEvent
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
import uuid

class RuleBasedLogAnalysisService(LogAnalysisService):
    def __init__(self, parser: LogContentParser, date_time_provider: DateTimeProvider) -> None:
        self.parser = parser
        self.date_time_provider = date_time_provider

    async def analyze_log_file_contents(
        self, file_path: str, monitoring_run_id: int
    ) -> Tuple[List[MonitoringIssue], List[MonitoringEvent], str]:
        events_data = await self.parser.parse(file_path)
        
        issues = []
        events = []
        overall_status = "OK"
        
        current_time = self.date_time_provider.get_current_utc_time()
        
        for data in events_data:
            msg = data.get("message", "")
            lvl = data.get("level", "INFO")
            
            ev = MonitoringEvent(timestamp=current_time, level=lvl, message=msg)
            events.append(ev)
            
            if lvl == "ERROR":
                overall_status = "CRITICAL"
                iss = MonitoringIssue(
                    id=0,
                    issue_identifier=f"ISS-{uuid.uuid4().hex[:8]}",
                    monitoring_run_id=monitoring_run_id,
                    severity="CRITICAL",
                    pattern="Error Pattern Detected",
                    description=msg[:250],
                    recommended_action="Review log context and consult documentation.",
                    event_timestamp=current_time,
                    related_article_number=None,
                    related_article_url=None
                )
                issues.append(iss)
                
        return issues, events[:100], overall_status
