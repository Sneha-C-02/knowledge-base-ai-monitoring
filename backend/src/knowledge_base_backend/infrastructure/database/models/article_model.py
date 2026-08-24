from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base
from pgvector.sqlalchemy import Vector

article_instruments = Table(
    'article_instruments',
    Base.metadata,
    Column('article_id', BigInteger, ForeignKey('articles.id'), primary_key=True),
    Column('instrument_id', BigInteger, ForeignKey('instruments.id'), primary_key=True)
)

class ArticleModel(Base):
    __tablename__ = "articles"

    id = Column(BigInteger, primary_key=True)
    article_number = Column(String, unique=True, nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False)
    searchable_content = Column(Text, nullable=False)
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    
    article_embedding = Column(Vector(384))
    
    instruments = relationship("InstrumentModel", secondary=article_instruments)
