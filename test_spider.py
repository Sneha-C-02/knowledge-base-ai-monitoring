
import scrapy

class TestSpider(scrapy.Spider):
    name = 'test'
    def start_requests(self):
        print('====== TEST SPIDER START REQUESTS ======')
        yield scrapy.Request('https://example.com', dont_filter=True)

    def parse(self, response):
        print('====== TEST SPIDER PARSE ======')

