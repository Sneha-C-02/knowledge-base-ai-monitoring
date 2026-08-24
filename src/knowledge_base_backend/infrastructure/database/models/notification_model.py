from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, Identity
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base

class SystemNotificationModel(Base):
    __tablename__ = "system_notifications"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    notification_identifier = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
