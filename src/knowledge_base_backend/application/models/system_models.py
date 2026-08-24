from dataclasses import dataclass

@dataclass
class DashboardStatistics:
    support_queries: int
    active_logs: int
    detected_issues: int
    kb_articles: int
