from typing import Protocol
from datetime import datetime

class DateTimeProvider(Protocol):
    def get_current_utc_time(self) -> datetime: ...
