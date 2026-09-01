from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from src.knowledge_base_backend.domain.repositories.instrument_repository import InstrumentRepository
from src.knowledge_base_backend.domain.entities.instrument import Instrument
from src.knowledge_base_backend.infrastructure.database.models.instrument_model import InstrumentModel

class SqlAlchemyInstrumentRepository(InstrumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        
    def _map_to_domain(self, model: InstrumentModel) -> Instrument:
        return Instrument(id=model.id, name=model.name)
        
    async def get_by_id(self, id: int) -> Optional[Instrument]:
        model = await self.session.get(InstrumentModel, id)
        if model:
            return self._map_to_domain(model)
        return None
        
    async def get_by_name(self, name: str) -> Optional[Instrument]:
        query = select(InstrumentModel).where(InstrumentModel.name == name)
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model:
            return self._map_to_domain(model)
        return None
        
    async def get_all(self) -> List[Instrument]:
        query = select(InstrumentModel).order_by(InstrumentModel.name)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._map_to_domain(model) for model in models]

    async def create(self, name: str) -> Instrument:
        model = InstrumentModel(name=name)
        self.session.add(model)
        await self.session.flush()
        # We flush so that the model gets its ID populated, but the actual 
        # commit is handled by the caller/middleware.
        return self._map_to_domain(model)
