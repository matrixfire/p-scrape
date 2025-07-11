import json
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from playwright.async_api import Page
from typing import List, Optional
from ocr_captcha import handle_captcha


import json
from playwright.async_api import async_playwright, Page



async def handle_login_if_required(page: Page):
    """Check if login prompt appears and log in again if needed."""
    login_btn = await page.query_selector('div[class*="loginBtn"] a')
    if login_btn is not None:
        print("[!] Login prompt detected. Logging in again...")
        await login_btn.click()
        await page.wait_for_selector('form[name="loginForm"]')

        await page.fill('input[placeholder="用户名/电子邮件地址"]', 'tychan@163.com')
        await page.fill('input[placeholder="密码"]', 'Kumai666888!')
        await page.press('input[placeholder="密码"]', 'Enter')
        await page.wait_for_timeout(5000)
        print("[✓] Re-login completed.")


async def login_and_get_context(playwright=None, headless=False):
    close_playwright = False
    if playwright is None:
        playwright = await async_playwright().start()
        close_playwright = True

    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()

    # Load cookies if available
    try:
        with open("cj_cookies.json", "r") as f:
            cookies = json.load(f)
            await context.add_cookies(cookies)
    except FileNotFoundError:
        print("[!] No cookies found. Proceeding without cookies.")

    page = await context.new_page()

    await page.goto("https://www.cjdropshipping.com/")
    await handle_captcha(page)
    await handle_login_if_required(page)

    # Wait for login to settle
    await page.wait_for_timeout(2000)

    # Save cookies after login
    cookies = await context.cookies()
    with open("cj_cookies.json", "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)

    return browser, context, page, playwright, close_playwright






async def nonlogin_and_get_context(playwright=None, headless=False):
    close_playwright = False
    if playwright is None:
        playwright = await async_playwright().start()
        close_playwright = True

    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("https://www.cjdropshipping.com/")
    await handle_captcha(page)
    await page.wait_for_timeout(3000)  # Optional: give it time to load

    # Return same structure as login function
    return browser, context, page, playwright, close_playwright



class CategoryNode:
    def __init__(self, name: str, url: str) -> None:
        self.name: str = name
        self.url: str = url

    def __str__(self) -> str:
        return self.name


async def extract_category_paths_from_page(page: Page) -> List[List[CategoryNode]]:
    """Extracts category paths from a page using Playwright's async API."""
    result_paths: List[List[CategoryNode]] = []
    
    # Check if root UL exists
    root_ul = page.locator('ul.cate1-group').first
    if not await root_ul.is_visible():
        return result_paths

    # Stack for DFS: (locator to current UL, current path)
    stack = [(root_ul, [])]
    
    while stack:
        current_ul, current_path = stack.pop()
        
        # Process each direct child LI
        li_locators = await current_ul.locator(':scope > li').all()
        for li in reversed(li_locators):  # Reverse to maintain left-to-right order
            # Get anchor element
            anchor = li.locator('a').first
            
            # Skip if no anchor found
            if not await anchor.is_visible():
                continue
                
            # Extract category info
            name = (await anchor.text_content() or '').strip()
            url = (await anchor.get_attribute('href') or '').strip()
            new_node = CategoryNode(name, url)
            new_path = current_path + [new_node]
            
            # Check for child UL
            child_ul = li.locator('ul').first
            if await child_ul.is_visible():
                # Add child UL to stack for processing
                stack.append((child_ul, new_path))
            else:
                # Add leaf path to results
                result_paths.append(new_path)
    
    return result_paths