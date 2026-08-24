"""
Scrapy item definitions for Waters Knowledge Base articles.

Defines the data containers passed between spider, pipeline, and
database layers during the Scrapy crawl lifecycle.
"""

import scrapy


class WatersArticleItem(scrapy.Item):
    """
    Scrapy item representing a downloaded Waters Knowledge Base article.

    Fields:
        response_url: The URL the article was downloaded from.
        html_content: Raw HTML body of the article page.
        http_status: HTTP response status code.
    """
    response_url = scrapy.Field()
    html_content = scrapy.Field()
    http_status = scrapy.Field()
