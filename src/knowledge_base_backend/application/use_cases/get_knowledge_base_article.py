from src.knowledge_base_backend.domain.repositories.article_repository import ArticleRepository
from src.knowledge_base_backend.domain.entities.knowledge_base_article import KnowledgeBaseArticle
from src.knowledge_base_backend.domain.exceptions.article_exceptions import ArticleNotFoundError

class GetKnowledgeBaseArticleUseCase:
    def __init__(self, article_repository: ArticleRepository) -> None:
        self.article_repository = article_repository

    async def execute(self, identifier: str) -> KnowledgeBaseArticle:
        if identifier.isdigit():
            article = await self.article_repository.retrieve_article_by_database_id(int(identifier))
        else:
            article = await self.article_repository.retrieve_article_by_number(identifier)

        if not article:
            raise ArticleNotFoundError(f"Article with identifier {identifier} not found")

        return article
