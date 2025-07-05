import json
from pickle import DICT
import random
import asyncio
import logging
from urllib.parse import urljoin
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from cj_login import login_and_get_context
from config import get_scraped_db_config
from pymongo.collection import Collection
from pymongo import MongoClient, errors
from typing import List, Dict, Any, Optional


from playwright.async_api import ElementHandle

from utils import async_timed
import re


def transform_packaging_dimensions(input_dict: dict) -> dict:
    new_dict = {k: v for k, v in input_dict.items() if k != '包装尺寸'}

    if '包装尺寸' in input_dict:
        dimension_sets = [d.strip() for d in input_dict['包装尺寸'].split(';') if d.strip()]
        if dimension_sets:
            last_dimension_str = dimension_sets[-1]
            match = re.search(r'(\d+)\*(\d+)\*(\d+)\(mm\)', last_dimension_str)
            if match:
                new_dict['长'] = f"{float(match.group(1)) / 10:.0f}cm"
                new_dict['宽'] = f"{float(match.group(2)) / 10:.0f}cm"
                new_dict['高'] = f"{float(match.group(3)) / 10:.0f}cm"
            else:
                print(f"Warning: Could not parse packaging dimensions from '{last_dimension_str}'")
        else:
            print("Warning: '包装尺寸' key found but no valid dimension sets.")
    return new_dict


# PRODUCT_LIST_URL = "https://www.cjdropshipping.com/list/wholesale-womens-clothing-l-2FE8A083-5E7B-4179-896D-561EA116F730.html?pageNum=1&from=US"
PRODUCT_LIST_URL = "https://www.cjdropshipping.com/list/wholesale-pet-supplies-l-2409110611570657700.html?pageNum=1&from=US"
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


async def extract_table_items(desc_elem: ElementHandle) -> Dict[str, str]:
    """
    Given a parent element desc_elem, extract key-value pairs from child elements
    whose class includes "tableItem", and return them as a dictionary.
    """
    table_items = await desc_elem.query_selector_all("div[class*='tableItem']")
    result = {}

    for item in table_items:
        label_elem = await item.query_selector("div[class*='tableLabel']")
        text_elem = await item.query_selector("div[class*='tableText']")

        # Extract inner text safely
        label = await label_elem.inner_text() if label_elem else None
        text = await text_elem.inner_text() if text_elem else None

        if label and text:
            result[label.strip()] = text.strip()

    return result


async def extract_product_data(card) -> Optional[Dict[str, Any]]:
    try:
        a_tag = await card.query_selector("a.productCard--nLiHk")
        name = (await (await a_tag.query_selector("div[class*='name']")).inner_text()).strip() if a_tag and await a_tag.query_selector("div[class*='name']") else None
        price = (await (await a_tag.query_selector("span[class*='sellPriceSpan']")).inner_text()).strip() if a_tag and await a_tag.query_selector("span[class*='sellPriceSpan']") else None
        # Currency: get first non-empty
        currency = None
        currency_spans = await a_tag.query_selector_all("span[class*='sellCurrency']") if a_tag else []
        for span in currency_spans:
            text = (await span.inner_text()).strip()
            if text:
                currency = text
                break
        ad_quantity = (await (await a_tag.query_selector("div[class*='second'] span")).inner_text()).strip() if a_tag and await a_tag.query_selector("div[class*='second'] span") else None
        product_url = await a_tag.get_attribute('href') if a_tag else None
        if product_url and not product_url.startswith("http"):
            product_url = urljoin(BASE_URL, product_url)
        product_id = None
        try:
            tracking_elem = await a_tag.query_selector("div[class*='productImage'] div[class*='fillBtn']") if a_tag else None
            if tracking_elem:
                tracking_data = await tracking_elem.get_attribute('data-tracking-element-click')
                if tracking_data:
                    product_id = json.loads(tracking_data)['list'][0]['fieldValue']
        except Exception:
            pass
        image_url = None
        try:
            img_elem = await a_tag.query_selector("img") if a_tag else None
            if img_elem:
                image_url = await img_elem.get_attribute('data-src')
        except Exception:
            pass
        product_data = {
            'name': name,
            'price': price,
            'currency': currency,
            # 'ad_quantity': ad_quantity,
            'product_url': product_url,
            'product_id': product_id,
            'image_url': image_url
        }
        # logger.info(f"Scraped product: {product_data}")
        return product_data
    except Exception as e:
        logger.error(f"Error parsing product card: {e}")
        return None


async def scrape_single_product_list_page(page, url: str) -> List[Dict[str, Any]]:
    await page.goto(url)
    # Try to dismiss popups/overlays
    try:
        await page.click("button[aria-label='close']", timeout=3000)
    except Exception:
        pass
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass
    await page.mouse.wheel(0, 2000)
    await page.wait_for_timeout(2000)
    try:
        await page.wait_for_selector("div.product-card", timeout=15000)
    except Exception:
        logger.warning(f"Timeout: Product cards did not appear in time for {url}!")
    product_cards = await page.query_selector_all("div.product-card") # *** Extract product cards from the product list page
    logger.info(f"Found {len(product_cards)} product cards on {url}")
    products = []
    for card in product_cards:
        data = await extract_product_data(card)
        if data:
            products.append(data)
    return products


