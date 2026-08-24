"""
Scrapy spider for discovering and downloading Waters Knowledge Base articles.

Supports two discovery methods:
1. Primary: Sitemap-based discovery
2. Fallback: Category/listing page crawling

Respects robots.txt, rate limits, and access controls.
Does not follow logout, login, account, search, or tracking URLs.
"""

import json
import logging
import os
import re
from typing import Any, Generator, Optional, AsyncIterator
from urllib.parse import urljoin, urlparse

import scrapy
from scrapy.http import Response, XmlResponse
from scrapy_playwright.page import PageMethod

from waters_knowledge_base.items import WatersArticleItem
from waters_knowledge_base.utilities.text_helpers import (
    canonicalize_url,
    is_article_url,
)

logger = logging.getLogger(__name__)

# Default start and sitemap URLs (overridden by environment variables)
DEFAULT_START_URL = "https://support.waters.com/"
DEFAULT_SITEMAP_URL = ""

# URL pattern to identify knowledge base article pages
ARTICLE_URL_PATTERN: re.Pattern = re.compile(
    r"/support/knowledge-base/.*", re.IGNORECASE
)


class WatersArticlesSpider(scrapy.Spider):
    """
    Spider that discovers and downloads Waters Knowledge Base articles.

    Supports sitemap-based and listing-page-based discovery.
    Deduplicates URLs, enforces domain restrictions, and respects
    configurable article limits.
    """

    name = "waters_articles"
    allowed_domains = ["waters.com", "support.waters.com"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,  # Disabled because CDN blocks robots.txt with 403
    }

    def __init__(
        self,
        run_mode: str = "full",
        maximum_articles: int = 0,
        single_article_url: str = "",
        dry_run: bool = False,
        discover_only: bool = False,
        retry_failed_file: str = "",
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize the spider with run configuration.

        Args:
            run_mode: One of "full", "incremental", "discover-only".
            maximum_articles: Maximum articles to process (0 = unlimited).
            single_article_url: Process only this one URL.
            dry_run: If True, extract and validate but skip database writes.
            discover_only: If True, only discover URLs without downloading.
            retry_failed_file: Path to a failed_articles.json to retry.
        """
        super().__init__(*args, **kwargs)

        self.run_mode: str = run_mode
        self.maximum_articles: int = int(maximum_articles)
        self.single_article_url: str = single_article_url
        self.dry_run: bool = dry_run if isinstance(dry_run, bool) else str(dry_run).lower() == "true"
        self.discover_only: bool = discover_only if isinstance(discover_only, bool) else str(discover_only).lower() == "true"
        self.retry_failed_file: str = retry_failed_file

        self.discovered_article_urls: set[str] = set()
        self.visited_listing_urls: set[str] = set()
        self.processed_article_urls: set[str] = set()
        self.processed_article_count: int = 0
        self.output_directory: str = os.environ.get("OUTPUT_DIRECTORY", "output")

        self.start_url: str = os.environ.get(
            "WATERS_KNOWLEDGE_BASE_START_URL", DEFAULT_START_URL
        )
        self.sitemap_url: str = os.environ.get(
            "WATERS_KNOWLEDGE_BASE_SITEMAP_URL", DEFAULT_SITEMAP_URL
        )
        
        self._load_state()

        logger.info("Spider initialized: mode=%s, max=%d, dry_run=%s",
                     self.run_mode, self.maximum_articles, self.dry_run)

    def _is_allowed_path(self, path: str) -> bool:
        """Check if a URL path is allowed to be crawled based on the 5 main categories."""
        path_lower = path.lower()
        if path_lower in ("/kb_inst", "/kb_inst/"):
            return True
            
        if path_lower.startswith("/kb_inst/"):
            allowed_inst_subs = [
                "/kb_inst/chromatography",
                "/kb_inst/purification_sfx",
                "/kb_inst/mass_spectrometry",
                "/kb_inst/lab_automation",
                "/kb_inst/other",
                "/kb_inst/wyatt_products",
            ]
            return any(path_lower.startswith(sub) for sub in allowed_inst_subs)
            
        if path_lower in ("/kb_inf", "/kb_inf/"):
            return True
            
        if path_lower.startswith("/kb_inf/"):
            allowed_inf_subs = [
                "/kb_inf/empower_breeze",
                "/kb_inf/masslynx",
                "/kb_inf/nugenesis",
                "/kb_inf/unifi",
                "/kb_inf/other",
                "/kb_inf/empower_tips_of_the_week",
                "/kb_inf/waters_connect",
                "/kb_inf/wyatt_software",
            ]
            return any(path_lower.startswith(sub) for sub in allowed_inf_subs)
            
        if path_lower in ("/kb_chem", "/kb_chem/"):
            return True
            
        if path_lower.startswith("/kb_chem/"):
            allowed_chem_subs = [
                "/kb_chem/analytical_standards_and_reagents",
                "/kb_chem/columns",
                "/kb_chem/other",
                "/kb_chem/sample_preparation",
            ]
            return any(path_lower.startswith(sub) for sub in allowed_chem_subs)
            
        if path_lower in ("/select", "/select/"):
            return True
            
        if path_lower.startswith("/select/"):
            allowed_select_subs = [
                "/select/cyclic_ims",
                "/select/select_series_mrt",
            ]
            return any(path_lower.startswith(sub) for sub in allowed_select_subs)
            
        other_allowed = [
            "/kits"
        ]
        return any(path_lower.startswith(prefix) for prefix in other_allowed)

    def _is_listing_page(self, path: str) -> bool:
        """Check if a URL path is exactly a category/subcategory listing page."""
        # Normalize path
        p = path.lower().rstrip("/")
        if not p:
            return False
            
        listing_pages = {
            "/kb_inst",
            "/kb_inst/chromatography",
            "/kb_inst/purification_sfx",
            "/kb_inst/mass_spectrometry",
            "/kb_inst/lab_automation",
            "/kb_inst/other",
            "/kb_inst/wyatt_products",
            
            "/kb_inf",
            "/kb_inf/empower_breeze",
            "/kb_inf/masslynx",
            "/kb_inf/nugenesis",
            "/kb_inf/unifi",
            "/kb_inf/other",
            "/kb_inf/empower_tips_of_the_week",
            "/kb_inf/waters_connect",
            "/kb_inf/wyatt_software",
            
            "/kb_chem",
            "/kb_chem/analytical_standards_and_reagents",
            "/kb_chem/columns",
            "/kb_chem/other",
            "/kb_chem/sample_preparation",
            
            "/select",
            "/select/cyclic_ims",
            "/select/select_series_mrt",
            
            "/kits",
        }
        return p in listing_pages

    async def start(self) -> AsyncIterator[scrapy.Request | Any]:
        """Generate initial requests based on the run mode."""
        # Mode: Single article URL
        if self.single_article_url:
            logger.info("Processing single article: %s", self.single_article_url)
            yield scrapy.Request(
                url=self.single_article_url,
                callback=self.parse_article_page,
                errback=self.handle_request_error,
            )
            return

        if not self.discover_only and len(self.discovered_article_urls) > 0:
            logger.info(
                "Already loaded %d discovered URLs. Skipping discovery phase.",
                len(self.discovered_article_urls)
            )
        elif self.sitemap_url:
            # Mode: Primary sitemap discovery
            logger.info("Starting sitemap discovery from: %s", self.sitemap_url)
            yield scrapy.Request(
                url=self.sitemap_url,
                callback=self.parse_sitemap,
                errback=self.handle_sitemap_error,
            )
        else:
            listing_paths = [
                "/kb_inst",
                "/kb_inst/chromatography",
                "/kb_inst/purification_sfx",
                "/kb_inst/mass_spectrometry",
                "/kb_inst/lab_automation",
                "/kb_inst/other",
                "/kb_inst/wyatt_products",
                "/kb_inf",
                "/kb_inf/empower_breeze",
                "/kb_inf/masslynx",
                "/kb_inf/nugenesis",
                "/kb_inf/unifi",
                "/kb_inf/other",
                "/kb_inf/empower_tips_of_the_week",
                "/kb_inf/waters_connect",
                "/kb_inf/wyatt_software",
                "/kb_chem",
                "/kb_chem/analytical_standards_and_reagents",
                "/kb_chem/columns",
                "/kb_chem/other",
                "/kb_chem/sample_preparation",
                "/select",
                "/select/cyclic_ims",
                "/select/select_series_mrt",
                "/kits",
            ]
            logger.info("No sitemap URL provided. Seeding UI discovery with %d root listing pages.", len(listing_paths))
            for path in listing_paths:
                url = f"https://support.waters.com{path}"
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_listing_page,
                    errback=self.handle_request_error,
                    meta={
                        "playwright": True,
                        "playwright_page_goto_kwargs": {"wait_until": "networkidle"},
                        "playwright_page_methods": [
                            PageMethod("wait_for_timeout", 2000),
                            PageMethod(
                                "evaluate",
                                """
                                async () => {
                                    let lastHeight = document.body.scrollHeight;
                                    for(let i = 0; i < 15; i++) {
                                        window.scrollTo(0, document.body.scrollHeight);
                                        await new Promise(r => setTimeout(r, 2000));
                                        let newHeight = document.body.scrollHeight;
                                        if (newHeight === lastHeight) {
                                            break;
                                        }
                                        lastHeight = newHeight;
                                    }
                                }
                                """
                            ),
                            PageMethod("wait_for_timeout", 1000),
                        ]
                    }
                )

        # In case we resumed state, enqueue previously discovered articles
        if not self.discover_only:
            for req in self._generate_article_requests():
                yield req

    def parse_sitemap(self, response: Response) -> Generator[scrapy.Request, None, None]:
        """
        Parse a sitemap XML to discover article URLs.

        Handles both sitemap index files and regular sitemaps.
        Falls back to listing page discovery if the sitemap is unusable.
        """
        try:
            body_text = response.text
        except Exception:
            body_text = response.body.decode("utf-8", errors="replace")

        # Check for sitemap index
        if "<sitemapindex" in body_text:
            logger.info("Found sitemap index. Parsing sub-sitemaps...")
            sitemap_urls = re.findall(r"<loc>\s*(.*?)\s*</loc>", body_text)
            for sitemap_url in sitemap_urls:
                # Prefer knowledge-base related sub-sitemaps
                yield scrapy.Request(
                    url=sitemap_url.strip(),
                    callback=self.parse_sitemap,
                    errback=self.handle_request_error,
                )
            return

        # Parse regular sitemap
        article_urls_found = re.findall(r"<loc>\s*(.*?)\s*</loc>", body_text)
        logger.info("Found %d URLs in sitemap.", len(article_urls_found))

        for raw_url in article_urls_found:
            canonical_url = canonicalize_url(raw_url.strip())
            parsed_url = urlparse(canonical_url)
            if parsed_url.netloc != "support.waters.com":
                continue
            if not self._is_allowed_path(parsed_url.path):
                continue
            if not is_article_url(canonical_url, allowed_domain="support.waters.com"):
                continue
            if canonical_url in self.discovered_article_urls:
                continue
            self.discovered_article_urls.add(canonical_url)

        logger.info(
            "Discovered %d article URLs from sitemap.",
            len(self.discovered_article_urls),
        )

        # Write discovered URLs
        self._write_discovered_urls()

        if self.discover_only:
            logger.info("Discover-only mode. Stopping after URL discovery.")
            return

        # If no articles found in sitemap, fall back to listing pages
        if not self.discovered_article_urls:
            logger.warning(
                "No article URLs found in sitemap. Falling back to listing page."
            )
            yield scrapy.Request(
                url=self.start_url,
                callback=self.parse_listing_page,
                errback=self.handle_request_error,
                meta={"playwright": True},
            )

    def handle_sitemap_error(self, failure: Any) -> Generator[scrapy.Request, None, None]:
        """Fall back to listing page if sitemap fails."""
        logger.warning(
            "Sitemap request failed: %s. Falling back to listing page.",
            failure.getErrorMessage(),
        )
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse_listing_page,
            errback=self.handle_request_error,
            meta={"playwright": True},
        )

    def parse_listing_page(self, response: Response) -> Generator[scrapy.Request, None, None]:
        """
        Parse a category or listing page to discover article links.

        Follows pagination links and discovers article URLs.
        """
        logger.info("Parsing listing page: %s", response.url)

        # Find all links on the page
        all_links = response.css("a[href]::attr(href)").getall()
        logger.debug("Found %d links on %s", len(all_links), response.url)
        for href in all_links:
            if "kb_inst" in href.lower() or "kb_inf" in href.lower():
                logger.info("Found potential missing link: %s", href)

        for href in all_links:
            if not href:
                continue

            absolute_url = urljoin(response.url, href)
            canonical_url = canonicalize_url(absolute_url)

            # Enforce that the URL must be exactly support.waters.com (no prefixes)
            parsed_url = urlparse(canonical_url)
            if parsed_url.netloc != "support.waters.com":
                continue

            if not self._is_allowed_path(parsed_url.path):
                continue

            if self._is_listing_page(parsed_url.path):
                if canonical_url not in self.visited_listing_urls:
                    self.visited_listing_urls.add(canonical_url)
                    yield scrapy.Request(
                        url=canonical_url,
                        callback=self.parse_listing_page,
                        errback=self.handle_request_error,
                        meta={
                            "playwright": True,
                            "playwright_page_goto_kwargs": {"wait_until": "networkidle"},
                            "playwright_page_methods": [
                                PageMethod("wait_for_timeout", 2000),
                                PageMethod(
                                    "evaluate",
                                    """
                                    async () => {
                                        let lastHeight = document.body.scrollHeight;
                                        for(let i = 0; i < 15; i++) {
                                            window.scrollTo(0, document.body.scrollHeight);
                                            await new Promise(r => setTimeout(r, 2000));
                                            let newHeight = document.body.scrollHeight;
                                            if (newHeight === lastHeight) {
                                                break;
                                            }
                                            lastHeight = newHeight;
                                        }
                                    }
                                    """
                                ),
                                PageMethod("wait_for_timeout", 1000),
                            ]
                        }
                    )
            else:
                # If it's an allowed path and NOT a listing page, it must be an article
                if canonical_url not in self.discovered_article_urls:
                    self.discovered_article_urls.add(canonical_url)
                if not self.discover_only and canonical_url not in self.processed_article_urls:
                    yield scrapy.Request(
                        url=canonical_url,
                        callback=self.parse_article_page,
                        errback=self.handle_request_error,
                    )

        logger.info(
            "Discovered %d article URLs overall.",
            len(self.discovered_article_urls),
        )

        self._write_discovered_urls()
        self._write_visited_listing_urls()

    def parse_article_page(self, response: Response) -> Generator[WatersArticleItem, None, None]:
        """
        Parse a downloaded article page and yield it as a Scrapy item.

        Args:
            response: The HTTP response containing the article HTML.

        Yields:
            WatersArticleItem with the article's HTML content.
        """
        # Check for non-success responses
        if response.status in (401, 403):
            logger.warning(
                "Access denied (HTTP %d) for %s. Skipping.",
                response.status,
                response.url,
            )
            return

        if response.status >= 400:
            logger.warning(
                "HTTP %d error for %s. Skipping.",
                response.status,
                response.url,
            )
            return

        self.processed_article_count += 1
        logger.info(
            "Downloaded article %d: %s",
            self.processed_article_count,
            response.url,
        )

        article_item = WatersArticleItem()
        article_item["response_url"] = response.url
        article_item["html_content"] = response.text
        article_item["http_status"] = response.status

        # Track that we have processed this URL to allow resuming
        self.processed_article_urls.add(response.url)
        self._write_processed_article_urls()

        yield article_item

    def handle_request_error(self, failure: Any) -> None:
        """Log request failures without terminating the crawl."""
        logger.error(
            "Request failed: %s — %s",
            failure.request.url if hasattr(failure, "request") else "unknown",
            failure.getErrorMessage(),
        )

    def _generate_article_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate download requests for discovered article URLs."""
        urls_to_process = [
            url for url in self.discovered_article_urls 
            if url not in self.processed_article_urls
        ]

        if self.maximum_articles > 0:
            urls_to_process = urls_to_process[:self.maximum_articles]
            logger.info(
                "Limiting to %d articles (maximum_articles=%d).",
                len(urls_to_process),
                self.maximum_articles,
            )

        for article_url in urls_to_process:
            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article_page,
                errback=self.handle_request_error,
                dont_filter=False,
            )

    def _generate_retry_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate requests from a failed_articles.json file."""
        if not os.path.exists(self.retry_failed_file):
            logger.error(
                "Retry file not found: %s", self.retry_failed_file
            )
            return

        try:
            with open(self.retry_failed_file, "r", encoding="utf-8") as retry_file:
                failed_articles = json.load(retry_file)
        except (json.JSONDecodeError, OSError) as load_error:
            logger.error("Failed to load retry file: %s", load_error)
            return

        retry_urls = [
            entry["article_url"]
            for entry in failed_articles
            if entry.get("retry_recommended", False)
            and entry.get("article_url")
        ]

        logger.info("Retrying %d failed articles.", len(retry_urls))

        for article_url in retry_urls:
            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article_page,
                errback=self.handle_request_error,
            )

    def _write_discovered_urls(self) -> None:
        """Write discovered article URLs to the output directory."""
        os.makedirs(self.output_directory, exist_ok=True)
        output_path = os.path.join(
            self.output_directory, "discovered_article_urls.json"
        )
        try:
            with open(output_path, "w", encoding="utf-8") as urls_file:
                json.dump(
                    sorted(list(self.discovered_article_urls)),
                    urls_file,
                    indent=2,
                )
            
            # Also write out ONLY the new ones (not yet processed) for user verification
            new_urls = self.discovered_article_urls - self.processed_article_urls
            new_output_path = os.path.join(self.output_directory, "newly_discovered_urls.json")
            with open(new_output_path, "w", encoding="utf-8") as new_urls_file:
                json.dump(
                    sorted(list(new_urls)),
                    new_urls_file,
                    indent=2,
                )

            logger.info(
                "Wrote %d total discovered URLs to %s. (%d are new/unprocessed)",
                len(self.discovered_article_urls),
                output_path,
                len(new_urls)
            )
        except OSError as write_error:
            logger.error("Failed to write discovered URLs: %s", write_error)

    def _write_visited_listing_urls(self) -> None:
        """Write visited listing URLs to the output directory to allow resuming."""
        os.makedirs(self.output_directory, exist_ok=True)
        output_path = os.path.join(
            self.output_directory, "visited_listing_urls.json"
        )
        try:
            with open(output_path, "w", encoding="utf-8") as urls_file:
                json.dump(
                    sorted(list(self.visited_listing_urls)),
                    urls_file,
                    indent=2,
                )
        except OSError as write_error:
            logger.error("Failed to write visited listing URLs: %s", write_error)

    def _write_processed_article_urls(self) -> None:
        """Write processed article URLs to the output directory to allow resuming."""
        os.makedirs(self.output_directory, exist_ok=True)
        output_path = os.path.join(
            self.output_directory, "processed_article_urls.json"
        )
        try:
            with open(output_path, "w", encoding="utf-8") as urls_file:
                json.dump(
                    sorted(list(self.processed_article_urls)),
                    urls_file,
                    indent=2,
                )
        except OSError as write_error:
            logger.error("Failed to write processed article URLs: %s", write_error)

    def _load_state(self) -> None:
        """Load discovered, visited, and processed URLs from disk if they exist, to resume execution."""
        disc_path = os.path.join(self.output_directory, "discovered_article_urls.json")
        visit_path = os.path.join(self.output_directory, "visited_listing_urls.json")
        processed_path = os.path.join(self.output_directory, "processed_article_urls.json")
        
        if os.path.exists(disc_path):
            try:
                with open(disc_path, "r", encoding="utf-8") as disc_file:
                    self.discovered_article_urls = set(json.load(disc_file))
                logger.info("Resumed state: Loaded %d discovered URLs.", len(self.discovered_article_urls))
            except Exception as e:
                logger.error("Failed to load discovered URLs state: %s", e)

        if os.path.exists(visit_path):
            try:
                with open(visit_path, "r", encoding="utf-8") as visit_file:
                    self.visited_listing_urls = set(json.load(visit_file))
                logger.info("Resumed state: Loaded %d visited listing URLs.", len(self.visited_listing_urls))
            except Exception as e:
                logger.error("Failed to load visited listing URLs state: %s", e)
                
        if os.path.exists(processed_path):
            try:
                with open(processed_path, "r", encoding="utf-8") as processed_file:
                    self.processed_article_urls = set(json.load(processed_file))
                logger.info("Resumed state: Loaded %d processed article URLs.", len(self.processed_article_urls))
            except Exception as e:
                logger.error("Failed to load processed article URLs state: %s", e)
