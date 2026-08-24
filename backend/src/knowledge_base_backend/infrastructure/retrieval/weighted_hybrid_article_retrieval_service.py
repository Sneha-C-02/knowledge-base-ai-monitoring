import asyncio
import re
from typing import List, Optional, Dict
from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from src.knowledge_base_backend.domain.repositories.article_repository import ArticleRepository
from src.knowledge_base_backend.domain.repositories.article_vector_search_repository import ArticleVectorSearchRepository
from src.knowledge_base_backend.domain.services.embedding_generation_service import EmbeddingGenerationService
from src.knowledge_base_backend.domain.value_objects.article_search_criteria import ArticleSearchCriteria
from src.knowledge_base_backend.configuration.application_settings import settings
import math

class WeightedHybridArticleRetrievalService(HybridArticleRetrievalService):
    def __init__(
        self, 
        article_repository: ArticleRepository,
        vector_repository: ArticleVectorSearchRepository,
        embedding_service: EmbeddingGenerationService
    ) -> None:
        self.article_repository = article_repository
        self.vector_repository = vector_repository
        self.embedding_service = embedding_service

    def _extract_product_tokens(self, text: str) -> List[str]:
        tokens = []
        # Hyphenated models like P-200A
        tokens.extend(re.findall(r'\b[A-Za-z]+-\d+[A-Za-z]*\b', text, re.IGNORECASE))
        # Nine-digit parts
        tokens.extend(re.findall(r'\b\d{9}\b', text))
        # CamelCase and specific instrument names like MaldiChrom, ACQUITY, SYNAPT
        tokens.extend(re.findall(r'\b(?:MaldiChrom|ACQUITY|SYNAPT|Xevo|Alliance|Empower|MassLynx)\b', text, re.IGNORECASE))
        return [t.lower() for t in tokens]

    def _calculate_intent_score(self, query: str, article_title: str) -> float:
        q_lower = query.lower()
        t_lower = article_title.lower()
        score = 0.0
        
        is_procedure = any(w in q_lower for w in ['procedure', 'service', 'maintain', 'fix', 'troubleshoot', 'error', 'step', 'replace'])
        is_parts = any(w in q_lower for w in ['part', 'kit', 'included'])
        
        title_is_kit = 'kit' in t_lower
        title_is_procedure = any(w in t_lower for w in ['how to', 'procedure', 'error', 'replace'])
        
        if is_procedure and not is_parts:
            if title_is_procedure:
                score += settings.intent_match_boost
            if title_is_kit:
                score -= settings.intent_match_boost
                
        if is_parts and not is_procedure:
            if title_is_kit:
                score += settings.intent_match_boost
                
        return score

    async def retrieve_relevant_articles(
        self, query: str, instrument_name: Optional[str], limit: int
    ) -> List[RelevantArticleMatch]:
        
        criteria = ArticleSearchCriteria(search_query=query, instrument_name=None)
        full_text_results = await self.article_repository.search_articles_by_full_text(criteria, limit=limit*3)
        
        vector_matches = []
        if settings.vector_search_enabled:
            try:
                query_embedding = await self.embedding_service.generate_text_embedding(query)
                vector_matches = await self.vector_repository.retrieve_articles_by_vector_similarity(
                    query_embedding=query_embedding,
                    instrument_name=None,
                    minimum_similarity=settings.vector_similarity_threshold,
                    maximum_result_count=limit*3
                )
            except Exception as e:
                print(f"Vector retrieval failed: {e}")

        article_map: Dict[str, RelevantArticleMatch] = {}
        max_ts_rank = max((score for _, score in full_text_results), default=0.0)
        
        product_tokens = self._extract_product_tokens(query)
        nine_digit_ids = re.findall(r'\b\d{9}\b', query)
        
        def calculate_boosts(article) -> tuple[float, list]:
            boost = 0.0
            reasons = []
            
            # Exact Article ID Match
            if nine_digit_ids and article.article_number in nine_digit_ids:
                boost += settings.exact_article_id_boost
                reasons.append("Exact Article Number Match")
                
            # Entity Match
            t_lower = article.title.lower()
            for p_token in product_tokens:
                if p_token in t_lower:
                    boost += settings.entity_match_boost
                    reasons.append(f"Entity Match ({p_token})")
                    break
                    
            # Intent Match
            intent_score = self._calculate_intent_score(query, article.title)
            if intent_score > 0:
                reasons.append("Intent Match")
            elif intent_score < 0:
                reasons.append("Intent Mismatch Penalty")
            boost += intent_score
            
            # Instrument Match
            if instrument_name and instrument_name in article.instruments:
                boost += settings.instrument_match_boost
                reasons.append("Instrument Category Boost")
                
            return boost, list(set(reasons))
        
        for article, raw_score in full_text_results:
            normalized_ft = (raw_score / max_ts_rank) if max_ts_rank > 0 else 0.0
            boost, reasons = calculate_boosts(article)
            
            hybrid = (normalized_ft * settings.full_text_search_weight) + boost
            
            reason_str = ", ".join(reasons) if reasons else "Lexical Overlap"
            
            article_map[article.article_number] = RelevantArticleMatch(
                article=article,
                matched_instruments=article.instruments,
                full_text_score=normalized_ft,
                vector_similarity_score=0.0,
                combined_relevance_score=hybrid,
                retrieval_method="full_text",
                retrieval_reason=reason_str
            )
            
        for match in vector_matches:
            art_num = match.article.article_number
            vector_sim = match.vector_similarity_score
            hybrid_addition = vector_sim * settings.vector_search_weight
            
            if art_num in article_map:
                existing = article_map[art_num]
                new_hybrid = existing.combined_relevance_score + hybrid_addition
                new_reasons = existing.retrieval_reason.split(", ") if existing.retrieval_reason != "Lexical Overlap" else ["Lexical Overlap"]
                new_reasons.append("Semantic Match")
                
                article_map[art_num] = RelevantArticleMatch(
                    article=existing.article,
                    matched_instruments=existing.matched_instruments,
                    full_text_score=existing.full_text_score,
                    vector_similarity_score=vector_sim,
                    combined_relevance_score=new_hybrid,
                    retrieval_method="hybrid",
                    retrieval_reason=", ".join(set(new_reasons))
                )
            else:
                boost, reasons = calculate_boosts(match.article)
                hybrid = hybrid_addition + boost
                reasons.append("Semantic Match")
                
                article_map[art_num] = RelevantArticleMatch(
                    article=match.article,
                    matched_instruments=match.article.instruments,
                    full_text_score=0.0,
                    vector_similarity_score=vector_sim,
                    combined_relevance_score=hybrid,
                    retrieval_method="vector",
                    retrieval_reason=", ".join(set(reasons))
                )
                
        def is_sufficiently_relevant(m: RelevantArticleMatch) -> bool:
            if m.combined_relevance_score < settings.minimum_hybrid_score_threshold:
                return False
            if "Exact Article Number Match" in m.retrieval_reason:
                return True
            if m.combined_relevance_score >= 0.50:
                return True
            if "Entity Match" in m.retrieval_reason:
                return True
            if "Semantic Match" in m.retrieval_reason and "Lexical Overlap" in m.retrieval_reason:
                return True
            return False

        sorted_matches = sorted(article_map.values(), key=lambda x: x.combined_relevance_score, reverse=True)
        final_matches = [m for m in sorted_matches if is_sufficiently_relevant(m)]
        
        return final_matches[:limit]
