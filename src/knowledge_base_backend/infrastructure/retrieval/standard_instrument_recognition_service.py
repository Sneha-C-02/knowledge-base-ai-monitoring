from typing import List, Optional
from src.knowledge_base_backend.domain.services.instrument_recognition_service import InstrumentRecognitionService
from src.knowledge_base_backend.domain.repositories.instrument_repository import InstrumentRepository

class StandardInstrumentRecognitionService(InstrumentRecognitionService):
    def __init__(self, instrument_repository: InstrumentRepository) -> None:
        self.instrument_repository = instrument_repository
        
    async def detect_instrument_name(self, query: str) -> Optional[str]:
        # A simple keyword match in a real implementation
        instruments = await self.instrument_repository.get_all()
        for inst in instruments:
            if inst.name.lower() in query.lower():
                return inst.name
        return None
