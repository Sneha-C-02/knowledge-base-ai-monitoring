from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, Identity, ForeignKey
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base


class InstrumentMemoryModel(Base):
    __tablename__ = "instrument_memory"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    instrument_id = Column(BigInteger, ForeignKey("instruments.id"), nullable=False, index=True)
    instrument_name = Column(String, nullable=False)
    analysis_timestamp = Column(DateTime(timezone=True), nullable=False)
    log_filename = Column(String, nullable=False)
    critical_incidents = Column(Integer, nullable=False, default=0)
    warnings = Column(Integer, nullable=False, default=0)
    errors = Column(Integer, nullable=False, default=0)
    healthy_apps = Column(Integer, nullable=False, default=0)
    ai_summary = Column(Text, nullable=False)
    raw_issues_json = Column(Text, nullable=True)
