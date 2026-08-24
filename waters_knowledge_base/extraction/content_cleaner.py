"""
Article content cleaner for Waters Knowledge Base pages.

Removes non-content elements (scripts, styles, navigation, headers,
footers, cookie banners, forms) and normalizes the remaining article
text for clean storage and search indexing.
"""

import re

from bs4 import BeautifulSoup, Comment, NavigableString, Tag


# HTML tags that never contain article content
TAGS_TO_REMOVE: list[str] = [
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "video",
    "audio",
    "source",
    "track",
    "map",
    "area",
]

# HTML elements with these roles, classes, or IDs are navigation/chrome
# and should be removed before content extraction.
# These patterns are intentionally broad to cover common CMS structures.
BOILERPLATE_CSS_SELECTORS: list[str] = [
    "header",
    "footer",
    "nav",
    "aside",
    "form",
    "[role='banner']",
    "[role='navigation']",
    "[role='contentinfo']",
    "[role='search']",
    "[role='complementary']",
    ".cookie-banner",
    ".cookie-notice",
    ".cookie-consent",
    "#cookie-banner",
    "#cookie-notice",
    ".site-header",
    ".site-footer",
    ".site-nav",
    ".global-header",
    ".global-footer",
    ".global-nav",
    ".main-nav",
    ".main-navigation",
    ".breadcrumb",
    ".breadcrumbs",
    ".elm-header",
    ".elm-footer",
    ".elm-nav",
    ".elm-meta-data",
    ".sidebar",
    ".side-nav",
    ".social-share",
    ".social-links",
    ".share-buttons",
    ".related-articles",
    ".related-content",
    ".newsletter-signup",
    ".subscribe-form",
    ".feedback-form",
    ".print-only",
    ".skip-link",
    ".skip-nav",
    ".back-to-top",
    ".pagination",
]

# Additional class/ID substrings that indicate boilerplate
BOILERPLATE_CLASS_PATTERNS: list[str] = [
    "cookie",
    "gdpr",
    "privacy-banner",
    "chat-widget",
    "live-chat",
    "popup",
    "modal-overlay",
    "tooltip",
    "mega-menu",
    "dropdown-menu",
    "mobile-menu",
    "hamburger",
]


def clean_article_content(
    html_content: str,
    article_url: str = "",
) -> str:
    """
    Extract and clean the main article text from raw HTML.

    Removes all non-content elements, normalizes whitespace, and
    preserves meaningful paragraph and section breaks.

    Args:
        html_content: Raw HTML string of the article page.
        article_url: URL of the article for logging context.

    Returns:
        Cleaned plain-text article content.
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove unwanted tags entirely
    for tag_name in TAGS_TO_REMOVE:
        for element in soup.find_all(tag_name):
            element.decompose()

    # Remove boilerplate elements by CSS selector
    for selector in BOILERPLATE_CSS_SELECTORS:
        for element in soup.select(selector):
            element.decompose()

    # Remove elements with boilerplate class/ID patterns
    _remove_elements_with_boilerplate_patterns(soup)

    # Remove hidden elements
    _remove_hidden_elements(soup)

    # Try to find the main content area
    main_content = _find_main_content_area(soup)

    # Extract text with meaningful line breaks
    raw_text = _extract_text_with_line_breaks(main_content)

    # Normalize the text
    cleaned_text = _normalize_extracted_text(raw_text)

    return cleaned_text


def _remove_elements_with_boilerplate_patterns(soup: BeautifulSoup) -> None:
    """Remove elements whose class or ID matches boilerplate patterns."""
    for element in soup.find_all(True):
        if not isinstance(element, Tag) or not element.attrs:
            continue

        element_classes = " ".join(element.get("class", []))
        element_id = element.get("id", "") or ""
        combined_identifiers = f"{element_classes} {element_id}".lower()

        for pattern in BOILERPLATE_CLASS_PATTERNS:
            if pattern in combined_identifiers:
                element.decompose()
                break


def _remove_hidden_elements(soup: BeautifulSoup) -> None:
    """Remove elements that are explicitly hidden via inline styles."""
    for element in soup.find_all(True):
        if not isinstance(element, Tag) or not element.attrs:
            continue
        style = element.get("style", "")
        if style and isinstance(style, str):
            style_lower = style.lower().replace(" ", "")
            if "display:none" in style_lower or "visibility:hidden" in style_lower:
                element.decompose()


def _find_main_content_area(soup: BeautifulSoup) -> Tag | BeautifulSoup:
    """
    Attempt to locate the main content area of the page.

    Tries semantic HTML5 elements first, then falls back to common
    content container patterns.
    """
    # Try semantic main element
    main_element = soup.find("main")
    if main_element and _has_meaningful_text(main_element):
        return main_element

    # Try article element
    article_element = soup.find("article")
    if article_element and _has_meaningful_text(article_element):
        return article_element

    # Try role="main"
    main_role = soup.find(attrs={"role": "main"})
    if main_role and _has_meaningful_text(main_role):
        return main_role

    # Try common content container IDs and classes
    content_identifiers = [
        "content",
        "main-content",
        "article-content",
        "article-body",
        "page-content",
        "entry-content",
        "post-content",
        "kb-article",
        "knowledge-base-content",
        "mt-content-container",
        "elm-content-container",
    ]

    for identifier in content_identifiers:
        by_id = soup.find(id=identifier)
        if by_id and _has_meaningful_text(by_id):
            return by_id

        by_class = soup.find(class_=identifier)
        if by_class and _has_meaningful_text(by_class):
            return by_class

    # Fall back to body
    body = soup.find("body")
    if body:
        return body

    return soup


def _has_meaningful_text(element: Tag, minimum_length: int = 100) -> bool:
    """Check whether an element contains enough text to be the main content."""
    text = element.get_text(separator=" ", strip=True)
    return len(text) >= minimum_length


def _extract_text_with_line_breaks(element: Tag | BeautifulSoup) -> str:
    """
    Extract text from an element tree, preserving meaningful line breaks
    at paragraph, heading, and list boundaries.
    """
    text_parts: list[str] = []

    # Block-level elements that should produce line breaks
    block_tags = {
        "p", "div", "section", "article", "main",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "li", "dt", "dd",
        "blockquote", "pre", "figure", "figcaption",
        "tr", "th", "td",
        "br",
    }

    for child in element.descendants:
        if isinstance(child, NavigableString):
            text = str(child)
            if text.strip():
                text_parts.append(text)
        elif isinstance(child, Tag):
            if child.name in block_tags:
                text_parts.append("\n")
            if child.name == "br":
                text_parts.append("\n")

    return "".join(text_parts)


def _normalize_extracted_text(raw_text: str) -> str:
    """
    Normalize extracted text by collapsing excessive whitespace and
    blank lines while preserving paragraph structure.
    """
    # Replace tabs with spaces
    text = raw_text.replace("\t", " ")

    # Normalize spaces within lines (but not newlines)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip each line
    lines = text.splitlines()
    stripped_lines = [line.strip() for line in lines]

    # Remove leading and trailing empty lines
    while stripped_lines and not stripped_lines[0]:
        stripped_lines.pop(0)
    while stripped_lines and not stripped_lines[-1]:
        stripped_lines.pop()

    return "\n".join(stripped_lines)
