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