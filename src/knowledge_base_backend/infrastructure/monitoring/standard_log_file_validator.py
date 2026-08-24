from typing import BinaryIO
import os
from src.knowledge_base_backend.domain.services.log_file_validator import LogFileValidator
from src.knowledge_base_backend.domain.exceptions.monitoring_exceptions import InvalidLogFileError
from src.knowledge_base_backend.configuration.application_settings import settings

class StandardLogFileValidator(LogFileValidator):
    def validate_uploaded_log_file(self, filename: str, file_stream: BinaryIO) -> None:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.allowed_extensions_list:
            raise InvalidLogFileError(f"Extension {ext} is not allowed")
            
        file_stream.seek(0, os.SEEK_END)
        size = file_stream.tell()
        file_stream.seek(0)
        
        if size > settings.maximum_log_file_size_bytes:
            raise InvalidLogFileError(f"File {filename} exceeds maximum allowed size")
