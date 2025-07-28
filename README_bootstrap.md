# Bootstrap Scraper

This bootstrap script processes categories from `filtered_categories.json` one by one, automatically updating the configuration and running the scraping process for each category.

## How it works

1. **Loads categories**: Reads all categories from `filtered_categories.json`
2. **Processes one by one**: Takes each category item and:
   - Updates `temp.json` with the current category
   - Updates `config.py` to set `SCRAPED_COLLECTION_NAME` to the category name
   - Runs the scraping process for that category
   - Saves results to MongoDB with the category-specific collection name

## Files

- `bootstrap_scraper.py` - Main bootstrap script
- `test_bootstrap.py` - Test script to verify functionality
- `filtered_categories.json` - Source categories file
- `config.py` - Configuration file (will be modified during execution)
- `scrape_product_list_async.py` - Main scraping module

## Usage

### Basic usage
```bash
python bootstrap_scraper.py
```

### With custom parameters
```bash
# Start from a specific index (useful for resuming)
python bootstrap_scraper.py --start-index 5

# Set maximum concurrent detail page scrapes
python bootstrap_scraper.py --max-concurrent 5

# Combine both
python bootstrap_scraper.py --start-index 10 --max-concurrent 3
```

### Test the bootstrap functionality
```bash
python test_bootstrap.py
```

## Example workflow

1. **First category** (`运动夹克`):
   - Updates `temp.json` with the first category
   - Sets `SCRAPED_COLLECTION_NAME = '运动夹克'` in `config.py`
   - Runs scraping for that category
   - Saves to MongoDB collection named `运动夹克`

2. **Second category** (`羊毛混纺`):
   - Updates `temp.json` with the second category
   - Sets `SCRAPED_COLLECTION_NAME = '羊毛混纺'` in `config.py`
   - Runs scraping for that category
   - Saves to MongoDB collection named `羊毛混纺`

3. **Continues** for all categories...

## Features

- **Progress tracking**: Each category gets its own progress file
- **Error handling**: Failed categories are logged and the process continues
- **Resume capability**: Use `--start-index` to resume from a specific category
- **Summary report**: Shows successful and failed categories at the end
- **Delay between categories**: 5-second delay to avoid overwhelming the server

## Configuration

The script automatically:
- Updates `temp.json` with each category
- Modifies `SCRAPED_COLLECTION_NAME` in `config.py`
- Creates category-specific progress files
- Initializes MongoDB collections with category names

## Output

- **MongoDB collections**: One collection per category (named after the category)
- **Progress files**: `progress_[category_name].json` for each category
- **Logs**: Detailed logging of the entire process
- **Summary**: Final report of successful and failed categories

## Error handling

- If a category fails, the script continues with the next category
- Failed categories are logged and reported at the end
- The process can be resumed using `--start-index`

## Dependencies

- `filtered_categories.json` - Must exist with category data
- `config.py` - Will be modified during execution
- `scrape_product_list_async.py` - Main scraping module
- All other dependencies from the original scraping project 