"""
Text helper utilities for the Waters Knowledge Base Loader.

Provides common text cleaning and normalization functions used by
multiple extraction and validation modules.
"""

import re
from urllib.parse import urljoin, urlparse, urlunparse


def normalize_whitespace(text: str) -> str:
    """
    Collapse all internal whitespace sequences to a single space
    and strip leading/trailing whitespace.

    Args:
        text: Raw text to normalize.

    Returns:
        Whitespace-normalized string.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def remove_empty_lines(text: str) -> str:
    """
    Remove completely empty lines while preserving meaningful line breaks.

    Args:
        text: Multi-line text.

    Returns:
        Text with empty lines removed.
    """
    lines = text.splitlines()
    non_empty_lines = [line for line in lines if line.strip()]
    return "\n".join(non_empty_lines)


def canonicalize_url(url: str, base_url: str = "") -> str:
    """
    Normalize a URL by resolving relative references, removing fragments,
    and ensuring consistent formatting.

    Args:
        url: The URL to canonicalize.
        base_url: Optional base URL for resolving relative URLs.

    Returns:
        Canonicalized absolute URL string.
    """
    if not url or not url.strip():
        return ""

    cleaned_url = url.strip()

    # Resolve relative URLs if a base is provided
    if base_url and not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = urljoin(base_url, cleaned_url)

    # Parse and remove fragments
    parsed = urlparse(cleaned_url)
    canonical = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/") if parsed.path != "/" else "/",
        parsed.params,
        parsed.query,
        "",  # Remove fragment
    ))

    return canonical


def is_article_url(url: str, allowed_domain: str = "waters.com") -> bool:
    """
    Check whether a URL appears to be a Waters Knowledge Base article.

    This function applies configurable rules to identify article URLs
    and reject navigation, login, search, and other non-article URLs.

    Args:
        url: The URL to check.
        allowed_domain: The authorized domain to restrict crawling to.

    Returns:
        True if the URL looks like a valid article URL.
    """
    if not url:
        return False

    parsed = urlparse(url)
    hostname = parsed.netloc.lower()

    # Must be on the allowed domain
    if allowed_domain not in hostname:
        return False

    path_lower = parsed.path.lower()

    # Reject known non-article URL patterns
    excluded_path_segments = [
        "/login",
        "/logout",
        "/account",
        "/search",
        "/special:search",
        "/cart",
        "/checkout",
        "/tracking",
        "/preferences",
        "/subscribe",
        "/unsubscribe",
        "/api/",
        "/assets/",
        "/static/",
        "/cdn-cgi/",
        "/wp-admin",
        "/wp-login",
    ]
    for excluded_segment in excluded_path_segments:
        if excluded_segment in path_lower:
            return False

    # Look for knowledge-base article indicators
    # These patterns should be adjusted based on actual Waters URL structure
    article_path_indicators = [
        "/support/knowledge-base/",
        "/knowledgebase/",
        "/kb/",
        "/nextgen/",
        "/articles/",
        "article",
        "wkb",  # Common prefix for Waters KB articles (e.g. WKB12345)
        "/kb_inst/",
        "/kb_inf/",
        "/kb_chem/",
        "/select/",
        "/kits/",
    ]

    for indicator in article_path_indicators:
        if indicator in path_lower:
            return True

    # If the URL is on the allowed domain but doesn't match known patterns,
    # it might still be an article — return True conservatively for the
    # allowed domain, but log it for review
    return False


def truncate_for_logging(text: str, maximum_length: int = 200) -> str:
    """
    Truncate a text string for safe inclusion in log messages.

    Args:
        text: The text to truncate.
        maximum_length: Maximum character length.

    Returns:
        Truncated string with ellipsis if it was shortened.
    """
    if not text:
        return ""
    if len(text) <= maximum_length:
        return text
    return text[:maximum_length] + "..."


def mask_database_credentials(connection_url: str) -> str:
    """
    Mask the password in a PostgreSQL connection URL for safe logging.

    Args:
        connection_url: A PostgreSQL connection string.

    Returns:
        Connection URL with password replaced by '***'.
    """
    if not connection_url:
        return ""

    # Match postgresql://user:password@host pattern
    masked = re.sub(
        r"(postgresql(?:\+\w+)?://[^:]+:)([^@]+)(@)",
        r"\1***\3",
        connection_url,
    )
    return masked
