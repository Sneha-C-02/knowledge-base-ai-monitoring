from dataclasses import dataclass
from typing import Generic, TypeVar, List

T = TypeVar("T")

@dataclass
class PaginationResult(Generic[T]):
    items: List[T]
    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next_page: bool
    has_previous_page: bool
    next_page: int | None
    previous_page: int | None

    @classmethod
    def create(cls, items: List[T], current_page: int, page_size: int, total_items: int) -> "PaginationResult[T]":
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
        has_next_page = current_page < total_pages
        has_previous_page = current_page > 1
        
        return cls(
            items=items,
            current_page=current_page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
            next_page=current_page + 1 if has_next_page else None,
            previous_page=current_page - 1 if has_previous_page else None
        )
