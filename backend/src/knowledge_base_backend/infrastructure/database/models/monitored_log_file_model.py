from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, Identity, ForeignKey
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base


class MonitoredLogFileModel(Base):
    __tablename__ = "monitored_log_files"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    instrument_id = Column(BigInteger, ForeignKey("instruments.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    total_lines_analyzed = Column(Integer, nullable=False, default=0)
    full_context_summary = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
