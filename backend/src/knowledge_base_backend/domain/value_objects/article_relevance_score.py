from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ArticleRelevanceScore:
    full_text_score: float
    vector_similarity_score: float
    instrument_match_score: float
    combined_relevance_score: float

    def __post_init__(self) -> None:
        for val in (self.full_text_score, self.vector_similarity_score, self.instrument_match_score, self.combined_relevance_score):
            if math.isnan(val) or math.isinf(val):
                raise ValueError("Score cannot be NaN or Infinite.")
        
        # Clamp combined relevance score between 0 and 1 safely
        object.__setattr__(self, 'combined_relevance_score', max(0.0, min(1.0, self.combined_relevance_score)))
