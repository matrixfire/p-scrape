import json
from pickle import DICT
import random
import asyncio
import logging
from unicodedata import category
from urllib.parse import urljoin
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from cj_login import login_and_get_context, nonlogin_and_get_context, extract_category_paths_from_page, handle_login_if_required
from config import get_scraped_db_config
from pymongo.collection import Collection
from pymongo import MongoClient, errors
from typing import List, Dict, Any, Optional
from playwright.async_api import ElementHandle
from utils import async_timed, resolve_currency, extract_category_paths, save_log, load_name_url_tuples, TaskTracker, pretty_print_json
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from typing import Any, List, Tuple
from Levenshtein_get_color import get_color_name
from ocr_captcha import handle_captcha
from handle_imgs import extract_valid_urls
from choose_shipping import extract_shipping_info

# ========== Logging setup ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# PRODUCT_LIST_URL = "https://www.cjdropshipping.com/list/wholesale-womens-clothing-l-2FE8A083-5E7B-4179-896D-561EA116F730.html?pageNum=1&from=US"
PRODUCT_LIST_URL = "https://www.cjdropshipping.com/list/wholesale-security-protection-l-192C9D30-5FEA-4B67-B251-AF6E97678DFF.html"
BASE_URL = PRODUCT_LIST_URL.split("/list/")[0] + "/"



