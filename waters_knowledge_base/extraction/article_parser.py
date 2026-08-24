"""
Article parser for Waters Knowledge Base pages.

Extracts article number, title, canonical URL, searchable content,
source update date, and instrument names from downloaded HTML pages.
Uses a layered extraction strategy: semantic HTML first, then headings
and labels, then CSS selectors, then configurable fallbacks.
"""

import logging
import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from waters_knowledge_base.extraction.content_cleaner import clean_article_content
from waters_knowledge_base.extraction.instrument_extractor import extract_instrument_names
from waters_knowledge_base.utilities.date_parsing import parse_article_date
from waters_knowledge_base.utilities.text_helpers import normalize_whitespace

logger = logging.getLogger(__name__)

# Configurable regex for extracting WKB article numbers, WAT numbers, or part numbers
ARTICLE_NUMBER_REGEX_STRICT: re.Pattern = re.compile(r"((?:WKB|WAT)\d+)", re.IGNORECASE)
ARTICLE_NUMBER_REGEX_BARE: re.Pattern = re.compile(r"\b(\d{7,})\b")

# CSS selectors for finding article number (tried in order)
ARTICLE_NUMBER_SELECTORS: list[str] = [
    "meta[name='article-number']",
    "meta[name='articleNumber']",
    "meta[name='article_number']",
    ".article-number",
    ".article-id",
    "#article-number",
    "[data-article-number]",
    "[data-article-id]",
]

# CSS selectors for finding the title (tried in order)
TITLE_SELECTORS: list[str] = [
    "meta[property='og:title']",
    "meta[name='title']",
    "h1.article-title",
    "h1.page-title",
    "h1",
]

# CSS selectors for finding the source update date
DATE_SELECTORS: list[str] = [
    "meta[property='article:modified_time']",
    "meta[property='article:published_time']",
    "meta[name='last-modified']",
    "meta[name='date']",
    "meta[name='dcterms.modified']",
    "time[datetime]",
    ".article-date",
    ".last-updated",
    ".modified-date",
    ".publish-date",
]


class ExtractionResult:
    """Container for the result of extracting data from one article page."""

    def __init__(self):
        self.article_number: str = ""
        self.title: str = ""
        self.canonical_url: str = ""
        self.searchable_content: str = ""
        self.source_updated_at: Optional[Any] = None
        self.raw_instrument_names: list[str] = []
        self.extraction_warnings: list[str] = []


def extract_article_information(
    html_content: str,
    response_url: str,
) -> ExtractionResult:
    """
    Extract all article fields from a downloaded HTML page.

    Args:
        html_content: Raw HTML string of the article page.
        response_url: The URL the HTML was downloaded from.

    Returns:
        ExtractionResult with all extracted fields and any warnings.
    """
    result = ExtractionResult()
    soup = BeautifulSoup(html_content, "lxml")

    # Extract each field using layered strategies
    result.article_number = _extract_article_number(soup, response_url, result)
    result.title = _extract_title(soup, response_url, result)
    result.canonical_url = _extract_canonical_url(soup, response_url)
    result.searchable_content = clean_article_content(html_content, response_url)
    result.source_updated_at = _extract_source_date(soup, response_url, result)
    result.raw_instrument_names = extract_instrument_names(html_content, response_url)

    return result


def _extract_article_number(
    soup: BeautifulSoup, response_url: str, result: ExtractionResult
) -> str:
    """Extract the article number using layered strategies."""
    
    # PASS 1: Look for explicit WKB or WAT prefix identifiers
    
    # URL path
    match = ARTICLE_NUMBER_REGEX_STRICT.search(response_url)
    if match: return match.group(1).upper()
        
    # Page title
    title_tag = soup.find("title")
    if title_tag:
        match = ARTICLE_NUMBER_REGEX_STRICT.search(title_tag.get_text())
        if match: return match.group(1).upper()

    # Structured metadata
    for selector in ARTICLE_NUMBER_SELECTORS:
        element = soup.select_one(selector)
        if element:
            value = element.get("content", "") or element.get_text(strip=True)
            if isinstance(value, list): value = value[0] if value else ""
            match = ARTICLE_NUMBER_REGEX_STRICT.search(str(value))
            if match: return match.group(1).upper()

    # Full page text scan
    match = ARTICLE_NUMBER_REGEX_STRICT.search(soup.get_text())
    if match:
        result.extraction_warnings.append("Article number extracted from page body text (last-resort fallback).")
        return match.group(1).upper()
        
    # PASS 2: Look for bare numbers with > 6 digits (e.g. Kits / Parts)
    
    # URL path
    match = ARTICLE_NUMBER_REGEX_BARE.search(response_url)
    if match:
        result.extraction_warnings.append("Article number extracted from bare number in URL.")
        return match.group(1)
        
    # Page title
    if title_tag:
        match = ARTICLE_NUMBER_REGEX_BARE.search(title_tag.get_text())
        if match:
            result.extraction_warnings.append("Article number extracted from bare number in title.")
            return match.group(1)

    return ""


def _extract_title(
    soup: BeautifulSoup, response_url: str, result: ExtractionResult
) -> str:
    """Extract the article title."""
    for selector in TITLE_SELECTORS:
        element = soup.select_one(selector)
        if element:
            if element.name == "meta":
                content = element.get("content", "")
                if content:
                    return normalize_whitespace(str(content))
            else:
                text = element.get_text(strip=True)
                if text:
                    return normalize_whitespace(text)

    # Fallback: HTML <title> tag, cleaned of site boilerplate
    title_tag = soup.find("title")
    if title_tag:
        raw_title = title_tag.get_text(strip=True)
        # Remove common suffixes like " | Waters" or " - Waters Corporation"
        cleaned = re.sub(r"\s*[|–-]\s*Waters.*$", "", raw_title, flags=re.IGNORECASE)
        if cleaned.strip():
            result.extraction_warnings.append("Title from <title> tag (fallback).")
            return normalize_whitespace(cleaned)

    return ""


def _extract_canonical_url(soup: BeautifulSoup, response_url: str) -> str:
    """Extract the canonical URL."""
    canonical_link = soup.find("link", rel="canonical")
    if canonical_link and canonical_link.get("href"):
        return str(canonical_link["href"]).strip()

    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        return str(og_url["content"]).strip()

    return response_url


def _extract_source_date(
    soup: BeautifulSoup, response_url: str, result: ExtractionResult
) -> Optional[Any]:
    """Extract the source update date."""
    for selector in DATE_SELECTORS:
        element = soup.select_one(selector)
        if element:
            if element.name == "meta":
                date_str = element.get("content", "")
            elif element.name == "time":
                date_str = element.get("datetime", "") or element.get_text(strip=True)
            else:
                date_str = element.get_text(strip=True)

            if date_str:
                parsed = parse_article_date(str(date_str), response_url)
                if parsed:
                    return parsed

    # Don't substitute the current date for missing source dates
    return None
