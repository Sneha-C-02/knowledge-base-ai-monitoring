from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime
from sqlalchemy.orm import mapped_column
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base
from sqlalchemy import Identity

class UserModel(Base):
    __tablename__ = "application_users"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
