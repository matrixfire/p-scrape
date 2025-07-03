import json
import random
import time
import logging
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from cj_login import login_and_get_context
from config import get_scraped_db_config
from pymongo.collection import Collection
from pymongo import MongoClient, errors
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from utils import sync_timed

PRODUCT_LIST_URL = "https://www.cjdropshipping.com/list/wholesale-womens-clothing-l-2FE8A083-5E7B-4179-896D-561EA116F730.html?pageNum=1&from=US"
BASE_URL = PRODUCT_LIST_URL.split("/list/")[0] + "/"

# ========== Logging setup ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ========== MongoDB helpers ==========
def init_mongo_scraped() -> Optional[Collection]:
    config = get_scraped_db_config()
    try:
        client = MongoClient(config['MONGO_URI'])
        db = client[config['DB_NAME']]
        collection = db[config['COLLECTION_NAME']]
        logger.info(f"MongoDB connected: {config['DB_NAME']}.{config['COLLECTION_NAME']}")
        return collection
    except errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None


def save_to_mongo(collection: Collection, products: List[Dict[str, Any]]) -> None:
    for product in products:
        if collection.find_one({"product_id": product["product_id"]}):
            logger.warning(f"Already exists: {product['product_id']}")
        else:
            collection.insert_one(product)
            logger.info(f"Inserted: {product['name']}")


def extract_product_data(card) -> Optional[Dict[str, Any]]:
    try:
        a_tag = card.query_selector("a.productCard--nLiHk")
        name = a_tag.query_selector("div[class*='name']").inner_text().strip() if a_tag and a_tag.query_selector("div[class*='name']") else None
        price = a_tag.query_selector("span[class*='sellPriceSpan']").inner_text().strip() if a_tag and a_tag.query_selector("span[class*='sellPriceSpan']") else None
        # Currency: get first non-empty
        currency = None
        currency_spans = a_tag.query_selector_all("span[class*='sellCurrency']") if a_tag else []
        for span in currency_spans:
            text = span.inner_text().strip()
            if text:
                currency = text
                break
        ad_quantity = a_tag.query_selector("div[class*='second'] span").inner_text().strip() if a_tag and a_tag.query_selector("div[class*='second'] span") else None
        product_url = a_tag.get_attribute('href') if a_tag else None
        if product_url and not product_url.startswith("http"):
            product_url = urljoin(BASE_URL, product_url)
        product_id = None
        try:
            tracking_elem = a_tag.query_selector("div[class*='productImage'] div[class*='fillBtn']") if a_tag else None
            if tracking_elem:
                tracking_data = tracking_elem.get_attribute('data-tracking-element-click')
                if tracking_data:
                    product_id = json.loads(tracking_data)['list'][0]['fieldValue']
        except Exception:
            pass
        image_url = None
        try:
            img_elem = a_tag.query_selector("img") if a_tag else None
            if img_elem:
                image_url = img_elem.get_attribute('data-src')
        except Exception:
            pass
        product_data = {
            'name': name,
            'price': price,
            'currency': currency,
            'ad_quantity': ad_quantity,
            'product_url': product_url,
            'product_id': product_id,
            'image_url': image_url
        }
        logger.info(f"Scraped product: {product_data}")
        return product_data
    except Exception as e:
        logger.error(f"Error parsing product card: {e}")
        return None


def scrape_single_product_list_page(page, url: str) -> List[Dict[str, Any]]:
    page.goto(url)
    # Try to dismiss popups/overlays
    try:
        page.click("button[aria-label='close']", timeout=3000)
    except Exception:
        pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    page.mouse.wheel(0, 2000)
    page.wait_for_timeout(2000)
    try:
        page.wait_for_selector("div.product-card", timeout=15000)
    except Exception:
        logger.warning(f"Timeout: Product cards did not appear in time for {url}!")
    product_cards = page.query_selector_all("div.product-card")
    logger.info(f"Found {len(product_cards)} product cards on {url}")
    products = []
    for card in product_cards:
        data = extract_product_data(card)
        if data:
            products.append(data)
    return products


def scrape_product_detail_page(context, product_url: str) -> Optional[str]:
    """
    Scrape the detail page for a product and extract the description text from <div id='description-description'>.
    Returns the plain text content, or None if not found.
    """
    logger.info(f"Scraping detail page: {product_url}")
    page = context.new_page()
    page.goto(product_url)
    try:
        page.wait_for_selector("div#description-description", timeout=15000)
    except Exception:
        logger.warning(f"Timeout: description not found for {product_url}")
    html = page.content()
    page.close()
    soup = BeautifulSoup(html, "html.parser")
    desc_div = soup.find("div", id="description-description")
    if desc_div:
        desc_text = desc_div.get_text(separator='\n', strip=True)
        logger.info(f"Extracted description for {product_url} (first 20 chars): {desc_text[:20]}")
        return desc_text
    else:
        logger.warning(f"No description found for {product_url}")
        return None

@sync_timed
def scrape_multiple_pages(base_url: str, num_pages: int = 2) -> List[Dict[str, Any]]:
    playwright = sync_playwright().start()
    browser, context, page, _, _ = login_and_get_context(playwright=playwright, headless=False)
    all_products = []

    for page_num in range(1, num_pages + 1):
        url = f"{base_url}?pageNum={page_num}"
        logger.info(f"--- Scraping page {page_num}: {url} ---")
        products = scrape_single_product_list_page(page, url)
        # For each product, scrape its detail page and add the info
        for product in products:
            detail_info = None
            if product.get('product_url'):
                detail_text = scrape_product_detail_page(context, product['product_url'])
                if detail_text:
                    detail_info = detail_text[:20]  # Truncate to 20 chars
            product['detail_info'] = detail_info
            logger.info(
                "\n========== Enriched product ==========\n"
                f"{json.dumps(product, indent=2, ensure_ascii=False)}\n"
                "======================================\n"
            )
        all_products.extend(products)
        # Add random sleep to minimize anti-scraping detection
        if page_num < num_pages:
            sleep_time = random.uniform(1.5, 4.0)
            logger.info(f"Sleeping for {sleep_time:.2f} seconds before next page...")
            time.sleep(sleep_time)
            
    browser.close()
    playwright.stop()
    return all_products


if __name__ == "__main__":
    all_products = scrape_multiple_pages(PRODUCT_LIST_URL, num_pages=2)
    logger.info(f"Total products scraped: {len(all_products)}")
    # for product in all_products:
    #     logger.info(product)
    # Save to MongoDB
    collection = init_mongo_scraped()
    if collection is not None:
        save_to_mongo(collection, all_products) 