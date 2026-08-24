from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class KnowledgeBaseArticleSummary:
    id: str
    database_id: int
    article_number: str
    title: str
    description: str
    url: str
    instruments: List[str]
    last_updated: Optional[datetime]
