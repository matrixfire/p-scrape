async def scrape_product_detail_page(context, product_url: str, semaphore: asyncio.Semaphore) -> Optional[str]:
    async with semaphore:
        logger.info(f"Scraping detail page: {product_url}")
        page = await context.new_page()
        try:
            await page.goto(product_url, timeout=30000)
            try:
                await page.wait_for_selector("div#description-description", timeout=15000)
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout: description not found for {product_url}")
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            desc_div = soup.find("div", id="description-description")
            if desc_div:
                desc_text = desc_div.get_text(separator='\n', strip=True)
                logger.info(f"\n========== Extracted description for {product_url} (first 20 chars): {desc_text[:20]} ==========\n")
                return desc_text
            else:
                logger.warning(f"No description found for {product_url}")
                return None
        except PlaywrightTimeoutError:
            logger.error(f"Timeout loading page: {product_url}")
            return None
        except PlaywrightError as e:
            logger.error(f"Playwright error for {product_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {product_url}: {e}")
            return None
        finally:
            try:
                await page.close()
            except Exception:
                pass
        # Optionally, add a small random sleep to reduce load
        await asyncio.sleep(random.uniform(0.2, 0.6))












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
            'ad_quantity': ad_quantity,
            'product_url': product_url,
            'product_id': product_id,
            'image_url': image_url
        }
        # logger.info(f"Scraped product: {product_data}")
        return product_data
    except Exception as e:
        logger.error(f"Error parsing product card: {e}")
        return None