async def scrape_product_detail_page(context, product_url: str, semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
    detailed_info_dict = {}
    # Use a semaphore to limit the number of concurrent detail page scrapes
    async with semaphore:
        logger.info(f"Scraping detail page: {product_url}")
        # Open a new browser page for this product detail
        page = await context.new_page()
        try:
            # Navigate to the product detail page with a timeout
            await page.goto(product_url, timeout=30000)
            
            # === 1. Extract variant SKUs from JS ===
            try:
                product_data = await page.evaluate("() => window.productDetailData?.stanProducts || []")
                if product_data:
                    skus = [item["sku"] for item in product_data if "sku" in item]
                    detailed_info_dict["variants"] = skus
                    logger.info(f"Extracted {len(skus)} SKUs from variants on {product_url}")
                else:
                    logger.warning(f"No stanProducts found for {product_url}")
            except Exception as e:
                logger.error(f"Failed to extract variant SKUs from JS on {product_url}: {e}")

            # === 2. Wait for and extract description (same as your original) ===
            try:
                # Wait for the description section to appear (if it exists)
                await page.wait_for_selector("div#description-description", timeout=15000)
            except PlaywrightTimeoutError:
                # Log a warning if the description section does not appear in time
                logger.warning(f"Timeout: description not found for {product_url}")
            # Use Playwright's selector to get the description text
            desc_elem = await page.query_selector("div#description-description")
            if desc_elem:
                # Try to find a child div with class containing 'descriptionContainer'
                child_elem = await desc_elem.query_selector('div[class*="descriptionContainer"]')
                info_dict = await extract_table_items(desc_elem)
                info_dict = transform_packaging_dimensions(info_dict)
                if child_elem:
                    child_text = (await child_elem.inner_text()).strip()
                    logger.info(f"\n\n========== Extracted child description for {product_url} (first 20 chars): {info_dict} ==========\n\n")
                    detailed_info_dict['description'] = child_text
                    detailed_info_dict.update(info_dict)
                    return detailed_info_dict
            else:
                # Log a warning if the description div is not found
                logger.warning(f"No description found for {product_url}")
                return None
        except PlaywrightTimeoutError:
            # Handle timeout errors when loading the page
            logger.error(f"Timeout loading page: {product_url}")
            return None
        except PlaywrightError as e:
            # Handle other Playwright-specific errors
            logger.error(f"Playwright error for {product_url}: {e}")
            return None
        except Exception as e:
            # Handle any other unexpected errors
            logger.error(f"Unexpected error for {product_url}: {e}")
            return None
        finally:
            # Always attempt to close the page, even if an error occurred
            try:
                await page.close()
            except Exception:
                pass
        # Optionally, add a small random sleep to reduce load and avoid anti-scraping detection
        await asyncio.sleep(random.uniform(0.2, 0.6))


@async_timed
async def scrape_multiple_pages(base_url: str, num_pages: int = 2, max_concurrent_details: int = 3) -> List[Dict[str, Any]]:
    async with async_playwright() as playwright:
        browser, context, page, _, _ = await login_and_get_context(playwright=playwright, headless=False)
        all_products = []
        semaphore = asyncio.Semaphore(max_concurrent_details)
        for page_num in range(1, num_pages + 1):
            url = f"{base_url}?pageNum={page_num}"
            logger.info(f"--- Scraping page {page_num}: {url} ---")
            products = await scrape_single_product_list_page(page, url)
            # For each product, scrape its detail page and add the info concurrently
            detail_tasks = []
            for product in products:
                if product.get('product_url'):
                    detail_tasks.append(scrape_product_detail_page(context, product['product_url'], semaphore))
                else:
                    detail_tasks.append(asyncio.sleep(0, result=None))
            detail_infos = await asyncio.gather(*detail_tasks)
            for product, detail_info in zip(products, detail_infos):
                # product['detail_info'] = detail_info[:20] if detail_info else None
                product.update(detail_info)
                logger.info(
                    "\n========== Enriched product =========="
                    f"{json.dumps(product, indent=2, ensure_ascii=False)}\n"
                    "======================================\n"
                )
            all_products.extend(products)
            # Add random sleep to minimize anti-scraping detection
            if page_num < num_pages:
                sleep_time = random.uniform(1.5, 4.0)
                logger.info(f"Sleeping for {sleep_time:.2f} seconds before next page...")
                await asyncio.sleep(sleep_time)
        await browser.close()
        return all_products


if __name__ == "__main__":
    all_products = asyncio.run(scrape_multiple_pages(PRODUCT_LIST_URL, num_pages=2, max_concurrent_details=3))
    logger.info(f"Total products scraped: {len(all_products)}")
    # for product in all_products:
    #     logger.info(product)
    # Save to MongoDB
    collection = init_mongo_scraped()
    if collection is not None:
        save_to_mongo(collection, all_products) 