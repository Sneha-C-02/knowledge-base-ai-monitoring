
import scrapy
from scrapy.crawler import CrawlerProcess
import sys

class TestSpider(scrapy.Spider):
    name = 'test'
    def start_requests(self):
        print('====== TEST SPIDER START REQUESTS ======')
        sys.stdout.flush()
        yield scrapy.Request('https://example.com', dont_filter=True)

    def parse(self, response):
        print('====== TEST SPIDER PARSE ======')
        sys.stdout.flush()

process = CrawlerProcess({'LOG_ENABLED': False})
process.crawl(TestSpider)
process.start()

