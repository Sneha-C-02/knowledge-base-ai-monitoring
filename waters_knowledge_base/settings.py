"""
Scrapy settings for the Waters Knowledge Base Loader.

Reads configuration from environment variables (loaded by python-dotenv)
and applies safe, conservative defaults for responsible crawling.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# -----------------------------------------------------------------------
# Scrapy core settings
# -----------------------------------------------------------------------
BOT_NAME = "waters_knowledge_base"
SPIDER_MODULES = ["waters_knowledge_base.spiders"]
NEWSPIDER_MODULE = "waters_knowledge_base.spiders"

# -----------------------------------------------------------------------
# Responsible crawling settings
# -----------------------------------------------------------------------
ROBOTSTXT_OBEY = os.environ.get("RESPECT_ROBOTS_TXT", "true").lower() == "true"

USER_AGENT = os.environ.get(
    "USER_AGENT_NAME", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Concurrent requests — conservative by default (limited to 1 to save memory)
CONCURRENT_REQUESTS = int(
    os.environ.get("MAXIMUM_CONCURRENT_REQUESTS", "25")
)
CONCURRENT_REQUESTS_PER_DOMAIN = CONCURRENT_REQUESTS

# Download delay between requests
DOWNLOAD_DELAY = float(os.environ.get("CRAWL_DELAY_SECONDS", "0.2"))
RANDOMIZE_DOWNLOAD_DELAY = False

# Request timeout
DOWNLOAD_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30"))

# Maximum response size (10 MB safety limit)
DOWNLOAD_MAXSIZE = 100 * 1024 * 1024
DOWNLOAD_WARNSIZE = 75 * 1024 * 1024

# -----------------------------------------------------------------------
# AutoThrottle (adaptive request throttling)
# -----------------------------------------------------------------------
AUTOTHROTTLE_ENABLED = False
AUTOTHROTTLE_DEBUG = False

# -----------------------------------------------------------------------
# Retry settings
# -----------------------------------------------------------------------
RETRY_ENABLED = True
RETRY_TIMES = int(os.environ.get("MAXIMUM_RETRY_ATTEMPTS", "3"))
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

# -----------------------------------------------------------------------
# HTTP caching (for development — disable in production)
# -----------------------------------------------------------------------
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = ".scrapy/httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [401, 403, 429, 500, 502, 503, 504]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# -----------------------------------------------------------------------
# Cookie and redirect handling
# -----------------------------------------------------------------------
COOKIES_ENABLED = False
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5

# -----------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# -----------------------------------------------------------------------
# Item pipelines
# -----------------------------------------------------------------------
ITEM_PIPELINES = {
    "waters_knowledge_base.pipelines.ArticleProcessingPipeline": 300,
}

# -----------------------------------------------------------------------
# Downloader middlewares
# -----------------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
    "waters_knowledge_base.middlewares.RateLimitingMiddleware": 543,
    "waters_knowledge_base.middlewares.RetryAfterMiddleware": 550,
}

# -----------------------------------------------------------------------
# Twisted reactor (required for modern Scrapy)
# -----------------------------------------------------------------------
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"

# -----------------------------------------------------------------------
# Playwright settings
# -----------------------------------------------------------------------
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,
    "args": [
        "--disable-http2",
        "--disable-blink-features=AutomationControlled",
    ],
}
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "java_script_enabled": True,
        "bypass_csp": True,
        "ignore_https_errors": True,
    }
}
PLAYWRIGHT_MAX_CONTEXTS = 1
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = CONCURRENT_REQUESTS

# -----------------------------------------------------------------------
# Security: Do not use stealth or circumvention features
# -----------------------------------------------------------------------
# No proxy rotation
# No user-agent rotation
# No CAPTCHA bypass
# No stealth plugins
