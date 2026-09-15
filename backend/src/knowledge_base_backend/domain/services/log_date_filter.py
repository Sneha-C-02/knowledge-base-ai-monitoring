"""Domain service for filtering log lines by date/time range."""

import re
from datetime import datetime
from typing import List, Optional, Tuple

# Common log timestamp patterns — order matters (most specific first).
_TIMESTAMP_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # "Mon Oct 20 11:32:42 AM GMT Summer Time:" (instrument log format)
    (
        re.compile(
            r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
            r"(\w{3}\s+\d{1,2}\s+\d{1,2}:\d{2}:\d{2}\s+(?:AM|PM))"
        ),
        "%b %d %I:%M:%S %p",
    ),
    # ISO-8601: "2026-09-01T14:07:38" or "2026-09-01 14:07:38"
    (
        re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"),
        "%Y-%m-%dT%H:%M:%S",
    ),
    # Syslog-style: "Sep  1 14:07:38"
    (
        re.compile(r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"),
        "%b %d %H:%M:%S",
    ),
]


class LogDateFilter:
    """
    Filters log lines to only those whose embedded timestamp falls within
    [date_from, date_to].  If neither bound is provided the original list
    is returned untouched.  Lines without a parseable timestamp are always
    kept (conservative — never drop content that cannot be dated).
    """

    @classmethod
    def filter_lines(
        cls,
        lines: List[str],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[str]:
        """Return lines whose timestamp is within the specified range."""
        if date_from is None and date_to is None:
            return lines

        filtered: List[str] = []
        for line in lines:
            ts = self._parse_timestamp(line)
            if ts is None:
                # Cannot determine date — keep the line (safe default)
                filtered.append(line)
                continue

            if date_from and ts < date_from:
                continue
            if date_to and ts > date_to:
                continue
            filtered.append(line)

        return filtered

    @staticmethod
    def _parse_timestamp(line: str) -> Optional[datetime]:
        """Attempt to extract a datetime from the beginning of a log line."""
        for pattern, fmt in _TIMESTAMP_PATTERNS:
            match = pattern.search(line)
            if match:
                raw = match.group(1).strip()
                # Normalise ISO separator
                if "T" not in raw and fmt == "%Y-%m-%dT%H:%M:%S":
                    fmt = "%Y-%m-%d %H:%M:%S"
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    continue
        return None
