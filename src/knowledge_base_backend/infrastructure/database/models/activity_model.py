from sqlalchemy import Column, BigInteger, String, Text, DateTime, Identity
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base

class SystemActivityModel(Base):
    __tablename__ = "system_activities"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    activity_identifier = Column(String, unique=True, nullable=False)
    activity_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    username = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
