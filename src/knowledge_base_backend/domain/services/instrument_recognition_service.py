from typing import Protocol, Optional

class InstrumentRecognitionService(Protocol):
    async def detect_instrument_name(self, query: str) -> Optional[str]: ...