async def parse_description_div(page, product_url=''):
    try:
        # Wait for the description div to load
        await page.wait_for_selector('div#description-description', timeout=10000)

        # Get the inner HTML of the div
        div_html = await page.locator('div#description-description').inner_html()

        # Parse only that portion with BeautifulSoup
        soup = BeautifulSoup(div_html, 'html.parser')

        # Extract text and images
        text = soup.get_text(separator='\n', strip=True)
        images = [img['src'] for img in soup.find_all('img') if img.get('src')]

        # Package and dump as JSON string
        result = {
            'product_url': product_url, 
            'text': text,
            'images': images
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        print("[ERROR] Failed to parse description div:", e)
        # Return empty JSON structure as string
        return json.dumps({'product_url': product_url, 'text': '', 'images': []}, ensure_ascii=False)



def transform_packaging_dimensions(input_dict: dict) -> dict:
    new_dict = {k: v for k, v in input_dict.items() if k != '包装尺寸'}

    if '包装尺寸' in input_dict:
        dimension_sets = [d.strip() for d in input_dict['包装尺寸'].split(';') if d.strip()]
        if dimension_sets:
            last_dimension_str = dimension_sets[-1]
            match = re.search(r'(\d+)\*(\d+)\*(\d+)\(mm\)', last_dimension_str)
            if match:
                new_dict['length'] = f"{float(match.group(1)) / 10:.0f}"
                new_dict['width'] = f"{float(match.group(2)) / 10:.0f}"
                new_dict['height'] = f"{float(match.group(3)) / 10:.0f}"
                new_dict['size_unit'] = "cm"
            else:
                print(f"Warning: Could not parse packaging dimensions from '{last_dimension_str}'")
        else:
            print("Warning: '包装尺寸' key found but no valid dimension sets.")
    return new_dict


def get_country_from_url(url: str) -> str:
    """
    Parse the given URL and return the country from the 'from' query parameter.
    If not present, return 'Global'.
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    country = query.get('from', [None])[0]
    return country if country else "Global"


def set_country_in_url(url: str, country: str) -> str:
    """
    Set or update the 'from' query parameter in the given URL with the specified country.

    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    # Set or update the 'from' parameter
    query['from'] = [country]

    # Encode query parameters back into URL
    new_query = urlencode(query, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


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
        if collection.find_one({"pid": product["pid"]}):
            logger.warning(f"Already exists: {product['pid']}")
        else:
            collection.insert_one(product)
            logger.info(f"Inserted: {product['name']}")


def save_one_product_to_mongo(collection: Collection, product: Dict[str, Any]) -> None:
    if collection.find_one({"pid": product["pid"]}):
        logger.warning(f"Already exists: {product['pid']}")
    else:
        collection.insert_one(product)
        logger.info(f"Inserted: {product['name']}")


async def safe_goto(page, url):
    await page.goto(url)
    await handle_captcha(page)
    await handle_login_if_required(page)


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


def enrich_variants_with_product_id(product: dict) -> dict:
    """
    Enrich each variant in the 'variants' list with a custom 'product_id',
    and remove the outer 'product_id' key from the product dictionary.

    Args:
        product (dict): Original product dictionary with a 'variants' list and top-level 'product_id'.

    Returns:
        dict: Modified dictionary with enriched variants and no outer 'product_id'.
    """
    if "variants" in product and isinstance(product["variants"], list):
        for variant in product["variants"]:
            sku = variant.get("sku", "")
            variant_key = variant.get("variant_key", "")
            top_product_id = product.get("product_id", "")
            # Construct the new product_id for the variant
            variant["product_id"] = f"cj_{top_product_id}"

    # Remove the outer 'product_id'
    product["pid"] = product["product_id"]
    product.pop("product_id", None)
    pretty_print_json(product, "Enriched Product Dict", 10, 3)

    return product


async def extract_product_data(card) -> Optional[Dict[str, Any]]:
    ''' From list page, getting each product card's data '''
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
                # print(f"currency is {currency}")
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
        product_data_basic = {
            'name': name,
            'price': price,
            'currency': resolve_currency(str(currency)),
            'product_url': product_url,
            'product_id': product_id,
            'image_url': image_url
        }
        # logger.info(f"Scraped product: {product_data_basic}")
        return product_data_basic
    except Exception as e:
        logger.error(f"Error parsing product card: {e}")
        return None


@async_timed
async def scrape_single_product_list_page(page, url: str) -> List[Dict[str, Any]]:
    await safe_goto(page, url)
    await handle_captcha(page)
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
    logger.info(f"Found {len(product_cards)} product cards on {url}\n")
    products = []
    for card in product_cards:
        data = await extract_product_data(card)
        if data:
            products.append(data)
    return products


def getting_color(s):
    first_part = s.split("-")[0].lower()
    color_name = get_color_name(first_part)
    if color_name == "NOT FOUND":
        color_name = "多色"

    return color_name

def getting_size(s):
    try:
        first_part = s.split("-")[1].lower()
        size_name = first_part
    except:
        size_name = "NO SIZE"

    return size_name


def get_country_data(data_list, target_country="US"):
    for item in data_list:
        if item.get("countryCode") == target_country:
            return item
    # If not found, return a zero-valued default dict for the country
    return {
        "countryCode": target_country,
        "totalInventory": 0,
        "cjInventory": 0,
        "factoryInventory": 0,
        "verifiedWarehouse": 0
    }



async def fetch_logistics_data_individual(page, product_url: str = "", skus_need_shipping_dict: dict = None):
    """异步抓取当前页面的物流信息，仅对 skus_need_shipping_dict 中 value 为 1 的 sku 发起请求"""
    try:
        if not skus_need_shipping_dict:
            print("⚠️ 未提供 sku 列表，跳过抓取")
            return None

        await page.wait_for_function("window.productDetailData?.stanProducts?.length > 0", timeout=10_000)

        # evaluate 中传入 skus_need_shipping_dict 参数
        logistics_data = await page.evaluate(
            """async (skusNeedShipping) => {
                const variants = window.productDetailData?.stanProducts || [];
                const productInfo = window.productDetailData;
                if (!variants.length || !productInfo) return { error: "Missing product data" };

                // 过滤 variants，只保留需要 shipping 的 sku
                const filteredVariants = variants.filter(v => skusNeedShipping[v.sku.toLowerCase()] === 1);

                const productType = productInfo.productType;
                const startCountryCode = 'US';
                const receiverCountryCode = 'US';
                const platform = 'shopify';
                const quantity = 1;
                const customerCode = window.loginInfoController?.info?.("userId") || "";
                const token = window.loginInfoController?.info?.("token") || "";

                const fetchResults = [];

                for (const variant of filteredVariants) {
                    const param = {
                        startcountrycode: startCountryCode,
                        countrycode: receiverCountryCode,
                        platform: platform,
                        property: productInfo.property.key,
                        weight: +variant.packWeight * quantity,
                        sku: variant.sku,
                        pid: productInfo.id,
                        length: variant.long,
                        width: variant.width,
                        height: variant.height,
                        volume: +variant.volume * quantity,
                        quantity: quantity,
                        customercode: customerCode,
                        skus: [variant.sku],
                        producttype: productType,
                        supplierid: productType === window.CjProductDetail_type?.$u?.SupplierSelf
                            ? productInfo.supplierId
                            : undefined
                    };

                    // Make sure all keys in param are lowercased
                    const lowerParam = {};
                    for (const k in param) {
                        if (Object.hasOwn(param, k)) {
                            lowerParam[k.toLowerCase()] = param[k];
                        }
                    }

                    try {
                        const res = await fetch("https://www.cjdropshipping.com/product-api/assign/batchUnionLogisticsFreightV355", {
                            method: "POST",
                            headers: {
                                "accept": "application/json;charset=utf-8",
                                "content-type": "application/json;charset=UTF-8",
                                "token": token
                            },
                            body: JSON.stringify([lowerParam]),
                            credentials: "include"
                        });

                        const contentType = res.headers.get("content-type") || "";
                        if (!res.ok || !contentType.includes("application/json")) {
                            const text = await res.text();
                            // Lowercase keys for error object
                            fetchResults.push({ error: "Invalid response", preview: text.slice(0, 300), sku: variant.sku.toLowerCase() });
                            continue;
                        }

                        const json = await res.json();
                        // Lowercase keys for result object
                        fetchResults.push({ sku: variant.sku.toLowerCase(), result: json?.data || [] });
                    } catch (e) {
                        fetchResults.push({ error: "Request failed", detail: e?.toString?.(), sku: variant.sku.toLowerCase() });
                    }
                }

                // Lowercase all keys in each result object
                return fetchResults.map(obj => {
                    const lowerObj = {};
                    for (const k in obj) {
                        if (Object.hasOwn(obj, k)) {
                            lowerObj[k.toLowerCase()] = obj[k];
                        }
                    }
                    return lowerObj;
                });
            }""",
            skus_need_shipping_dict  # 👈 这里是传入的 Python dict，会作为 skusNeedShipping 出现在 JS 中
        )

        print(f"\n🚚 每个 variant 的物流数据 from {product_url or '[current page]'}:")
        print("=" * 40)

        for entry in logistics_data:
            # All keys are lowercased now
            sku = entry.get("sku", "N/A")
            if "error" in entry:
                print(f"❌ {sku}: {entry['error']}")
                if "preview" in entry:
                    print(f"🔍 预览: {entry['preview']}")
                continue

            results = entry.get("result", [])
            print(f"✅ SKU: {sku}")
            for item in results:
                # Try to print lowercased keys for item as well
                logistic_name = item.get('logisticname', item.get('logisticName'))
                price = item.get('price', "")
                print(f"  {logistic_name}: {price}")

        print("=" * 40)
        return logistics_data

    except Exception as e:
        print("⚠️ 异常发生:", e)
        return None




def extract_dimensions(s: str) -> tuple:
    try:
        parts = dict(item.split('=') for item in s.split(','))
        def to_cm(key):
            value = parts.get(key, "")
            return str(round(float(value) / 10, 1)) if value else ""
        return to_cm("long"), to_cm("width"), to_cm("height")
    except Exception:
        return "", "", ""


async def extract_variant_skus_and_inventory(page, product_dict: Dict[str, Any], product_url: str):
    ''' inventory and logistics '''
    try:
        # Step 1: Extract product and inventory data
        product_data = await page.evaluate("() => window.productDetailData?.stanProducts || []")
        variant_inventory_data = await page.evaluate("() => window.productDetailData?.variantInventory || []")
        # await page.wait_for_load_state("networkidle")

        
        # Extract all image links from divs with data-id attribute inside the slides container
        all_image_links = []
        image_divs = await page.query_selector_all('div#slides > div[data-id] > div[data-id]')
        for div in image_divs:
            data_id = await div.get_attribute('data-id')
            if data_id:
                all_image_links.append(data_id)

        if product_data:
            variants = []

            # Build a lookup dictionary from vid -> inventory info
            inventory_lookup = {}
            for inv_entry in variant_inventory_data:
                ''' inv_entry will be like:
                {'vid': 'FF730E7B-8B6D-45D8-B7A4-8562227A0CB6',
                'inventory': [{'countryCode': 'CN',
                'totalInventory': 10928,
                'cjInventory': 0,
                'factoryInventory': 10928,
                'verifiedWarehouse': 2}]}
                '''

                vid = inv_entry.get("vid")
                inventory_list = inv_entry.get("inventory", [])

                if inventory_list:
                    inv = get_country_data(inventory_list, "US") #; inventory_list[0]
                    inventory_lookup[vid] = {
                        "cjInventory": int(inv.get("cjInventory") or 0),
                        "factoryInventory": int(inv.get("factoryInventory") or 0)
                    }
            skus_need_shipping_dict = {} # {"sku1": 0, "sku2": 1}
            # Match each product's id with inventory vid
            for item in product_data:
                sku = item.get("sku")
                variant_id = item.get("id")  # same as vid
                variant_price = item.get("sellPrice")
                variant_weight = item.get("weight")
                variant_img = item.get("image").encode('utf-8').decode('unicode_escape')
                variant_key = item.get("variantKey", "")

                inventory_info = inventory_lookup.get(variant_id, {"cjInventory": 0, "factoryInventory": 0})
                bg_imgs_str = ','.join(all_image_links)
                variant_details = {
                    "sku": f"{sku.lower()}",
                    "variant_id": variant_id,
                    "cjInventory": inventory_info["cjInventory"],
                    "factoryInventory": inventory_info["factoryInventory"],
                    "price": variant_price,
                    "weight": variant_weight,
                    "weight_unit": "g",
                    "variant_image": variant_img,
                    "variant_key": variant_key,
                    "bg_img": ','.join([img_url for img_url in extract_valid_urls(bg_imgs_str) if img_url != variant_img]),
                    "color": getting_color(variant_key),
                    "size":  getting_size(variant_key),
                    "length": extract_dimensions(item.get("standard", ""))[0],
                    "width": extract_dimensions(item.get("standard", ""))[1],
                    "height": extract_dimensions(item.get("standard", ""))[2],
                    "size_unit": "cm",
                    "shipping_fee": "",
                    "shipping_method": "",
                    "delivery_time": "",
                }
                # print(variant_details)
                if int(variant_details['cjInventory']) >= 5:
                    skus_need_shipping_dict[variant_details['sku']] = 1
                else:
                    skus_need_shipping_dict[variant_details['sku']] = 0
                    

                variants.append(variant_details)
            print(skus_need_shipping_dict)
            logistics = await fetch_logistics_data_individual(page, skus_need_shipping_dict=skus_need_shipping_dict)
            shipping_result = extract_shipping_info(skus_need_shipping_dict, logistics)
            for variant_details in variants:
                variant_details.update(shipping_result[variant_details["sku"].lower()])
            # pretty_print_json(logistics, "LOGISTICS INFO", 10, 2)
            # pretty_print_json(shipping_result, "Shipping Choice")
            product_dict["variants"] = variants
            # logger.info(f"Extracted {len(variants)} variants with SKUs and inventory from {product_url}")
        else:
            logger.warning(f"No stanProducts found for {product_url}")

    except Exception as e:
        logger.error(f"Failed to extract variant SKUs and inventory from JS on {product_url}: {e}")


async def scrape_product_detail_page(context, product_url: str, semaphore: asyncio.Semaphore, context_dict = {}) -> Optional[Dict[str, Any]]:
    product_dict = {}
    # Use a semaphore to limit the number of concurrent detail page scrapes
    async with semaphore:
        logger.info(f"Scraping detail page: {product_url}")
        # Open a new browser page for this product detail
        page = await context.new_page()
        try:
            # Navigate to the product detail page with a timeout
            await safe_goto(page, product_url)
            await handle_captcha(page)

            # === 1. Extract variant SKUs and info from JS ===
            await extract_variant_skus_and_inventory(page, product_dict, product_url)

            # === 2. Wait for and extract description (same as your original) ===
            try:
                # Wait for the description section to appear (if it exists)
                await page.wait_for_selector("div#description-description", timeout=35000)
            except PlaywrightTimeoutError:
                # Log a warning if the description section does not appear in time
                logger.warning(f"Timeout: description not found for {product_url}")
            # Use Playwright's selector to get the description text
            desc_elem = await page.query_selector("div#description-description")

            other_data = await parse_description_div(page, product_url)

            category = await extract_breadcrumb(page)
            if category is None:
                category = context_dict["category"]
            # category = context_dict["category"]
            product_dict['category'] = category
            # if desc_elem:
            #     # Try to find a child div with class containing 'descriptionContainer'
            #     child_elem = await desc_elem.query_selector('div[class*="descriptionContainer"]')
            #     info_dict = await extract_table_items(desc_elem)
            #     info_dict = transform_packaging_dimensions(info_dict)
            #     if child_elem:
            #         child_text = (await child_elem.inner_text()).strip()
            #         logger.info(f"\n\n========== Extracted child description for {product_url}: {info_dict} ==========\n\n")
            #         product_dict['description'] = child_text
            #         # product_dict.update(info_dict)
            #         # pretty_print_json(product_dict, "Product Dict", 10, 3)
            #         # return product_dict
            # else:
            #     # Log a warning if the description div is not found
            #     logger.warning(f"No description found for {product_url}")
                # return None
            product_dict['description'] = other_data    
            return product_dict
                
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


def build_paginated_url(base_url: str, page_num: int) -> str:
    """
    Given a base_url, return a new URL with the pageNum parameter set to page_num.
    If pageNum already exists, it will be replaced. Other query params are preserved.
    """
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query['pageNum'] = [str(page_num)]
    new_query = urlencode(query, doseq=True)
    new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    return new_url


async def get_breadcrumb_(page, category_name="CATEGORY") -> str:
    """
    Extracts the breadcrumb trail from the product page.
    Falls back to 'CATEGORY' if extraction fails.
    """
    try:
        breadcrumb = await page.evaluate("""() => {
            const containers = Array.from(document.querySelectorAll('div'));
            const breadcrumbContainer = containers.find(div =>
                div.innerText.includes('Home') && div.querySelectorAll('a').length > 1
            );

            if (!breadcrumbContainer) return null;

            const links = Array.from(breadcrumbContainer.querySelectorAll('a'));
            const filtered = links
                .map(a => a.textContent.trim())
                .filter(text => text.toLowerCase() !== 'home');

            return filtered.length ? filtered.join(' / ') : null;
        }""")
    except Exception:
        breadcrumb = None

    # return breadcrumb or category_name
    return category_name


async def get_breadcrumb(page, category_name="CATEGORY") -> str:
    """
    Extracts the breadcrumb trail from the product page.
    Falls back to 'CATEGORY' if extraction fails.
    """
    try:
        # Wait for the selector to exist to avoid NoneType errors
        await page.wait_for_selector('div#vue-search-filter div.select-item', timeout=5000)
        div_html = await page.locator('div#vue-search-filter div.select-item').inner_html()
        soup = BeautifulSoup(div_html, "lxml")
        # Defensive: .select() may return empty list
        parts = [a.get_text(strip=True).rstrip(">").strip() for a in soup.select("a.filter-span")]
        if not parts:
            return category_name
        combined_path_category = " / ".join(parts)
        if not combined_path_category.strip():
            return category_name
        return combined_path_category
    except Exception as e:
        return category_name
    

async def extract_breadcrumb(page):
    try:
        result = await page.evaluate("""() => {
            // Find all <div> elements whose class includes "bread"
            const breadcrumbDivs = Array.from(document.querySelectorAll("div[class*='bread']"));

            for (const div of breadcrumbDivs) {
                const links = Array.from(div.querySelectorAll("a"));
                if (links.length > 1 && links[0].textContent.trim().toLowerCase() === "home") {
                    // Skip the first "Home" link, join the rest with "/"
                    return links
                        .slice(1)
                        .map(a => a.textContent.trim())
                        .join("/");
                }
            }
            return null;
        }""")

        return result if result else None
    except Exception as e:
        print(f"[ERROR] Failed to extract breadcrumb: {e}")
        return None





async def get_max_num_pages(page) -> int:
    """
    Extract the maximum number of pages from the product listing page.
    Looks for: <div class="to-go"> ... <span>of N</span> ... </div>
    Returns the integer N, or 1 if not found.
    """
    try:
        # Wait for the pagination element to appear
        await page.wait_for_selector('div.to-go span', timeout=15000)
        spans = await page.query_selector_all('div.to-go span')
        for span in spans:
            text = (await span.inner_text()).strip()
            print(f"TEXT FOUND: {text}")
            # Try to extract the last number in the text, regardless of language or prefix
            numbers = re.findall(r'\d+', text)
            if numbers:
                return int(numbers[-1])
    except Exception as e:
        logger.warning(f"Could not extract max num pages: {e}")
    return 1


async def get_categories_links(page: Any) -> List[Tuple[str, str]]:
    # First, hover over the ul.cate1-group element to trigger category fetching
    try:
        await page.wait_for_selector('ul.cate1-group', timeout=10000)
        await page.hover('ul.cate1-group')
        # Add a small delay to allow the hover to trigger the data fetching
        await page.wait_for_timeout(1000)
    except Exception as e:
        logger.warning(f"Could not hover over ul.cate1-group: {e}")
    
    # await page.wait_for_selector('li.cate2-item', timeout=5000) # later added
    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title and soup.title.string else '(No title found)'
    result_paths_: List[List[dict]] = extract_category_paths(soup)
    print(len(result_paths_), '\n'*10)
    # Save result_paths_ to a JSON file for inspection
    with open("category_paths.json", "w", encoding="utf-8") as f:
        json.dump(result_paths_, f, ensure_ascii=False, indent=2)
    # result_paths = [p[-1] for p in result_paths_]
    real_cared_ones: List[dict] = [lt[-1] for lt in result_paths_]

    categoris_links: List[Tuple[str, str]] = [(obj["name"], urljoin(BASE_URL, obj["url"])) for obj in real_cared_ones]
    print(f"[BeautifulSoup] Page title: {title}, {categoris_links[0]}"+'\n'*10)
    return categoris_links


async def scrape_multiple_pages(
    start_url: str,
    num_pages: int = 0,
    max_concurrent_details: int = 3,
    context=None,
    page=None,
    category="general"
) -> List[Dict[str, Any]]:
    country = get_country_from_url(start_url)

    close_context = False
    if context is None or page is None:
        playwright = await async_playwright().start()
        browser, context, page, _, _ = await login_and_get_context(playwright=playwright, headless=False)
        close_context = True

    all_products = []
    semaphore = asyncio.Semaphore(max_concurrent_details)
    await safe_goto(page, build_paginated_url(start_url, 1))
    await handle_captcha(page)

    if num_pages <= 0:
        num_pages = await get_max_num_pages(page)
        logger.info(f"Detected max num_pages: {num_pages}")

    for page_num in range(1, num_pages + 1):
        url = build_paginated_url(start_url, page_num)
        logger.info(f"\n--- Scraping page {page_num}: {url} ---\n")

        products = await scrape_single_product_list_page(page, url)
        detail_tasks = []
        for product in products:
            if product.get('product_url'):
                detail_tasks.append(scrape_product_detail_page(context, product['product_url'], semaphore, context_dict={"category": category}))
            else:
                detail_tasks.append(asyncio.sleep(0, result=None))
        detail_infos = await asyncio.gather(*detail_tasks)

        for product, detail_info in zip(products, detail_infos):
            if detail_info is not None:
                product.update(detail_info)
            # product.update({"country": country, "category": category})
            # category = await get_breadcrumb(page, category)
            print("FOUND CATEGORY", category)
            product.update({"country": country})
            pretty_print_json(product, "AFTER scrape_multiple_pages", 30, 5)

        products = list(map(enrich_variants_with_product_id, products))
        all_products.extend(products)
        if page_num < num_pages:
            sleep_time = random.uniform(1.5, 4.0)
            logger.info(f"Sleeping for {sleep_time:.2f} seconds before next page...")
            await asyncio.sleep(sleep_time)
    if close_context:
        await context.close()
        await browser.close()
    return all_products


async def scrape_multiple_urls(urls, collection, tracker, max_concurrent_details=3):
    async with async_playwright() as playwright:
        browser, context, page, _, _ = await login_and_get_context(playwright=playwright, headless=False)
        
        all_results = []

        if len(urls) == 0:
            categoris_links = await get_categories_links(page)
            urls = categoris_links

        for url_obj in urls:
            url = url_obj[-1]
            category = url_obj[0]
            logger.info(f"\n=== Scraping URL: {url} ===\n")
            await safe_goto(page, url)
            await handle_captcha(page)
            
            products = await scrape_multiple_pages(
                url,
                num_pages=0,
                max_concurrent_details=max_concurrent_details,
                context=context,
                page=page,
                category = category
            )
            all_results.extend(products)

            for product in products:
                save_one_product_to_mongo(collection, product)
            tracker.mark_done({'name':url_obj[0], 'url': url_obj[1].split('?')[0]})

        await asyncio.sleep(10) #testing

        await browser.close()
        return all_results


if __name__ == "__main__":
    collection = init_mongo_scraped()
    with open("diff_tt.json", "r", encoding='utf-8') as f:
        tasks = json.load(f)
    tracker = TaskTracker(tasks, id_key='url', progress_file='')
    print(f"Found tasks: {len(tasks)}\n")
    
    COUNTRY = get_country_from_url(PRODUCT_LIST_URL)
    COUNTRY = "US"

    urls_ = [(d['name'], d['url'])for d in tracker.get_pending_tasks()]
    urls = [(t[0], set_country_in_url(t[1], COUNTRY)) for t in urls_]
    print(urls)

    all_products = asyncio.run(scrape_multiple_urls(urls, max_concurrent_details=3, collection=collection, tracker=tracker))
    logger.info(f"\nTotal products scraped: {len(all_products)}\n")
