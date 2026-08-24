from sqlalchemy import Column, BigInteger, String
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base

class InstrumentModel(Base):
    __tablename__ = "instruments"

    id = Column(BigInteger, primary_key=True)
    name = Column(String, unique=True, nullable=False)
