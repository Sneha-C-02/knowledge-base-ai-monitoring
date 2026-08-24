from typing import List, Optional
from src.knowledge_base_backend.domain.services.instrument_recognition_service import InstrumentRecognitionService
from src.knowledge_base_backend.domain.repositories.instrument_repository import InstrumentRepository

class StandardInstrumentRecognitionService(InstrumentRecognitionService):
    def __init__(self, instrument_repository: InstrumentRepository) -> None:
        self.instrument_repository = instrument_repository
        
    async def detect_instrument_name(self, query: str) -> Optional[str]:
        import re
        instruments = await self.instrument_repository.get_all()
        for inst in instruments:
            # Prevent 'CE' from matching 'procedure' by using word boundaries
            pattern = r'\b' + re.escape(inst.name.lower()) + r'\b'
            if re.search(pattern, query.lower()):
                return inst.name
        return None
