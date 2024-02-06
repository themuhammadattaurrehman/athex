import scrapy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapy.selector import Selector

class AthexSpiderSpider(scrapy.Spider):
    name = "athex_spider"
    allowed_domains = ["www.athexgroup.gr"]
    start_urls = ["https://www.athexgroup.gr/helex-announcements/"]

    custom_settings = {
        "FEED_URI": "s3://fftech1/items.json",
        "FEED_FORMAT": "json",
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36",
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 16,
        "CONCURRENT_REQUESTS_PER_IP": 16,
        "DOWNLOAD_DELAY": 3,
    }

    def __init__(self):
        super(AthexSpiderSpider, self).__init__()
        options = webdriver.ChromeOptions()
        options.headless = True
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, meta={"driver": self.driver})

    def parse(self, response):
        driver = response.meta.get("driver", None)
        if not driver:
            # If 'driver' key is not present, create a new WebDriver instance
            driver = webdriver.Chrome(options=self.driver.options)

        driver.get(response.url)

        # Add an explicit wait for the content to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".portlet-section-body.results-row td a"))
        )

        sel = Selector(text=driver.page_source)
        table_rows = sel.css(".portlet-section-body.results-row")
        
        for row in table_rows:
            title_element = row.css("td a")
            title = title_element.xpath("text()").get() if title_element else None

            date_element = row.css("td:nth-child(2)")
            published_date = date_element.xpath("text()").get() if date_element else None

            yield {
                "title": title,
                "published_date": published_date
            }

        next_page = sel.css("div.page-links a.next::attr(href)").get()
        if next_page:
            next_page_url = response.urljoin(next_page)
            yield scrapy.Request(next_page_url, callback=self.parse, meta={"driver": driver})

    def closed(self, reason):
        self.driver.quit()
