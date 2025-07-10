import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'blog_database')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'blog4')

SCRAPED_DB_NAME = os.getenv('SCRAPED_DB_NAME', 'scraped_db')
# SCRAPED_COLLECTION_NAME = os.getenv('SCRAPED_COLLECTION_NAME', 'products')
SCRAPED_COLLECTION_NAME = os.getenv('SCRAPED_COLLECTION_NAME', 'products_2')

def get_mongo_config():
    return {
        'MONGO_URI': MONGO_URI,
        'DB_NAME': DB_NAME,
        'COLLECTION_NAME': COLLECTION_NAME
    }

def get_scraped_db_config():
    return {
        'MONGO_URI': MONGO_URI,
        'DB_NAME': SCRAPED_DB_NAME,
        'COLLECTION_NAME': SCRAPED_COLLECTION_NAME
    } 