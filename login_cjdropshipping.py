from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set headless=True to run in background
        page = browser.new_page()
        page.goto("https://www.cjdropshipping.com/")

        # Click the login button
        page.click('div.loginBtn--DtPtb a')

        # Wait for the login form to appear
        page.wait_for_selector('form[name="loginForm"]')

        # Fill in the username and password
        page.fill('input[placeholder="用户名/电子邮件地址"]', 'tychan@163.com')
        page.fill('input[placeholder="密码"]', 'Kumai666888!')

        # Submit the form (press Enter in password field)
        page.press('input[placeholder="密码"]', 'Enter')

        # Wait for navigation or some element that indicates login success
        page.wait_for_timeout(5000)  # Wait 5 seconds for demo purposes

        browser.close()

if __name__ == "__main__":
    run()