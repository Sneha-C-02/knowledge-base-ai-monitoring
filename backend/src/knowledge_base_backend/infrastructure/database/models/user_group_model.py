from sqlalchemy import Column, BigInteger, String, Text, Boolean, Identity
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base


class UserGroupModel(Base):
    __tablename__ = "user_groups"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)