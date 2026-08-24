from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class KnowledgeBaseArticle:
    id: str
    database_id: int
    article_number: str
    title: str
    url: str
    searchable_content: str
    instruments: List[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None
