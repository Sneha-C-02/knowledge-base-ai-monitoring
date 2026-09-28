from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import re
from typing import List, Tuple, Optional

from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.domain.services.log_date_filter import LogDateFilter
from src.knowledge_base_backend.domain.services.log_file_validator import LogFileValidator
from src.knowledge_base_backend.infrastructure.artificial_intelligence.groq_dashboard_analysis_service import GroqDashboardAnalysisService


@dataclass
class KeywordSearchResult:
    keywords: List[str]
    findings: List[dict]


class SearchLogKeywordsUseCase:
    """Searches only caller-supplied terms and has no persistence side effects."""

    def __init__(
        self,
        validator: LogFileValidator,
        ai_service: GroqDashboardAnalysisService,
        retrieval_service: Optional[HybridArticleRetrievalService] = None,
    ) -> None:
        self.validator = validator
        self.ai_service = ai_service
        self.retrieval_service = retrieval_service

    @staticmethod
    def _normalize_keywords(keywords: List[str]) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for value in keywords:
            for term in re.split(r"[,\n]", value):
                cleaned = " ".join(term.strip().split())
                key = cleaned.casefold()
                if cleaned and key not in seen:
                    normalized.append(cleaned)
                    seen.add(key)
        return normalized

    @staticmethod
    def _last_word_forms(word: str) -> List[str]:
        """Produce basic English inflection variants; never semantic synonyms."""
        word = word.casefold()
        forms = {word}
        roots = {word}
        if word.endswith("ies") and len(word) > 3:
            roots.add(word[:-3] + "y")
        elif word.endswith("ied") and len(word) > 3:
            roots.add(word[:-3] + "y")
        elif word.endswith("ing") and len(word) > 4:
            roots.add(word[:-3])
        elif word.endswith("ed") and len(word) > 3:
            roots.add(word[:-2])
        elif word.endswith("es") and len(word) > 3:
            roots.add(word[:-2])
        elif word.endswith("s") and len(word) > 2:
            roots.add(word[:-1])

        for root in roots:
            if len(root) < 2:
                continue
            forms.update({root, root + "s", root + "ed", root + "ing"})
            if root.endswith("y"):
                forms.update({root[:-1] + "ies", root[:-1] + "ied", root[:-1] + "ying"})
            elif root.endswith("e"):
                forms.update({root + "s", root + "d", root[:-1] + "ing"})
            elif root.endswith(("s", "x", "z", "ch", "sh")):
                forms.add(root + "es")
        return sorted(forms, key=len, reverse=True)

    @classmethod
    def _pattern_for_keyword(cls, keyword: str) -> re.Pattern[str]:
        words = keyword.casefold().split()
        prefix = r"\s+".join(re.escape(word) for word in words[:-1])
        last = "|".join(re.escape(form) for form in cls._last_word_forms(words[-1]))
        phrase = f"{prefix}\\s+(?:{last})" if prefix else f"(?:{last})"
        return re.compile(rf"(?<!\w){phrase}(?!\w)", re.IGNORECASE)

    async def execute(
        self,
        files: List[Tuple[str, bytes]],
        keywords: List[str],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> KeywordSearchResult:
        normalized = self._normalize_keywords(keywords)
        if not normalized:
            raise ValueError("Select or enter at least one keyword")

        patterns = [(keyword, self._pattern_for_keyword(keyword)) for keyword in normalized]
        findings: List[dict] = []
        for filename, contents in files:
            stream = BytesIO(contents)
            self.validator.validate_uploaded_log_file(filename, stream)
            lines = contents.decode("utf-8", errors="replace").splitlines()
            if date_from or date_to:
                lines = LogDateFilter.filter_lines(lines, date_from, date_to)
            for index, line in enumerate(lines):
                for keyword, pattern in patterns:
                    for match in pattern.finditer(line):
                        start, end = max(0, index - 5), min(len(lines), index + 6)
                        findings.append({
                            "keyword": keyword,
                            "filename": filename,
                            "line_number": index + 1,
                            "matched_text": match.group(0),
                            "context": lines[start:end],
                            "context_start_line": start + 1,
                        })

        classifications = await self.ai_service.classify_keyword_findings(findings)
        for finding, classification in zip(findings, classifications):
            finding.update(classification)

        if self.retrieval_service:
            for finding in findings:
                finding["kb_article"] = None
                candidates: List[str] = []
                for key in ("search_query", "error_type", "keyword", "matched_text"):
                    v = finding.get(key)
                    if v and isinstance(v, str) and v.strip() and v.strip() not in candidates:
                        candidates.append(v.strip())

                matches = []
                for cand in candidates:
                    try:
                        matches = await self.retrieval_service.retrieve_relevant_articles(cand, None, limit=1)
                        if matches:
                            break
                    except Exception:
                        continue

                if matches:
                    top = matches[0]
                    content = top.article.searchable_content or ""
                    snippet = content[:280].strip() + ("..." if len(content) > 280 else "")
                    finding["kb_article"] = {
                        "id": str(top.article.id),
                        "database_id": top.article.database_id,
                        "article_number": top.article.article_number,
                        "title": top.article.title,
                        "url": top.article.url or f"/article/{top.article.article_number}",
                        "summary": snippet,
                        "relevance_score": round(float(top.combined_relevance_score), 2),
                        "retrieval_reason": top.retrieval_reason or "Direct match for diagnosed problem",
                    }

        return KeywordSearchResult(keywords=normalized, findings=findings)
