import logging
from pymongo import MongoClient
from config import get_scraped_db_config
from utils import flatten_dict
from mysqll3 import insertt, insertt_p

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def connect_to_mongodb():
    """Connect to MongoDB using the scraped database configuration"""
    config = get_scraped_db_config()
    try:
        client = MongoClient(config['MONGO_URI'])
        db = client[config['DB_NAME']]
        collection = db[config['COLLECTION_NAME']]
        logger.info(f"Connected to MongoDB: {config['DB_NAME']}.{config['COLLECTION_NAME']}")
        return collection
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None

def fetch_and_flatten_data(collection):
    """Fetch all documents from MongoDB and flatten them using flatten_dict"""
    try:
        documents = list(collection.find({}))
        logger.info(f"Fetched {len(documents)} documents from MongoDB")
        flattened_data = []
        for doc in documents:
            doc['_id'] = str(doc['_id'])
            if 'variants' in doc and isinstance(doc['variants'], list):
                flattened_docs = flatten_dict(doc, 'variants')
                flattened_data.extend(flattened_docs)
                logger.info(f"Flattened document with {len(doc['variants'])} variants")
            else:
                flattened_data.append(doc)
                logger.info("Document has no variants, added as is")
        logger.info(f"Total flattened records: {len(flattened_data)}")
        return flattened_data
    except Exception as e:
        logger.error(f"Error fetching and flattening data: {e}")
        return []

# Mapping from flattened_data keys to lis_en keys
MONGO_TO_MYSQL_MAP = {
    'sku': 'sku',
    'product_id': 'id',
    'name': 'default_product_name_en',
    'multi_product_name_es': 'multi_product_name_es',
    'description': 'default_product_desc_en',
    'multi_product_desc_es': 'multi_product_desc_es',
    'image_url': 'main_img',
    'weight': 'weight',
    'weight_unit': 'weight_unit',
    'length': 'length',
    'width': 'width',
    'height': 'height',
    'size_unit': 'length_unit',
    'color': 'color',
    'category': 'category',
    # 'attribute' will be handled specially
    # 'bg_img' will use image_url as fallback
}

LIS_EN = ['sku','id','default_product_name_en','multi_product_name_es','default_product_desc_en','multi_product_desc_es','main_img','bg_img','weight','weight_unit','length','width','height','length_unit','color','attribute','category']

def build_attribute(row):
    # Combine 产品属性 and 材料 keys if present
    attr = []
    if '产品属性' in row and row['产品属性']:
        attr.append(str(row['产品属性']))
    if '材料' in row and row['材料']:
        attr.append(str(row['材料']))
    return ','.join(attr) if attr else None

def map_flattened_to_lis_en(row):
    mapped = {}
    for k in LIS_EN:
        if k == 'attribute':
            mapped[k] = build_attribute(row)
        elif k == 'bg_img':
            mapped[k] = row.get('image_url')
        else:
            # Find the mongo key for this lis_en key
            mongo_key = None
            for mk, lk in MONGO_TO_MYSQL_MAP.items():
                if lk == k:
                    mongo_key = mk
                    break
            if mongo_key:
                mapped[k] = row.get(mongo_key)
            else:
                mapped[k] = row.get(k)
    return mapped

def main():
    logger.info("Starting MongoDB to MySQL export process...")
    collection = connect_to_mongodb()
    if collection is None:
        logger.error("Failed to connect to MongoDB. Exiting.")
        return
    flattened_data = fetch_and_flatten_data(collection)
    if not flattened_data:
        logger.error("No data retrieved. Exiting.")
        return
    # Map and print the first 3 mapped records for debugging
    for i, row in enumerate(flattened_data[:3]):
        mapped = map_flattened_to_lis_en(row)
        print(f"\nMapped record {i+1}: {mapped}\n\n\n")
    success_count = 0
    fail_count = 0
    for i, row in enumerate(flattened_data):
        mapped = map_flattened_to_lis_en(row)
        try:
            insertt(mapped)
            logger.info(f"Inserted row {i+1} into MySQL: {mapped.get('sku', mapped.get('id', 'N/A'))}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to insert row {i+1}: {e}\nData: {mapped}")
            fail_count += 1
    logger.info(f"Inserted {success_count} rows into MySQL. Failed: {fail_count}")

if __name__ == "__main__":
    main() 