"""
Tests for the instrument normalizer module.

Validates alias resolution, case-insensitive deduplication,
whitespace normalization, and unreviewed name tracking.
"""

import json
import os
import tempfile

import pytest

from waters_knowledge_base.extraction.instrument_normalizer import (
    InstrumentNameNormalizer,
)


@pytest.fixture
def test_alias_file(tmp_path) -> str:
    """Create a temporary alias file for testing."""
    aliases = {
        "acquity uplc": "ACQUITY UPLC",
        "acquity uplc system": "ACQUITY UPLC",
        "empower": "Empower",
        "empower software": "Empower",
        "qsm": "QSM",
        "quaternary solvent manager": "QSM",
    }
    alias_path = tmp_path / "test_aliases.json"
    with open(alias_path, "w", encoding="utf-8") as alias_file:
        json.dump(aliases, alias_file)
    return str(alias_path)


@pytest.fixture
def normalizer(test_alias_file: str) -> InstrumentNameNormalizer:
    """Create a normalizer with test aliases."""
    return InstrumentNameNormalizer(alias_file_path=test_alias_file)


class TestAliasResolution:
    """Tests for instrument alias normalization."""

    def test_resolves_known_alias(self, normalizer: InstrumentNameNormalizer):
        """Known aliases should resolve to canonical names."""
        result = normalizer.normalize_instrument_name("acquity uplc")
        assert result == "ACQUITY UPLC"

    def test_case_insensitive_lookup(self, normalizer: InstrumentNameNormalizer):
        """Alias lookup should be case-insensitive."""
        result = normalizer.normalize_instrument_name("ACQUITY UPLC")
        assert result == "ACQUITY UPLC"

    def test_resolves_alternate_alias(self, normalizer: InstrumentNameNormalizer):
        """Multiple aliases should map to the same canonical name."""
        result1 = normalizer.normalize_instrument_name("empower")
        result2 = normalizer.normalize_instrument_name("Empower Software")
        assert result1 == "Empower"
        assert result2 == "Empower"

    def test_preserves_unknown_name(self, normalizer: InstrumentNameNormalizer):
        """Unknown names should be preserved in cleaned form."""
        result = normalizer.normalize_instrument_name("Unknown Instrument XYZ")
        assert result == "Unknown Instrument XYZ"

    def test_empty_string_returns_empty(self, normalizer: InstrumentNameNormalizer):
        """Empty strings should return empty."""
        result = normalizer.normalize_instrument_name("")
        assert result == ""

    def test_whitespace_only_returns_empty(self, normalizer: InstrumentNameNormalizer):
        """Whitespace-only strings should return empty."""
        result = normalizer.normalize_instrument_name("   ")
        assert result == ""


class TestWhitespaceNormalization:
    """Tests for whitespace handling during normalization."""

    def test_trims_leading_trailing_whitespace(
        self, normalizer: InstrumentNameNormalizer
    ):
        """Leading and trailing whitespace should be trimmed."""
        result = normalizer.normalize_instrument_name("  empower  ")
        assert result == "Empower"

    def test_collapses_internal_whitespace(
        self, normalizer: InstrumentNameNormalizer
    ):
        """Multiple internal spaces should be collapsed."""
        result = normalizer.normalize_instrument_name("acquity   uplc")
        assert result == "ACQUITY UPLC"


class TestDeduplication:
    """Tests for case-insensitive deduplication."""

    def test_removes_duplicates(self, normalizer: InstrumentNameNormalizer):
        """Duplicate names (case-insensitive) should be removed."""
        result = normalizer.normalize_instrument_names(
            ["Empower", "EMPOWER", "empower"]
        )
        assert len(result) == 1
        assert result[0] == "Empower"

    def test_sorts_results(self, normalizer: InstrumentNameNormalizer):
        """Results should be sorted case-insensitively."""
        result = normalizer.normalize_instrument_names(
            ["QSM", "ACQUITY UPLC", "Empower"]
        )
        assert result == ["ACQUITY UPLC", "Empower", "QSM"]

    def test_removes_empty_strings(self, normalizer: InstrumentNameNormalizer):
        """Empty strings should be filtered out."""
        result = normalizer.normalize_instrument_names(
            ["Empower", "", "  ", "QSM"]
        )
        assert "" not in result
        assert len(result) == 2


class TestUnreviewedNameTracking:
    """Tests for tracking instrument names not found in aliases."""

    def test_tracks_unreviewed_names(self, normalizer: InstrumentNameNormalizer):
        """Names not in the alias map should be tracked."""
        normalizer.normalize_instrument_name(
            "Brand New Instrument", source_article_url="https://example.com"
        )
        unreviewed = normalizer.get_unreviewed_names()
        assert len(unreviewed) == 1
        assert unreviewed[0]["cleaned_value"] == "Brand New Instrument"

    def test_counts_occurrences(self, normalizer: InstrumentNameNormalizer):
        """Repeated unreviewed names should increment the count."""
        normalizer.normalize_instrument_name("Unknown Device")
        normalizer.normalize_instrument_name("Unknown Device")
        normalizer.normalize_instrument_name("Unknown Device")
        unreviewed = normalizer.get_unreviewed_names()
        assert len(unreviewed) == 1
        assert unreviewed[0]["occurrence_count"] == 3

    def test_does_not_track_known_aliases(
        self, normalizer: InstrumentNameNormalizer
    ):
        """Known aliases should not appear in unreviewed names."""
        normalizer.normalize_instrument_name("empower")
        unreviewed = normalizer.get_unreviewed_names()
        assert len(unreviewed) == 0
