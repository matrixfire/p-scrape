import json
import os
import asyncio
import logging
from typing import Dict, Any, List
from config import get_scraped_mongodb_config
from scrape_product_list_async import scrape_multiple_urls, init_mongo_scraped, TaskTracker
from pymongo.collection import Collection

# ========== Logging setup ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_filtered_categories() -> List[Dict[str, str]]:
    """Load categories from filtered_categories.json"""
    try:
        with open('filtered_categories.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("filtered_categories.json not found!")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing filtered_categories.json: {e}")
        return []


def update_temp_json(category_item: Dict[str, str]) -> None:
    """Update temp.json with a single category item"""
    temp_data = [category_item]
    with open('temp.json', 'w', encoding='utf-8') as f:
        json.dump(temp_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Updated temp.json with category: {category_item['name']}")


def update_config_collection_name(category_name: str) -> None:
    """Update the SCRAPED_COLLECTION_NAME in config.py"""
    try:
        with open('config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the SCRAPED_COLLECTION_NAME line
        import re
        pattern = r"SCRAPED_COLLECTION_NAME = os\.getenv\('SCRAPED_COLLECTION_NAME', '[^']*'\)"
        replacement = f"SCRAPED_COLLECTION_NAME = os.getenv('SCRAPED_COLLECTION_NAME', '{category_name}')"
        
        updated_content = re.sub(pattern, replacement, content)
        
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logger.info(f"Updated config.py SCRAPED_COLLECTION_NAME to: {category_name}")
        
    except Exception as e:
        logger.error(f"Error updating config.py: {e}")


def get_progress_file(category_name: str) -> str:
    """Generate progress file name for each category"""
    return f"progress_{category_name.replace(' ', '_').replace('/', '_')}.json"


async def process_single_category(category_item: Dict[str, str], max_concurrent_details: int = 3) -> bool:
    """Process a single category item"""
    category_name = category_item['name']
    category_url = category_item['url']
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing category: {category_name}")
    logger.info(f"URL: {category_url}")
    logger.info(f"{'='*60}\n")
    
    try:
        # Step 1: Update temp.json with current category
        update_temp_json(category_item)
        
        # Step 2: Update config.py with new collection name
        update_config_collection_name(category_name)
        
        # Step 3: Initialize MongoDB collection with new name
        collection = init_mongo_scraped()
        if not collection:
            logger.error(f"Failed to initialize MongoDB collection for {category_name}")
            return False
        
        # Step 4: Create task tracker for this category
        progress_file = get_progress_file(category_name)
        tracker = TaskTracker([category_item], id_key='url', progress_file=progress_file)
        
        # Step 5: Prepare URLs for scraping
        urls = [(category_name, category_url)]
        
        # Step 6: Run the scraping process
        logger.info(f"Starting scraping for category: {category_name}")
        all_products = await scrape_multiple_urls(
            urls=urls,
            collection=collection,
            tracker=tracker,
            max_concurrent_details=max_concurrent_details
        )
        
        logger.info(f"Completed scraping for {category_name}. Total products: {len(all_products)}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing category {category_name}: {e}")
        return False


async def bootstrap_scraper(max_concurrent_details: int = 3, start_index: int = 0):
    """Main bootstrap function to process all categories"""
    categories = load_filtered_categories()
    
    if not categories:
        logger.error("No categories found to process!")
        return
    
    logger.info(f"Loaded {len(categories)} categories from filtered_categories.json")
    logger.info(f"Starting from index: {start_index}")
    
    successful_categories = []
    failed_categories = []
    
    for i, category_item in enumerate(categories[start_index:], start=start_index):
        logger.info(f"\nProcessing category {i+1}/{len(categories)}: {category_item['name']}")
        
        success = await process_single_category(category_item, max_concurrent_details)
        
        if success:
            successful_categories.append(category_item['name'])
        else:
            failed_categories.append(category_item['name'])
        
        # Add a delay between categories to avoid overwhelming the server
        if i < len(categories) - 1:  # Don't sleep after the last category
            delay = 5  # 5 seconds delay between categories
            logger.info(f"Waiting {delay} seconds before next category...")
            await asyncio.sleep(delay)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SCRAPING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total categories processed: {len(categories)}")
    logger.info(f"Successful: {len(successful_categories)}")
    logger.info(f"Failed: {len(failed_categories)}")
    
    if successful_categories:
        logger.info(f"Successful categories: {', '.join(successful_categories)}")
    
    if failed_categories:
        logger.info(f"Failed categories: {', '.join(failed_categories)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Bootstrap scraper for processing categories')
    parser.add_argument('--start-index', type=int, default=0, 
                       help='Start processing from this index (default: 0)')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum concurrent detail page scrapes (default: 3)')
    
    args = parser.parse_args()
    
    logger.info("Starting bootstrap scraper...")
    asyncio.run(bootstrap_scraper(
        max_concurrent_details=args.max_concurrent,
        start_index=args.start_index
    )) 