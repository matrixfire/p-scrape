import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
SCRAPED_DB_NAME = os.getenv('SCRAPED_DB_NAME', 'scraped_db_new')
SCRAPED_COLLECTION_NAME = os.getenv('SCRAPED_COLLECTION_NAME', 'products_tx')

def get_scraped_mongodb_config():
    return {
        'MONGO_URI': MONGO_URI,
        'DB_NAME': SCRAPED_DB_NAME,
        'COLLECTION_NAME': SCRAPED_COLLECTION_NAME
    }

db_config = {
    "host": "gz-cdb-qex076ap.sql.tencentcdb.com",
    "user": "root",
    "password": "shgj123456",
    "database": "rpa",
    # "database": "test",
    "port": 28745,
}

tasks_json = 'diff_cn_clothing_shoes.json'

cj_config = {
'cj_account': 'tychan@163.com',
'cj_password': 'Kumai666888!',
'country': 'CN'
}
