# Required: pip install opencv-python pillow pytesseract
import cv2
import numpy as np
from PIL import Image
import pytesseract



from playwright.async_api import async_playwright
import asyncio


def truncate_with_ellipsis(s: str, max_length: int = 10) -> str:
    """
    截断过长的字符串并添加省略号
    :param s: 要截断的原始字符串
    :param max_length: 允许的最大长度（默认10）
    :return: 截断后的字符串
    """
    if len(s) <= max_length:
        return s
    return s[:max_length] + '...'


# Your captcha-solving function (dummy example)
async def solve_captcha_from_src(src_url: str) -> str:
    # Download image and run OCR or any logic you use
    print(f"Solving captcha from: {truncate_with_ellipsis(src_url)}")

    save_base64_image(src_url, "captcha.png")
    captcha_txt = get_captcha_text("captcha.png")
    # Return dummy solution
    print(captcha_txt)
    return captcha_txt

async def handle_captcha(page):
    while True:
        try:
            if page.is_closed():
                print("Page is closed, skipping captcha handling.")
                return

            captcha_div = await page.query_selector("div.commit-main")
            if not captcha_div:
                break  # No captcha, continue with rest of scraping

            print("Captcha detected. Handling...")

            # Step 1: Click "Next" in #step1
            try:
                step1_next_button = await page.query_selector("#step1 button")
                if step1_next_button:
                    await step1_next_button.click()
                    await page.wait_for_timeout(1000)  # wait briefly for step2 to load
            except Exception as e:
                print(f"Error clicking step1 next button: {e}")
                return

            # Step 2: Wait for image to load in #step2
            try:
                captcha_img = await page.wait_for_selector("#step2 img#verifyCode", timeout=5000)
                src = await captcha_img.get_attribute("src")
                if not src:
                    print("Captcha image src not found.")
                    break
            except Exception as e:
                print(f"Error waiting for captcha image: {e}")
                return

            # Step 3: Solve captcha
            try:
                solution = await solve_captcha_from_src(src)
            except Exception as e:
                print(f"Error solving captcha: {e}")
                return

            # Step 4: Fill in captcha and submit
            try:
                await page.fill("#inputVerification", solution)
                await page.click("#submit")
            except Exception as e:
                print(f"Error submitting captcha: {e}")
                return

            # Step 4.5: If an alert popup appears, close it
            try:
                close_btn = await page.query_selector('div.alert-model-foot button.alert-model-foot-button')
                if close_btn:
                    await close_btn.click()
                    await page.wait_for_timeout(500)  # wait briefly after closing
            except Exception:
                pass  # ignore errors if the popup is not present

            # Step 5: Check again if captcha still exists
            await page.wait_for_timeout(2000)  # wait for possible transition

            # Defensive: check if page is closed after possible navigation
            if page.is_closed():
                print("Page closed after captcha submit.")
                return

            try:
                still_there = await page.query_selector("div.commit-main")
            except Exception as e:
                print(f"Error after captcha submit: {e}")
                return

            if not still_there:
                print("Captcha solved successfully.")
                break
            else:
                print("Captcha still present. Refreshing page and retrying...")
                try:
                    await page.reload()
                    await page.wait_for_timeout(1500)  # wait for reload
                except Exception as e:
                    print(f"Error during page reload: {e}")
                    return

        except Exception as e:
            print(f"Error in captcha handler: {e}")
            return

# async def main():
#     async with async_playwright() as pw:
#         browser = await pw.chromium.launch(headless=False)
#         context = await browser.new_context()
#         page = await context.new_page()

#         await page.goto("https://your-target-site.com")

#         await handle_captcha(page)

#         # Proceed with scraping
#         print("Continue with scraping...")

#         await browser.close()

# asyncio.run(main())









def load_image_pil(path: str) -> np.ndarray:
    """Load an image using PIL to handle Unicode paths, and convert to OpenCV BGR format."""
    img_pil = Image.open(path)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def preprocess_image(img: np.ndarray) -> np.ndarray:
    """Apply preprocessing: grayscale, resize, morph close, blur, and threshold."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize to improve OCR recognition
    h, w = gray.shape[:2]
    resized = cv2.resize(gray, (w * 2, h * 2))

    # Morphological closing to fill small gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    closed = cv2.morphologyEx(resized, cv2.MORPH_CLOSE, kernel)

    # Blur to smooth noise
    blurred = cv2.GaussianBlur(closed, (5, 5), sigmaX=1)

    # Threshold using Otsu's method
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    return binary


def extract_text(img: np.ndarray) -> str:
    """Extract text using pytesseract with a character whitelist."""
    config = r'-c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 --psm 8'
    return pytesseract.image_to_string(img, config=config).strip()


def get_captcha_text(image_path: str) -> str:
    img = load_image_pil(image_path)
    processed = preprocess_image(img)
    return extract_text(processed)




###############


import base64

def save_base64_image(data_url: str, filename: str = "output.png") -> None:
    """
    Save a base64-encoded image (data URL) to a PNG file.

    Parameters:
    - data_url (str): The full data URL string starting with 'data:image/...'.
    - filename (str): The output filename to save the image to (default: output.png).
    """
    try:
        header, base64_data = data_url.split(',', 1)
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(base64_data))
        print(f"[✓] Image saved to: {filename}")
    except Exception as e:
        print(f"[✗] Failed to save image: {e}")



















def main():
    image_path = "无标题.png"  # Or any filename with non-ASCII chars
    img = load_image_pil(image_path)
    processed = preprocess_image(img)
    result = extract_text(processed)

    print("CAPTCHA result:", result)


if __name__ == "__main__":
    main()
