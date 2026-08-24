"""
Instrument name extractor for Waters Knowledge Base articles.

Identifies instrument and software environment names from article
content by looking for recognized heading labels such as "Environment",
"Instruments", "Products", etc. Supports multiple value formats including
comma-separated lists, bulleted lists, and HTML list items.
"""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# CONFIGURATION: Recognized heading labels for instrument sections.
# These labels identify HTML sections or visible headings that contain
# instrument or software environment information.
# Add or remove labels here rather than scattering them through code.
# -----------------------------------------------------------------------
INSTRUMENT_SECTION_HEADING_LABELS: list[str] = [
    "environment",
    "environments",
    "instrument",
    "instruments",
    "product",
    "products",
    "system",
    "systems",
    "software",
    "platform",
    "platforms",
    "applicable products",
    "applicable systems",
    "applicable instruments",
    "related products",
    "related instruments",
]

# Characters/patterns used to split multi-value instrument fields
MULTI_VALUE_SEPARATORS: re.Pattern = re.compile(r"[;,]\s*|\s*\n\s*")


def extract_instrument_names(
    html_content: str,
    article_url: str = "",
) -> list[str]:
    """
    Extract instrument and software environment names from article HTML.

    Searches for recognized heading labels and extracts values from the
    content that follows those headings. Supports:
    - Text after heading elements (h2, h3, h4, strong, dt, th)
    - HTML list items (ul/ol > li)
    - Comma, semicolon, or newline-separated values
    - Table cells paired with heading cells

    Args:
        html_content: Raw HTML of the article page.
        article_url: URL for logging context.

    Returns:
        List of raw instrument name strings (not yet normalized).
    """
    soup = BeautifulSoup(html_content, "lxml")
    discovered_names: list[str] = []

    # Strategy 1: Look for heading elements followed by content
    discovered_names.extend(
        _extract_from_heading_elements(soup, article_url)
    )

    # Strategy 2: Look for definition lists (dt/dd pairs)
    discovered_names.extend(
        _extract_from_definition_lists(soup, article_url)
    )

    # Strategy 3: Look for table rows with label cells
    discovered_names.extend(
        _extract_from_table_rows(soup, article_url)
    )

    # Strategy 4: Look for labeled div/span patterns
    discovered_names.extend(
        _extract_from_labeled_elements(soup, article_url)
    )

    if not discovered_names:
        logger.debug(
            "No instrument names found in article %s", article_url
        )

    return discovered_names


def _matches_instrument_heading(text: str) -> bool:
    """Check if a text string matches one of the recognized heading labels."""
    if not text:
        return False
    cleaned_text = text.strip().rstrip(":").strip().lower()
    return cleaned_text in INSTRUMENT_SECTION_HEADING_LABELS


def _extract_from_heading_elements(
    soup: BeautifulSoup, article_url: str
) -> list[str]:
    """Extract instrument names from content following heading elements."""
    names: list[str] = []
    heading_tags = ["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"]

    for tag_name in heading_tags:
        for heading in soup.find_all(tag_name):
            heading_text = heading.get_text(strip=True)
            if not _matches_instrument_heading(heading_text):
                continue

            # Look at the next sibling elements for values
            sibling_values = _collect_values_from_siblings(heading)
            names.extend(sibling_values)

    return names


def _extract_from_definition_lists(
    soup: BeautifulSoup, article_url: str
) -> list[str]:
    """Extract instrument names from dt/dd definition list pairs."""
    names: list[str] = []

    for dt_element in soup.find_all("dt"):
        dt_text = dt_element.get_text(strip=True)
        if not _matches_instrument_heading(dt_text):
            continue

        # Collect all following dd elements until the next dt
        next_sibling = dt_element.find_next_sibling()
        while next_sibling and next_sibling.name == "dd":
            dd_text = next_sibling.get_text(strip=True)
            names.extend(_split_instrument_values(dd_text))
            next_sibling = next_sibling.find_next_sibling()

    return names


