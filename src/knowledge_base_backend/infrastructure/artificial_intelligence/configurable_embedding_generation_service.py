from typing import List
from src.knowledge_base_backend.domain.services.embedding_generation_service import EmbeddingGenerationService
from src.knowledge_base_backend.domain.value_objects.text_embedding import TextEmbedding
import httpx

class ConfigurableEmbeddingGenerationService(EmbeddingGenerationService):
    def __init__(self, api_key: str, model_name: str, dimension: int) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.dimension = dimension
        self.client = httpx.AsyncClient()

    async def generate_text_embedding(self, text: str) -> TextEmbedding:
        # Mock external call
        return TextEmbedding(values=tuple([0.0]*self.dimension), dimension=self.dimension, model_identifier=self.model_name)
        
    async def generate_multiple_text_embeddings(self, texts: List[str]) -> List[TextEmbedding]:
        # Mock external call
        return [await self.generate_text_embedding(t) for t in texts]
        
    def retrieve_embedding_dimension(self) -> int:
        return self.dimension
        
    def retrieve_model_identifier(self) -> str:
        return self.model_name
