from typing import Protocol
from typing import BinaryIO

class LogFileValidator(Protocol):
    def validate_uploaded_log_file(self, filename: str, file_stream: BinaryIO) -> None: ...
