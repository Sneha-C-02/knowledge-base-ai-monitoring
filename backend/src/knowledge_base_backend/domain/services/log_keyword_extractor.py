import re
from dataclasses import dataclass, field
from typing import List

# ---------------------------------------------------------------------------
# Keyword pattern dictionary — instrument-generic critical terms.
# Each key is a logical category name; the value is a compiled regex.
# Easy to extend: just add new entries to CRITICAL_PATTERNS.
# ---------------------------------------------------------------------------
CRITICAL_PATTERNS: dict[str, re.Pattern] = {
    "error":        re.compile(r"\b(error|fail(?:ed|ure)?|exception|abort(?:ed)?|crash|fatal|severe|fault)\b", re.IGNORECASE),
    "warning":      re.compile(r"\b(warn(?:ing)?|caution|deprecated|degraded|timeout|timed.out|retry)\b", re.IGNORECASE),
    "write_fail":   re.compile(r"failed to write|write error|unable to set|cannot set", re.IGNORECASE),
    "rio_status":   re.compile(r"\bRioStatus\b\s*(?:=>|=)\s*(-?\d+)", re.IGNORECASE),
    "threshold":    re.compile(r"\b(threshold|saturat(?:ed|ion)?|overflow|underflow|limit exceed(?:ed)?)\b", re.IGNORECASE),
    "connectivity": re.compile(r"\b(not respond(?:ing)?|unreachable|disconnect(?:ed)?|offline|unavailable)\b", re.IGNORECASE),
    "calibration":  re.compile(r"\b(calibrat(?:ion|e|ed)?|align(?:ment)?|resonan(?:ce)?|prescan|baseline)\b", re.IGNORECASE),
    "resolution":   re.compile(r"\b(resolution|mass\s+resolut|scan\s+function|tuning)\b", re.IGNORECASE),
    "hardware_param": re.compile(r"\b[A-Z][A-Z_]{3,}\s*(?:SETTING|MODE|STATUS|VALUE|PARAM)\b"),
    "voltage":      re.compile(r"\b(voltage|capillary|source|detector|high.?voltage)\b", re.IGNORECASE),
    "physics":      re.compile(r"\b(current|pressure|temperature|sensor|intensity|signal)\b", re.IGNORECASE),
    "memory":       re.compile(r"\b(memory|buffer|overflow|queue|deadlock|leak)\b", re.IGNORECASE),
    "acquisition":  re.compile(r"\b(acqui(?:re|red|sition)|scan|spectrum|dataBuffer)\b", re.IGNORECASE),
}

# Regex patterns for noise stripping — applied to matching lines before embedding
_TIMESTAMP_RE = re.compile(
    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\w+\s+\d+\s+\d+:\d+:\d+\s+(?:AM|PM)\s+[A-Za-z ]+:\s*"
)
_THREAD_ID_RE  = re.compile(r"\[\d{10,}\]")          # e.g., [20476553842352]
_MODULE_TAG_RE = re.compile(r"\[[A-Z]{2,6}\]\s*")    # e.g., [EPC]
_PAREN_PROC_RE = re.compile(r"\([A-Z][A-Za-z]+\):\s*")  # e.g., (EngineerServer):


@dataclass
class ExtractedKeywordEvent:
    severity: str                       # "critical" | "warning" | "info"
    component: str                      # e.g., "EngineerServer"
    cleaned_text: str                   # noise-stripped semantic text for embedding
    raw_line: str                       # original log line preserved for display
    matched_patterns: List[str] = field(default_factory=list)  # category names matched


class LogKeywordExtractor:
    """
    Scans log lines purely with regex — no LLM calls, no external I/O.
    Returns a list of ExtractedKeywordEvent for lines that match any
    critical pattern.  The cleaned_text on each event is suitable for
    passing directly to an embedding model.
    """

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    def extract_from_lines(self, lines: List[str]) -> List[ExtractedKeywordEvent]:
        """Process a list of raw log lines and return keyword events."""
        results: List[ExtractedKeywordEvent] = []
        for raw_line in lines:
            event = self._process_line(raw_line.rstrip("\n"))
            if event is not None:
                results.append(event)
        return results

    def extract_from_text(self, text: str) -> List[ExtractedKeywordEvent]:
        """Convenience wrapper: split text into lines first."""
        return self.extract_from_lines(text.splitlines())

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------
    def _process_line(self, raw_line: str) -> "ExtractedKeywordEvent | None":
        """Return an event if the line matches any critical pattern, else None."""
        matched: List[str] = []
        for category, pattern in CRITICAL_PATTERNS.items():
            if pattern.search(raw_line):
                matched.append(category)

        if not matched:
            return None

        severity = self._determine_severity(matched, raw_line)
        component = self._extract_component(raw_line)
        cleaned = self._clean_line(raw_line)

        return ExtractedKeywordEvent(
            severity=severity,
            component=component,
            cleaned_text=cleaned,
            raw_line=raw_line,
            matched_patterns=matched,
        )

    def _determine_severity(self, matched_categories: List[str], line: str) -> str:
        """Map matched categories to a severity level."""
        if "error" in matched_categories or "write_fail" in matched_categories or "rio_status" in matched_categories:
            # RioStatus => -1 is always critical; 0 may be OK
            rio_match = CRITICAL_PATTERNS["rio_status"].search(line)
            if rio_match:
                status_val = int(rio_match.group(1))
                if status_val != 0:
                    return "critical"
                # status 0 is success — treat as info
                return "info"
            return "critical"
        if "warning" in matched_categories or "threshold" in matched_categories or "connectivity" in matched_categories:
            return "warning"
        return "info"

    def _extract_component(self, raw_line: str) -> str:
        """Pull the parenthesised process name, e.g., 'EngineerServer'."""
        match = re.search(r"\(([A-Z][A-Za-z]+)\):", raw_line)
        return match.group(1) if match else "Unknown"

    def _clean_line(self, raw_line: str) -> str:
        """Strip timestamps, thread IDs, and module tags. Leave semantic text."""
        text = _TIMESTAMP_RE.sub("", raw_line)
        text = _THREAD_ID_RE.sub("", text)
        text = _MODULE_TAG_RE.sub("", text)
        text = _PAREN_PROC_RE.sub(r"", text)
        # Collapse multiple spaces
        text = re.sub(r"\s{2,}", " ", text).strip()
        return text
