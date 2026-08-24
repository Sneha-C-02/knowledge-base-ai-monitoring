from typing import Protocol, Optional
from dataclasses import dataclass
from src.knowledge_base_backend.domain.value_objects.monitoring_issue_search_context import MonitoringIssueSearchContext

@dataclass(frozen=True)
class GeneratedMonitoringExplanation:
    explanation: str
    recommended_action: str
    related_article_number: Optional[str]
    related_article_url: Optional[str]

class MonitoringExplanationGenerationService(Protocol):
    async def generate_grounded_monitoring_explanation(
        self, issue: MonitoringIssueSearchContext, context: str
    ) -> GeneratedMonitoringExplanation: ...
