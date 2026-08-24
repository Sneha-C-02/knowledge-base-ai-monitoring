"""
Instrument name normalizer for Waters Knowledge Base articles.

Applies alias resolution, whitespace normalization, and case-insensitive
deduplication to produce canonical instrument names.
"""

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_ALIAS_FILE_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "configuration",
    "instrument_aliases.json",
)


class InstrumentNameNormalizer:
    """Normalizes raw instrument names to canonical forms using an alias map."""

    def __init__(self, alias_file_path: str = DEFAULT_ALIAS_FILE_PATH):
        self.alias_file_path: str = alias_file_path
        self.alias_map: dict[str, str] = {}
        self.unreviewed_names: dict[str, dict[str, Any]] = {}
        self._load_alias_map()

    def _load_alias_map(self) -> None:
        """Load the alias map from JSON configuration."""
        if not os.path.exists(self.alias_file_path):
            logger.warning("Alias file not found: '%s'", self.alias_file_path)
            return
        try:
            with open(self.alias_file_path, "r", encoding="utf-8") as f:
                raw_aliases = json.load(f)
            if isinstance(raw_aliases, dict):
                for key, val in raw_aliases.items():
                    self.alias_map[key.strip().lower()] = val
                logger.info("Loaded %d aliases.", len(self.alias_map))
        except (json.JSONDecodeError, OSError) as err:
            logger.error("Failed to load aliases: %s", err)

    def normalize_instrument_name(self, raw_name: str, source_article_url: str = "") -> str:
        """Normalize a single instrument name."""
        cleaned = re.sub(r"\s+", " ", raw_name.strip()) if raw_name else ""
        if not cleaned:
            return ""
        lookup = cleaned.lower()
        if lookup in self.alias_map:
            return self.alias_map[lookup]
        if lookup not in self.unreviewed_names:
            self.unreviewed_names[lookup] = {
                "original_value": raw_name, "cleaned_value": cleaned,
                "source_article_url": source_article_url, "occurrence_count": 1,
            }
        else:
            self.unreviewed_names[lookup]["occurrence_count"] += 1
        return cleaned

    def normalize_instrument_names(self, raw_names: list[str], source_article_url: str = "") -> list[str]:
        """Normalize, deduplicate, and sort a list of instrument names."""
        seen: set[str] = set()
        result: list[str] = []
        for raw in raw_names:
            canonical = self.normalize_instrument_name(raw, source_article_url)
            if canonical and canonical.lower() not in seen:
                seen.add(canonical.lower())
                result.append(canonical)
        return sorted(result, key=lambda n: n.lower())

    def get_unreviewed_names(self) -> list[dict[str, Any]]:
        return list(self.unreviewed_names.values())
