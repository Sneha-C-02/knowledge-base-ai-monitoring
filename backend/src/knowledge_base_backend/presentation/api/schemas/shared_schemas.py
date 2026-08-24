from pydantic import BaseModel, ConfigDict
from typing import Optional

class ErrorDetails(BaseModel):
    code: str
    message: str
    request_identifier: str
    details: Optional[dict] = None

class StandardErrorResponse(BaseModel):
    error: ErrorDetails
    
    model_config = ConfigDict(populate_by_name=True)

class PaginationMetadataSchema(BaseModel):
    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next_page: bool
    has_previous_page: bool
    next_page: Optional[int]
    previous_page: Optional[int]
