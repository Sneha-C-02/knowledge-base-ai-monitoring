from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, asc
from typing import List, Optional
from src.knowledge_base_backend.domain.repositories.article_repository import ArticleRepository
from src.knowledge_base_backend.domain.entities.knowledge_base_article import KnowledgeBaseArticle
from src.knowledge_base_backend.domain.value_objects.article_search_criteria import ArticleSearchCriteria
from src.knowledge_base_backend.domain.value_objects.pagination_request import PaginationRequest
from src.knowledge_base_backend.domain.value_objects.pagination_result import PaginationResult
from src.knowledge_base_backend.infrastructure.database.models.article_model import ArticleModel
from src.knowledge_base_backend.infrastructure.database.models.instrument_model import InstrumentModel
from sqlalchemy.orm import selectinload

class SqlAlchemyArticleRepository(ArticleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        
    def _map_to_domain(self, model: ArticleModel) -> KnowledgeBaseArticle:
        instruments = [inst.name for inst in model.instruments] if model.instruments else []
        return KnowledgeBaseArticle(
            id=model.article_number,
            database_id=model.id,
            article_number=model.article_number,
            title=model.title,
            url=model.url,
            searchable_content=model.searchable_content,
            instruments=instruments,
            last_updated=model.source_updated_at
        )

    def _build_base_query(self, criteria: ArticleSearchCriteria):
        query = select(ArticleModel).options(selectinload(ArticleModel.instruments))
        
        if criteria.search_query:
            search_term = f"%{criteria.search_query}%"
            query = query.where(
                or_(
                    ArticleModel.article_number.ilike(search_term),
                    ArticleModel.title.ilike(search_term)
                    # Note: Full-text search with search_vector should go here via func.to_tsquery
                )
            )
            
        if criteria.instrument_name:
            query = query.join(ArticleModel.instruments).where(
                InstrumentModel.name == criteria.instrument_name
            )
            
        if criteria.sort_by:
            column = getattr(ArticleModel, criteria.sort_by, ArticleModel.id)
            if criteria.sort_direction == "descending":
                query = query.order_by(desc(column), asc(ArticleModel.id))
            else:
                query = query.order_by(asc(column), asc(ArticleModel.id))
        else:
            query = query.order_by(asc(ArticleModel.id))
            
        return query

    async def retrieve_paginated_articles(
        self, criteria: ArticleSearchCriteria, pagination: PaginationRequest
    ) -> PaginationResult[KnowledgeBaseArticle]:
        
        # Count total items
        count_query = select(func.count(ArticleModel.id))
        
        if criteria.search_query:
            search_term = f"%{criteria.search_query}%"
            count_query = count_query.where(
                or_(
                    ArticleModel.article_number.ilike(search_term),
                    ArticleModel.title.ilike(search_term)
                )
            )
            
        if criteria.instrument_name:
            count_query = count_query.join(ArticleModel.instruments).where(
                InstrumentModel.name == criteria.instrument_name
            )
            
        total_items_result = await self.session.execute(count_query)
        total_items = total_items_result.scalar() or 0
        
        # Get paginated items
        query = self._build_base_query(criteria)
        query = query.limit(pagination.page_size).offset(pagination.offset)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        items = [self._map_to_domain(model) for model in models]
        
        return PaginationResult.create(
            items=items,
            current_page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items
        )
        
    async def count_articles_matching_criteria(self, criteria: ArticleSearchCriteria) -> int:
        count_query = select(func.count(ArticleModel.id))
        if criteria.search_query:
            search_term = f"%{criteria.search_query}%"
            count_query = count_query.where(
                or_(
                    ArticleModel.article_number.ilike(search_term),
                    ArticleModel.title.ilike(search_term)
                )
            )
            
        if criteria.instrument_name:
            count_query = count_query.join(ArticleModel.instruments).where(
                InstrumentModel.name == criteria.instrument_name
            )
            
        result = await self.session.execute(count_query)
        return result.scalar() or 0
        
    async def retrieve_article_by_number(self, article_number: str) -> Optional[KnowledgeBaseArticle]:
        query = select(ArticleModel).options(selectinload(ArticleModel.instruments)).where(
            ArticleModel.article_number == article_number
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model:
            return self._map_to_domain(model)
        return None
        
    async def retrieve_article_by_database_id(self, database_id: int) -> Optional[KnowledgeBaseArticle]:
        query = select(ArticleModel).options(selectinload(ArticleModel.instruments)).where(
            ArticleModel.id == database_id
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model:
            return self._map_to_domain(model)
        return None
        
    async def retrieve_articles_by_identifiers(self, database_ids: List[int]) -> List[KnowledgeBaseArticle]:
        query = select(ArticleModel).options(selectinload(ArticleModel.instruments)).where(
            ArticleModel.id.in_(database_ids)
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._map_to_domain(model) for model in models]
        
    async def search_articles_by_full_text(self, criteria: ArticleSearchCriteria, limit: int) -> List[KnowledgeBaseArticle]:
        query = self._build_base_query(criteria).limit(limit)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._map_to_domain(model) for model in models]

    async def count_all_articles(self) -> int:
        query = select(func.count(ArticleModel.id))
        result = await self.session.execute(query)
        return result.scalar() or 0
