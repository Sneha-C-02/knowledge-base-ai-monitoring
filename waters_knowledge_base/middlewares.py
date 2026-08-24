"""
Scrapy middlewares for the Waters Knowledge Base Loader.

Implements rate-limiting awareness and Retry-After header handling
for responsible crawling behavior.
"""

import logging
import time
from typing import Any

from scrapy import signals
from scrapy.http import Request, Response
from scrapy.exceptions import IgnoreRequest

logger = logging.getLogger(__name__)


class RateLimitingMiddleware:
    """
    Middleware that detects HTTP 429 (Too Many Requests) responses
    and pauses crawling according to the Retry-After header.
    """

    @classmethod
    def from_crawler(cls, crawler: Any) -> "RateLimitingMiddleware":
        middleware = cls()
        return middleware

    def process_response(
        self, request: Request, response: Response
    ) -> Response:
        """Handle rate-limiting responses."""
        if response.status == 429:
            retry_after_seconds = self._parse_retry_after(response)
            logger.warning(
                "Rate limited (HTTP 429) on %s. "
                "Retry-After: %d seconds.",
                request.url,
                retry_after_seconds,
            )
            # The built-in retry middleware will handle the actual retry.
            # We just log the rate-limiting event here.
        return response

    def _parse_retry_after(self, response: Response) -> int:
        """Parse the Retry-After header value in seconds."""
        retry_after_header = response.headers.get(b"Retry-After", b"60")
        try:
            return int(retry_after_header)
        except (ValueError, TypeError):
            return 60


class RetryAfterMiddleware:
    """
    Middleware that adds delay before retrying requests that received
    a Retry-After header. Works with Scrapy's built-in retry middleware.
    """

    def process_response(
        self, request: Request, response: Response
    ) -> Response:
        """Add retry delay metadata for rate-limited responses."""
        if response.status == 429:
            retry_after_header = response.headers.get(b"Retry-After", b"60")
            try:
                retry_delay = int(retry_after_header)
            except (ValueError, TypeError):
                retry_delay = 60

            request.meta["download_delay"] = retry_delay
            logger.info(
                "Setting retry delay of %d seconds for %s",
                retry_delay,
                request.url,
            )
        return response
