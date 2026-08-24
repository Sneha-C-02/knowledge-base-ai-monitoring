from dataclasses import dataclass

@dataclass
class EmbeddingIndexingResult:
    processed_count: int
    failed_count: int
