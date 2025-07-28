#!/usr/bin/env python3
"""
Test script for bootstrap_scraper.py
This script tests the bootstrap functionality without actually running the full scraping process.
"""

import json
import asyncio
import logging
from bootstrap_scraper import load_filtered_categories, update_temp_json, update_config_collection_name

# ========== Logging setup ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_load_categories():
    """Test loading categories from filtered_categories.json"""
    logger.info("Testing load_filtered_categories()...")
    categories = load_filtered_categories()
    logger.info(f"Loaded {len(categories)} categories")
    
    if categories:
        logger.info(f"First category: {categories[0]}")
        logger.info(f"Last category: {categories[-1]}")
    
    return categories


def test_update_temp_json():
    """Test updating temp.json with a sample category"""
    logger.info("Testing update_temp_json()...")
    
    sample_category = {
        "name": "测试类别",
        "url": "https://www.cjdropshipping.com/list/wholesale-test-l-123456789.html"
    }
    
    update_temp_json(sample_category)
    
    # Verify the file was created correctly
    try:
        with open('temp.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"temp.json updated successfully: {data}")
        return True
    except Exception as e:
        logger.error(f"Error reading temp.json: {e}")
        return False


def test_update_config():
    """Test updating config.py with a new collection name"""
    logger.info("Testing update_config_collection_name()...")
    
    # Backup original config
    try:
        with open('config.py', 'r', encoding='utf-8') as f:
            original_config = f.read()
    except Exception as e:
        logger.error(f"Error reading config.py: {e}")
        return False
    
    # Test updating
    test_collection_name = "test_collection_运动夹克"
    update_config_collection_name(test_collection_name)
    
    # Verify the update
    try:
        with open('config.py', 'r', encoding='utf-8') as f:
            updated_config = f.read()
        
        if test_collection_name in updated_config:
            logger.info(f"Config updated successfully with collection name: {test_collection_name}")
        else:
            logger.error("Config update failed - collection name not found in file")
            return False
            
        # Restore original config
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(original_config)
        logger.info("Original config restored")
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying config update: {e}")
        # Try to restore original config
        try:
            with open('config.py', 'w', encoding='utf-8') as f:
                f.write(original_config)
        except:
            pass
        return False


async def test_single_category_processing():
    """Test processing a single category (without actual scraping)"""
    logger.info("Testing single category processing...")
    
    categories = load_filtered_categories()
    if not categories:
        logger.error("No categories found for testing")
        return False
    
    # Test with the first category
    test_category = categories[0]
    logger.info(f"Testing with category: {test_category['name']}")
    
    # Test temp.json update
    update_temp_json(test_category)
    
    # Test config update
    update_config_collection_name(test_category['name'])
    
    logger.info("Single category processing test completed successfully")
    return True


def main():
    """Run all tests"""
    logger.info("Starting bootstrap scraper tests...")
    
    # Test 1: Load categories
    categories = test_load_categories()
    if not categories:
        logger.error("Test failed: Could not load categories")
        return
    
    # Test 2: Update temp.json
    if not test_update_temp_json():
        logger.error("Test failed: Could not update temp.json")
        return
    
    # Test 3: Update config
    if not test_update_config():
        logger.error("Test failed: Could not update config.py")
        return
    
    # Test 4: Single category processing
    asyncio.run(test_single_category_processing())
    
    logger.info("All tests completed successfully!")
    logger.info("Bootstrap scraper is ready to use.")


if __name__ == "__main__":
    main() 