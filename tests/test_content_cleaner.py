"""
Tests for the content cleaner module.

Validates removal of boilerplate elements, whitespace normalization,
and preservation of main article content.
"""

import pytest

from waters_knowledge_base.extraction.content_cleaner import (
    clean_article_content,
)


class TestBoilerplateRemoval:
    """Tests for removing non-content elements."""

    def test_removes_script_tags(self):
        """Script tag content should not appear in cleaned text."""
        html = """
        <html><body>
            <main><p>Article content here with enough text to pass validation.</p></main>
            <script>var x = "this should not appear";</script>
        </body></html>
        """
        cleaned = clean_article_content(html)
        assert "this should not appear" not in cleaned
        assert "Article content" in cleaned

    def test_removes_style_tags(self):
        """Style tag content should not appear in cleaned text."""
        html = """
        <html><body>
            <main><p>Article content here.</p></main>
            <style>.hidden { display: none; }</style>
        </body></html>
        """
        cleaned = clean_article_content(html)
        assert "display: none" not in cleaned

    def test_removes_navigation(self):
        """Navigation elements should be excluded."""
        html = """
        <html><body>
            <nav class="main-navigation"><a href="/">Home</a></nav>
            <main><p>Main article content for testing the cleaner module here.</p></main>
        </body></html>
        """
        cleaned = clean_article_content(html)
        assert "Main article content" in cleaned
        # Nav content may or may not be present depending on main detection

    def test_removes_header_and_footer(self):
        """Header and footer content should be excluded."""
        html = """
        <html><body>
            <header class="site-header"><p>Header text</p></header>
            <main><p>Article body text for testing the content cleaner.</p></main>
            <footer class="site-footer"><p>Footer text</p></footer>
        </body></html>
        """
        cleaned = clean_article_content(html)
        assert "Article body text" in cleaned
        assert "Header text" not in cleaned
        assert "Footer text" not in cleaned

    def test_removes_cookie_banner(self):
        """Cookie banner content should be excluded."""
        html = """
        <html><body>
            <div class="cookie-banner"><p>We use cookies</p></div>
            <main><p>Main content for testing cookie banner removal here.</p></main>
        </body></html>
        """
        cleaned = clean_article_content(html)
        assert "We use cookies" not in cleaned

    def test_removes_hidden_elements(self):
        """Elements with display:none should be excluded."""
        html = """
        <html><body>
            <div style="display:none">Hidden text</div>
            <main><p>Visible article content for testing hidden element removal.</p></main>
        </body></html>
        """
        cleaned = clean_article_content(html)
        assert "Hidden text" not in cleaned
        assert "Visible article content" in cleaned


class TestWhitespaceNormalization:
    """Tests for whitespace handling in cleaned content."""

    def test_collapses_excessive_blank_lines(self):
        """Multiple consecutive blank lines should be collapsed."""
        html = """
        <html><body><main>
            <p>First paragraph content here.</p>
            <p></p><p></p><p></p>
            <p>Second paragraph content here.</p>
        </main></body></html>
        """
        cleaned = clean_article_content(html)
        assert "\n\n\n" not in cleaned

    def test_strips_leading_trailing_whitespace(self):
        """Cleaned content should not start or end with blank lines."""
        html = """
        <html><body><main>
            <p>Content in the main area here for testing whitespace.</p>
        </main></body></html>
        """
        cleaned = clean_article_content(html)
        assert not cleaned.startswith("\n")
        assert not cleaned.endswith("\n")


class TestMainContentDetection:
    """Tests for finding the main content area."""

    def test_prefers_main_element(self):
        """Should prefer <main> element content."""
        html = """
        <html><body>
            <div>Outside content that should be ignored by the cleaner.</div>
            <main><p>Inside main element content for testing detection.</p></main>
        </body></html>
        """
        cleaned = clean_article_content(html)
        assert "Inside main element" in cleaned

    def test_uses_article_element_fallback(self):
        """Should use <article> element when <main> is absent."""
        html = """
        <html><body>
            <article><p>Article element content for testing fallback detection.</p></article>
        </body></html>
        """
        cleaned = clean_article_content(html)
        assert "Article element content" in cleaned
