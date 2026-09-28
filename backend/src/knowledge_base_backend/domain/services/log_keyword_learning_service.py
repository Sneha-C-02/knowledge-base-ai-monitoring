"""Learns recurring, error-related vocabulary from parsed log events.

This module never talks to an LLM or performs I/O — it purely derives
candidate search keywords from lines that `LogKeywordExtractor` already
classified as "critical" or "warning" severity, so every suggestion this
service proposes is, by construction, related to an error or warning
condition observed in a real log file.

The caller (an application use case) is responsible for persisting the
returned candidates with frequency counters. That accumulation over many
analysis runs is what allows the system to "learn": the more often a term
shows up in error/warning lines across uploaded logs, the more prominently
it should be suggested in later keyword searches.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from src.knowledge_base_backend.domain.services.log_keyword_extractor import (
    CRITICAL_PATTERNS,
    ExtractedKeywordEvent,
)

# Only categories that actually drive "critical"/"warning" severity in
# LogKeywordExtractor are considered here, so learned keywords stay tightly
# scoped to genuine error/warning vocabulary — never incidental physics or
# hardware-parameter terms that might merely share a line with a real error.
_ERROR_RELEVANT_CATEGORIES = {
    "error",
    "warning",
    "write_fail",
    "rio_status",
    "threshold",
    "connectivity",
}
_LEARNABLE_SEVERITIES = {"critical", "warning"}
_MIN_KEYWORD_LENGTH = 3
_MAX_KEYWORD_LENGTH = 40


@dataclass(frozen=True)
class LearnedKeywordCandidate:
    """A single error-related keyword occurrence observed in one log line."""

    keyword: str
    severity: str  # "critical" | "warning"


class LogKeywordLearningService:
    """Derives LearnedKeywordCandidate objects from already-extracted log events."""

    def extract_candidates(self, events: List[ExtractedKeywordEvent]) -> List[LearnedKeywordCandidate]:
        """Return one candidate per error-related term found in critical/warning events."""
        candidates: List[LearnedKeywordCandidate] = []
        for event in events:
            if event.severity not in _LEARNABLE_SEVERITIES:
                continue
            for category in event.matched_patterns:
                if category not in _ERROR_RELEVANT_CATEGORIES:
                    continue
                candidates.extend(self._candidates_for_category(category, event))
        return candidates

    def _candidates_for_category(self, category: str, event: ExtractedKeywordEvent) -> List[LearnedKeywordCandidate]:
        if category == "rio_status":
            # The matched text always includes a variable numeric status code,
            # so a stable label is far more useful as a suggested search term
            # than the literal, ever-changing "RioStatus => -3" substring.
            return [LearnedKeywordCandidate(keyword="riostatus error", severity=event.severity)]

        pattern = CRITICAL_PATTERNS[category]
        results: List[LearnedKeywordCandidate] = []
        for match in pattern.finditer(event.raw_line):
            term = self._normalize(match.group(0))
            if term:
                results.append(LearnedKeywordCandidate(keyword=term, severity=event.severity))
        return results

    @staticmethod
    def _normalize(raw: str) -> Optional[str]:
        term = re.sub(r"\s{2,}", " ", raw.strip().lower())
        term = term.strip(".,:;()[]{}\"'")
        if len(term) < _MIN_KEYWORD_LENGTH or len(term) > _MAX_KEYWORD_LENGTH:
            return None
        if term.isdigit():
            return None
        return term
