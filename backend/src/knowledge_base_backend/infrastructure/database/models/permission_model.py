from sqlalchemy import Column, BigInteger, String, Text, Identity
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base


class PermissionModel(Base):
    __tablename__ = "permissions"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)