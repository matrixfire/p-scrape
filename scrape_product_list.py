import json
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from cj_login import login_and_get_page

PRODUCT_LIST_URL = "https://www.cjdropshipping.com/list/wholesale-womens-clothing-l-2FE8A083-5E7B-4179-896D-561EA116F730.html"

def scrape_product_list():
    playwright = sync_playwright().start()
    browser, page, _, _ = login_and_get_page(playwright=playwright, headless=False)

    page.goto(PRODUCT_LIST_URL)

    # Try to dismiss popups/overlays (try several common selectors and Escape key)
    try:
        page.click("button[aria-label='close']", timeout=3000)
    except Exception:
        pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    # Scroll down to trigger lazy loading
    page.mouse.wheel(0, 2000)
    page.wait_for_timeout(2000)  # Wait for products to load

    # Wait for product cards to appear
    try:
        page.wait_for_selector("div[class^='productCard--']", timeout=15000)
    except Exception:
        print("Timeout: Product cards did not appear in time!")

    # Use Playwright to extract product data
    product_cards = page.query_selector_all("div.product-card")
    print(f"Found {len(product_cards)} product cards")
    if len(product_cards) == 0:
        page.screenshot(path='debug_screenshot.png')
        print("No product cards found. Check screenshot for clues.")

    # Write the rendered HTML to a file for manual inspection
    with open('rendered_product_list.html', 'w', encoding='utf-8') as f:
        f.write(page.content())
        print("Rendered HTML written to rendered_product_list.html")


    # --- EXTRACT PRODUCT DATA FROM PRODUCT CARDS ---
    for card in product_cards:
        try:
            # The <a> tag containing most info
            a_tag = card.query_selector("a.productCard--nLiHk")
            # Name
            name = a_tag.query_selector("div[class*='name']").inner_text().strip() if a_tag and a_tag.query_selector("div[class*='name']") else None
            # Price
            price = a_tag.query_selector("span[class*='sellPriceSpan']").inner_text().strip() if a_tag and a_tag.query_selector("span[class*='sellPriceSpan']") else None
            # Currency
            currency = a_tag.query_selector("span[class*='sellCurrency']").inner_text().strip() if a_tag and a_tag.query_selector("span[class*='sellCurrency']") else None
            # Advertisement Quantity
            ad_quantity = a_tag.query_selector("div[class*='second'] span").inner_text().strip() if a_tag and a_tag.query_selector("div[class*='second'] span") else None
            # Product URL
            product_url = a_tag.get_attribute('href') if a_tag else None
            # Product ID
            product_id = None
            try:
                tracking_elem = a_tag.query_selector("div[class*='productImage'] div[class*='fillBtn']") if a_tag else None
                if tracking_elem:
                    tracking_data = tracking_elem.get_attribute('data-tracking-element-click')
                    if tracking_data:
                        product_id = json.loads(tracking_data)['list'][0]['fieldValue']
            except Exception:
                pass
            # Image URL
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
            print(product_data)
        except Exception as e:
            print(f"Error parsing product card: {e}")

    browser.close()
    playwright.stop()

if __name__ == "__main__":
    scrape_product_list() 