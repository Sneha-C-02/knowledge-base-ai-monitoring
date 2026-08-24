from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class TextEmbedding:
    values: Tuple[float, ...]
    dimension: int
    model_identifier: str

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("Embedding values cannot be empty.")
        if len(self.values) != self.dimension:
            raise ValueError(f"Embedding dimension mismatch. Expected {self.dimension}, got {len(self.values)}.")
