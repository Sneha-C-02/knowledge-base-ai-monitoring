from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.knowledge_base_backend.domain.repositories.monitoring_repository import MonitoringRepository
from src.knowledge_base_backend.domain.entities.monitoring_issue import MonitoringIssue
from src.knowledge_base_backend.infrastructure.database.models.monitoring_model import MonitoringIssueModel, MonitoringRunModel

class SqlAlchemyMonitoringRepository(MonitoringRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_issue(self, issue: MonitoringIssue) -> MonitoringIssue:
        model = MonitoringIssueModel(
            issue_identifier=issue.issue_identifier,
            monitoring_run_id=issue.monitoring_run_id,
            severity=issue.severity,
            event_timestamp=issue.event_timestamp,
            pattern=issue.pattern,
            description=issue.description,
            recommended_action=issue.recommended_action,
            related_article_number=issue.related_article_number,
            related_article_url=issue.related_article_url
        )
        self.session.add(model)
        await self.session.flush()
        issue.id = model.id
        return issue
        
    async def get_active_logs_count(self) -> int:
        query = select(func.count(MonitoringRunModel.id)).where(MonitoringRunModel.overall_status != 'COMPLETED')
        result = await self.session.execute(query)
        return result.scalar() or 0
        
    async def get_detected_issues_count(self) -> int:
        query = select(func.count(MonitoringIssueModel.id))
        result = await self.session.execute(query)
        return result.scalar() or 0
