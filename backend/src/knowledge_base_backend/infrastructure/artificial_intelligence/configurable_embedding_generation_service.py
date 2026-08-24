import asyncio
from typing import List, Any
from src.knowledge_base_backend.domain.services.embedding_generation_service import EmbeddingGenerationService
from src.knowledge_base_backend.domain.value_objects.text_embedding import TextEmbedding
from src.knowledge_base_backend.configuration.application_settings import settings

class ConfigurableEmbeddingGenerationService(EmbeddingGenerationService):
    def __init__(self, **kwargs: Any) -> None:
        self.provider = settings.embedding_provider
        self.dimension = settings.embedding_dimension
        if self.provider == "sentence-transformers":
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(settings.embedding_model_name or "all-MiniLM-L6-v2")
        else:
            self.model = None

    async def generate_text_embedding(self, text: str) -> TextEmbedding:
        if self.provider == "sentence-transformers" and self.model:
            loop = asyncio.get_running_loop()
            embedding = await loop.run_in_executor(None, self.model.encode, text)
            return TextEmbedding(values=tuple(embedding.tolist()), dimension=self.dimension, model_identifier=self.retrieve_model_identifier())
        return TextEmbedding(values=tuple([0.0] * self.dimension), dimension=self.dimension, model_identifier=self.retrieve_model_identifier())

    async def generate_multiple_text_embeddings(self, texts: List[str]) -> List[TextEmbedding]:
        if self.provider == "sentence-transformers" and self.model:
            loop = asyncio.get_running_loop()
            embeddings = await loop.run_in_executor(None, self.model.encode, texts)
            return [TextEmbedding(values=tuple(emb.tolist()), dimension=self.dimension, model_identifier=self.retrieve_model_identifier()) for emb in embeddings]
        return [TextEmbedding(values=tuple([0.0] * self.dimension), dimension=self.dimension, model_identifier=self.retrieve_model_identifier()) for _ in texts]

    def retrieve_embedding_dimension(self) -> int:
        return self.dimension

    def retrieve_model_identifier(self) -> str:
        return settings.embedding_model_name
