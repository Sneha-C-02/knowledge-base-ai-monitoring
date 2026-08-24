from src.knowledge_base_backend.domain.services.monitoring_explanation_generation_service import MonitoringExplanationGenerationService, GeneratedMonitoringExplanation
from src.knowledge_base_backend.domain.value_objects.monitoring_issue_search_context import MonitoringIssueSearchContext

class ConfigurableMonitoringExplanationGenerator(MonitoringExplanationGenerationService):
    async def generate_grounded_monitoring_explanation(
        self, issue: MonitoringIssueSearchContext, context: str
    ) -> GeneratedMonitoringExplanation:
        return GeneratedMonitoringExplanation(
            explanation="This issue relates to internal errors detected.",
            recommended_action="Please review system logs and restart if needed.",
            related_article_number=None,
            related_article_url=None
        )
