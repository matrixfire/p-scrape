import scrapy
import json
import os

class ProductsSpider(scrapy.Spider):
    name = "products"
    allowed_domains = ["cjdropshipping.com"]
    start_urls = ["https://www.cjdropshipping.com/"]

    async def start(self):
        # Load cookies from Playwright
        cookies_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'cj_cookies.json'))
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)

        # Convert Playwright cookies to Scrapy format
        scrapy_cookies = {cookie['name']: cookie['value'] for cookie in cookies}

        for url in self.start_urls:
            yield scrapy.Request(
                url,
                cookies=scrapy_cookies,
                callback=self.parse
            )

    def parse(self, response):
        self.log("Logged in! Now scraping product info...")
        self.log(response.xpath('//title/text()').get())