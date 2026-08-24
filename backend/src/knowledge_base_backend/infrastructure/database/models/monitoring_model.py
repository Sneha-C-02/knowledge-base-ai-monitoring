from sqlalchemy import Column, BigInteger, String, Text, DateTime, Identity, Integer, ForeignKey
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base
from sqlalchemy.orm import relationship

class MonitoringRunModel(Base):
    __tablename__ = "monitoring_runs"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    monitoring_identifier = Column(String, unique=True, nullable=False)
    requested_by_username = Column(String, nullable=True)
    overall_status = Column(String, nullable=False)
    uploaded_file_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    
    issues = relationship("MonitoringIssueModel", back_populates="run")


class MonitoringIssueModel(Base):
    __tablename__ = "monitoring_issues"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    issue_identifier = Column(String, unique=True, nullable=False)
    monitoring_run_id = Column(BigInteger, ForeignKey("monitoring_runs.id"))
    severity = Column(String, nullable=False)
    event_timestamp = Column(DateTime(timezone=True), nullable=True)
    pattern = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    related_article_number = Column(String, nullable=True)
    related_article_url = Column(Text, nullable=True)
    
    run = relationship("MonitoringRunModel", back_populates="issues")
