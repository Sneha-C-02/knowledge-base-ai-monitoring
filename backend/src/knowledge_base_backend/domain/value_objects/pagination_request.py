from dataclasses import dataclass

@dataclass(frozen=True)
class PaginationRequest:
    page: int = 1
    page_size: int = 100
    
    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("Page must be at least 1")
        if self.page_size < 1:
            raise ValueError("Page size must be at least 1")
        if self.page_size > 100:
            raise ValueError("Page size cannot exceed 100")
            
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
