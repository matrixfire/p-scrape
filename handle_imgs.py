import asyncio
import aiohttp
from typing import Optional, List
import re


SUPERBED_UPLOAD_API = "https://api.superbed.cc/upload"
SUPERBED_API_TOKEN = "74540c146b1c41a69f6bb51c2e618290"
DEFAULT_CATEGORY = "sy"
MAX_RETRIES = 5




def extract_valid_urls(text):
    """
    Extracts only valid URLs (starting with http/https) from a comma-separated string.
    """
    # Split by comma
    parts = text.split(',')
    # Use regex to validate URL
    url_regex = re.compile(r'^https?://[^\s,]+\.jpg$', re.IGNORECASE)
    # Filter and return valid URLs only
    return [part for part in parts if url_regex.match(part)]



class SuperbedUploader:
    def __init__(self, token: str, category: str = DEFAULT_CATEGORY):
        self.token = token
        self.category = category

    async def upload_image(self, session: aiohttp.ClientSession, image_url: str) -> Optional[str]:
        """Upload an image URL to Superbed with retries."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.post(
                    SUPERBED_UPLOAD_API,
                    data={
                        "token": self.token,
                        "categories": self.category,
                        "src": image_url
                    }
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("url")
            except Exception as e:
                print(f"⚠️ Attempt {attempt}/{MAX_RETRIES} failed for {image_url}: {e}")
        return None


async def process_images(input_str: str) -> str:
    cleaned_txt = ','.join(extract_valid_urls(input_str))
    image_urls = [url.strip() for url in cleaned_txt.split(",") if url.strip()]
    uploader = SuperbedUploader(token=SUPERBED_API_TOKEN)

    async with aiohttp.ClientSession() as session:
        tasks = [uploader.upload_image(session, url) for url in image_urls]
        results = await asyncio.gather(*tasks)

    modified_urls = [f"{url}?w=900" if url else "" for url in results]
    return ",".join(modified_urls)







if __name__ == "__main__":
    input_txt = '''https://cf.cjdropshipping.com/20200815/1586159702191.jpg,https://cf.cjdropshipping.com/20200815/1843395913091.jpg,https://cf.cjdropshipping.com/20200815/230347672425.jpg,https://cf.cjdropshipping.com/20200815/2126261465771.jpg,https://cf.cjdropshipping.com/20200815/1885062424759.jpg,https://cf.cjdropshipping.com/20200815/5174623216464.jpg,https://cf.cjdropshipping.com/20200815/2963734965611.jpg,https://cf.cjdropshipping.com/20200815/1570377892509.jpg,https://cf.cjdropshipping.com/20200815/1256395175032.jpg,https://cf.cjdropshipping.com/20200815/3487517152974.jpg,https://cf.cjdropshipping.com/20200815/1988759026450.jpg,https://cf.cjdropshipping.com/20200815/5661968830548.jpg,https://cf.cjdropshipping.com/20200815/1110028528400.jpg,https://cf.cjdropshipping.com/20200815/935280742390.jpg,https://cf.cjdropshipping.com/20200815/827411496832.jpg,https://cf.cjdropshipping.com/20200815/3905396648946.jpg,https://cf.cjdropshipping.com/20200815/1807094612890.jpg,https://cf.cjdropshipping.com/20200815/832079616682.jpg,https://cf.cjdropshipping.com/20200815/344908446477.png,https://cf.cjdropshipping.com/20200815/217390828681.jpg,https://cf.cjdropshipping.com/20200815/1878864670836.png,https://cf.cjdropshipping.com/20200815/184482192613.jpg,https://cf.cjdropshipping.com/20200815/1142506019513.jpg,https://cf.cjdropshipping.com/20200815/1780531425430.jpg'''
    input_txt = 'https://cf.cjdropshipping.com/20200815/1586159702191.jpg'
    final_result = asyncio.run(process_images(input_txt))
    print("\n🖼️ Processed Image URLs:\n")
    print(final_result)
