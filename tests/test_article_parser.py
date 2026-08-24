"""
Tests for the article parser module.

Validates extraction of article number, title, canonical URL,
main content, and source date from sample HTML fixtures.
"""

import os
import pytest

from waters_knowledge_base.extraction.article_parser import (
    extract_article_information,
)


@pytest.fixture
def sample_article_html() -> str:
    """Load the sample article HTML fixture."""
    fixture_path = os.path.join(
        os.path.dirname(__file__), "fixtures", "sample_article.html"
    )
    with open(fixture_path, "r", encoding="utf-8") as fixture_file:
        return fixture_file.read()


@pytest.fixture
def sample_response_url() -> str:
    """Return a sample response URL for testing."""
    return "https://www.waters.com/nextgen/us/en/support/knowledge-base/WKB12345.html"


class TestArticleNumberExtraction:
    """Tests for article number extraction."""

    def test_extracts_article_number_from_metadata(
        self, sample_article_html: str, sample_response_url: str
    ):
        """Article number should be extracted from meta tag."""
        result = extract_article_information(
            sample_article_html, sample_response_url
        )
        assert result.article_number == "WKB12345"

    def test_article_number_is_uppercase(
        self, sample_article_html: str, sample_response_url: str
    ):
        """Article number should always be normalized to uppercase."""
        result = extract_article_information(
            sample_article_html, sample_response_url
        )
        assert result.article_number == result.article_number.upper()

    def test_extracts_from_url_when_no_metadata(self):
        """Should fall back to URL-based extraction."""
        html = "<html><head><title>Test</title></head><body><p>Content</p></body></html>"
        url = "https://www.waters.com/support/knowledge-base/wkb99999.html"
        result = extract_article_information(html, url)
        assert result.article_number == "WKB99999"

    def test_returns_empty_when_no_article_number(self):
        """Should return empty string when no article number is found."""
        html = "<html><head><title>No Article</title></head><body><p>Content</p></body></html>"
        url = "https://www.waters.com/generic-page.html"
        result = extract_article_information(html, url)
        assert result.article_number == ""


class TestTitleExtraction:
    """Tests for article title extraction."""

    def test_extracts_title_from_og_title(
        self, sample_article_html: str, sample_response_url: str
    ):
        """Title should be extracted from og:title meta tag."""
        result = extract_article_information(
            sample_article_html, sample_response_url
        )
        assert result.title == "How to Configure the ACQUITY UPLC System"

    def test_title_is_whitespace_normalized(self):
        """Title should have normalized whitespace."""
        html = """
        <html><head>
            <meta property="og:title" content="  Title   with   spaces  ">
        </head><body><p>Content here for testing</p></body></html>
        """
        result = extract_article_information(html, "https://example.com")
        assert result.title == "Title with spaces"


class TestCanonicalUrlExtraction:
    """Tests for canonical URL extraction."""

    def test_extracts_canonical_url_from_link_element(
        self, sample_article_html: str, sample_response_url: str
    ):
        """Canonical URL should be extracted from link[rel=canonical]."""
        result = extract_article_information(
            sample_article_html, sample_response_url
        )
        expected_url = "https://www.waters.com/nextgen/us/en/support/knowledge-base/WKB12345.html"
        assert result.canonical_url == expected_url

    def test_falls_back_to_response_url(self):
        """Should use response URL when no canonical link is present."""
        html = "<html><head><title>Test</title></head><body><p>Content</p></body></html>"
        url = "https://www.waters.com/test-page.html"
        result = extract_article_information(html, url)
        assert result.canonical_url == url


class TestDateExtraction:
    """Tests for source update date extraction."""

    def test_extracts_date_from_article_modified_time(
        self, sample_article_html: str, sample_response_url: str
    ):
        """Date should be extracted from article:modified_time meta tag."""
        result = extract_article_information(
            sample_article_html, sample_response_url
        )
        assert result.source_updated_at is not None
        assert result.source_updated_at.year == 2026
        assert result.source_updated_at.month == 3
        assert result.source_updated_at.day == 15

    def test_returns_none_when_no_date(self):
        """Should return None when no date is found."""
        html = "<html><head><title>No Date</title></head><body><p>Content</p></body></html>"
        result = extract_article_information(html, "https://example.com")
        assert result.source_updated_at is None
