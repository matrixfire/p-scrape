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
    product_cards = page.query_selector_all("div[class^='thrid--']")
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
            price = card.query_selector("span[class*='sellPriceSpan']").inner_text().strip()
            currency = card.query_selector("span[class*='sellCurrency']").inner_text().strip()
            print({'price': price, 'currency': currency})
        except Exception as e:
            print(f"Error parsing product card: {e}")

    browser.close()
    playwright.stop()

if __name__ == "__main__":
    scrape_product_list() 