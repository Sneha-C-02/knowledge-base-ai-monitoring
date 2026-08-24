from src.knowledge_base_backend.application.models.embedding_indexing_models import EmbeddingIndexingResult

class IndexKnowledgeBaseArticleEmbeddingsUseCase:
    def __init__(self) -> None:
        pass
        
    async def execute(self, batch_size: int = 100) -> EmbeddingIndexingResult:
        return EmbeddingIndexingResult(processed_count=0, failed_count=0)
