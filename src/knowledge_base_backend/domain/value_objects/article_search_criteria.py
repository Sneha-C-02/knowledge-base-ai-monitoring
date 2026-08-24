from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ArticleSearchCriteria:
    search_query: Optional[str] = None
    instrument_name: Optional[str] = None
    sort_by: Optional[str] = None
    sort_direction: Optional[str] = None

    def __post_init__(self) -> None:
        query = self.search_query.strip() if self.search_query else None
        object.__setattr__(self, 'search_query', query if query else None)
        
        instrument = self.instrument_name.strip() if self.instrument_name else None
        object.__setattr__(self, 'instrument_name', instrument if instrument else None)
