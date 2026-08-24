from src.knowledge_base_backend.application.models.system_models import DashboardStatistics
from src.knowledge_base_backend.domain.repositories.article_repository import ArticleRepository
from src.knowledge_base_backend.domain.repositories.monitoring_repository import MonitoringRepository
from src.knowledge_base_backend.domain.repositories.activity_repository import ActivityRepository

class GetDashboardStatisticsUseCase:
    def __init__(
        self,
        article_repository: ArticleRepository,
        monitoring_repository: MonitoringRepository,
        activity_repository: ActivityRepository
    ) -> None:
        self.article_repository = article_repository
        self.monitoring_repository = monitoring_repository
        self.activity_repository = activity_repository

    async def execute(self) -> DashboardStatistics:
        kb_articles = await self.article_repository.count_all_articles()
        detected_issues = await self.monitoring_repository.get_detected_issues_count()
        active_logs = await self.monitoring_repository.get_active_logs_count()
        
        # In a real impl we'd query support queries
        support_queries = 0

        return DashboardStatistics(
            support_queries=support_queries,
            active_logs=active_logs,
            detected_issues=detected_issues,
            kb_articles=kb_articles
        )