def _extract_from_table_rows(
    soup: BeautifulSoup, article_url: str
) -> list[str]:
    """Extract instrument names from table rows where the label cell matches."""
    names: list[str] = []

    for table_row in soup.find_all("tr"):
        cells = table_row.find_all(["th", "td"])
        if len(cells) < 2:
            continue

        label_cell = cells[0]
        label_text = label_cell.get_text(strip=True)

        if not _matches_instrument_heading(label_text):
            continue

        # Remaining cells contain the values
        for value_cell in cells[1:]:
            # Check for nested lists first
            list_items = value_cell.find_all("li")
            if list_items:
                for list_item in list_items:
                    item_text = list_item.get_text(strip=True)
                    if item_text:
                        names.append(item_text)
            else:
                cell_text = value_cell.get_text(strip=True)
                names.extend(_split_instrument_values(cell_text))

    return names


def _extract_from_labeled_elements(
    soup: BeautifulSoup, article_url: str
) -> list[str]:
    """Extract instrument names from div/span elements with label patterns."""
    names: list[str] = []

    # Look for elements with class names containing instrument-related terms
    label_class_patterns = [
        "environment",
        "instrument",
        "product",
        "applicable",
    ]

    for pattern in label_class_patterns:
        for element in soup.find_all(
            True,
            class_=lambda css_class: css_class
            and pattern in " ".join(css_class).lower()
            if css_class
            else False,
        ):
            # Check if this element has a label-value structure
            label_element = element.find(
                ["span", "strong", "b", "label"],
                string=lambda text: text
                and _matches_instrument_heading(text)
                if text
                else False,
            )

            if label_element:
                # Get text from the parent, excluding the label text
                full_text = element.get_text(strip=True)
                label_text = label_element.get_text(strip=True)
                value_text = full_text.replace(label_text, "", 1).strip()
                value_text = value_text.lstrip(":").strip()
                if value_text:
                    names.extend(_split_instrument_values(value_text))

    return names


def _collect_values_from_siblings(heading: Tag) -> list[str]:
    """
    Collect instrument values from elements following a heading.

    Looks at the next sibling elements (p, ul, ol, div, span, text)
    and extracts values until another heading or section boundary is found.
    """
    values: list[str] = []
    stop_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "hr", "section"}

    current_element: Optional[Tag] = heading

    # Check for immediate text content after the heading in its parent
    parent = heading.parent
    if parent:
        # If the heading and value are in the same parent container
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag):
                if sibling.name in stop_tags:
                    break

                # Check for list items
                if sibling.name in ("ul", "ol"):
                    for list_item in sibling.find_all("li"):
                        item_text = list_item.get_text(strip=True)
                        if item_text:
                            values.append(item_text)
                    break

                # Check for paragraph or div with text
                if sibling.name in ("p", "div", "span", "td"):
                    text = sibling.get_text(strip=True)
                    if text:
                        values.extend(_split_instrument_values(text))
                    break
            elif hasattr(sibling, "strip"):
                # Bare text node
                text = str(sibling).strip()
                if text:
                    # Remove leading colon if present
                    text = text.lstrip(":").strip()
                    if text:
                        values.extend(_split_instrument_values(text))
                        break

    # If heading is followed by a next sibling element at the same level
    if not values:
        next_element = heading.find_next_sibling()
        if next_element and isinstance(next_element, Tag):
            if next_element.name in ("ul", "ol"):
                for list_item in next_element.find_all("li"):
                    item_text = list_item.get_text(strip=True)
                    if item_text:
                        values.append(item_text)
            elif next_element.name not in stop_tags:
                text = next_element.get_text(strip=True)
                if text:
                    values.extend(_split_instrument_values(text))

    return values


def _split_instrument_values(text: str) -> list[str]:
    """
    Split a multi-value instrument string into individual names.

    Handles comma-separated, semicolon-separated, and newline-separated
    values. Does NOT split on hyphens or ordinary spaces.
    """
    if not text:
        return []

    # Split on recognized separators
    parts = MULTI_VALUE_SEPARATORS.split(text)

    # Clean each part
    cleaned_parts: list[str] = []
    for part in parts:
        cleaned_part = part.strip()
        # Remove list bullet characters
        cleaned_part = cleaned_part.lstrip("•·–-▪►◦∙").strip()
        if cleaned_part:
            cleaned_parts.append(cleaned_part)

    return cleaned_parts
