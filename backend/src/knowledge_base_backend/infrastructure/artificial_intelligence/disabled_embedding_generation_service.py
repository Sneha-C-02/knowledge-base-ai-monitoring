from typing import List
from src.knowledge_base_backend.domain.services.embedding_generation_service import EmbeddingGenerationService
from src.knowledge_base_backend.domain.value_objects.text_embedding import TextEmbedding

class DisabledEmbeddingGenerationService(EmbeddingGenerationService):
    async def generate_text_embedding(self, text: str) -> TextEmbedding:
        raise NotImplementedError("Embedding generation is disabled")
        
    async def generate_multiple_text_embeddings(self, texts: List[str]) -> List[TextEmbedding]:
        raise NotImplementedError("Embedding generation is disabled")
        
    def retrieve_embedding_dimension(self) -> int:
        return 0
        
    def retrieve_model_identifier(self) -> str:
        return "disabled"
