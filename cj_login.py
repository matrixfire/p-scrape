import json
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

def login_and_get_context(playwright=None, headless=False):
    # Optionally accept an existing playwright instance for reuse
    close_playwright = False
    if playwright is None:
        playwright = sync_playwright().start()
        close_playwright = True
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.cjdropshipping.com/")
    page.click('div.loginBtn--DtPtb a')
    page.wait_for_selector('form[name="loginForm"]')
    page.fill('input[placeholder="用户名/电子邮件地址"]', 'tychan@163.com')
    page.fill('input[placeholder="密码"]', 'Kumai666888!')
    page.press('input[placeholder="密码"]', 'Enter')
    page.wait_for_timeout(5000)
    # Save cookies if needed
    cookies = context.cookies()
    with open('cj_cookies.json', 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    # Return browser, context, page, playwright, and close_playwright for further use
    return browser, context, page, playwright, close_playwright

async def login_and_get_context(playwright=None, headless=False):
    close_playwright = False
    if playwright is None:
        playwright = await async_playwright().start()
        close_playwright = True
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("https://www.cjdropshipping.com/")
    await page.click('div.loginBtn--DtPtb a')
    await page.wait_for_selector('form[name="loginForm"]')
    await page.fill('input[placeholder="用户名/电子邮件地址"]', 'tychan@163.com')
    await page.fill('input[placeholder="密码"]', 'Kumai666888!')
    await page.press('input[placeholder="密码"]', 'Enter')
    await page.wait_for_timeout(5000)
    # Save cookies if needed
    cookies = await context.cookies()
    with open('cj_cookies.json', 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    # Return browser, context, page, playwright, and close_playwright for further use
    return browser, context, page, playwright, close_playwright 