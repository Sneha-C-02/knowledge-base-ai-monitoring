from sqlalchemy import Column, BigInteger, ForeignKey
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base


class GroupPermissionModel(Base):
    __tablename__ = "group_permissions"

    group_id = Column(
        BigInteger,
        ForeignKey("user_groups.id", ondelete="CASCADE"),
        primary_key=True
    )

    permission_id = Column(
        BigInteger,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True
    )