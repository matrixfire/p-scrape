import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
SCRAPED_DB_NAME = os.getenv('SCRAPED_DB_NAME', 'scraped_db')
SCRAPED_COLLECTION_NAME = os.getenv('SCRAPED_COLLECTION_NAME', 'products_us_t4_pet')

def get_scraped_db_config():
    return {
        'MONGO_URI': MONGO_URI,
        'DB_NAME': SCRAPED_DB_NAME,
        'COLLECTION_NAME': SCRAPED_COLLECTION_NAME
    } 