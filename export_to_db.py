import logging
from pymongo import MongoClient
from config import get_scraped_db_config
from utils import flatten_dict
import time
from db_handler import insert_product_data, insert_stock_price, update_stock_price, insert_many_product_data, insert_many_stock_price
from typing import Dict, Any

from typing import Optional, Any, List
from pymongo.collection import Collection


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def connect_to_mongodb() -> Optional[Collection]:
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


def fetch_and_flatten_data(collection: Collection) -> List[dict]:
    """Fetch all documents from MongoDB and flatten them using flatten_dict"""
    try:
        documents = list(collection.find({}))
        logger.info(f"Fetched {len(documents)} documents from MongoDB")
        flattened_data: List[dict] = []
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

TABLE1_FIELDS = ['sku','id','default_product_name_en','multi_product_name_es',
'default_product_desc_en','multi_product_desc_es','main_img','bg_img','weight',
'weight_unit','length','width','height','length_unit','color','attribute','category']


# For insert_stock_price, map to lis_en2
TABLE2_FIELDS = ['sku', 'id', 'stock', 'price', 'status', 
'update_time', 'stock2', 'currency', 'country',
'color']




# Mapping from flattened_data keys to lis_en keys
MONGO_TO_MYSQL_MAP_T1 = {
    'product_id': 'sku',
    'sku': 'id',
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
    'currency': 'currency',
    'factoryInventory': 'stock'
}



MONGO_TO_MYSQL_MAP_T2 = {
    'product_id': 'sku',
    'sku': 'id',
    'cjInventory': 'stock2',
    'factoryInventory': 'stock',
    'price': 'price',
    'status': 'status',
    'currency': 'currency',
    'country': 'country'
}



def build_attribute(row):
    # Combine 产品属性 and 材料 keys if present
    attr = []
    if '产品属性' in row and row['产品属性']:
        attr.append(str(row['产品属性']))
    if '材料' in row and row['材料']:
        attr.append(str(row['材料']))
    return ','.join(attr) if attr else None



def map_flattened_to_table1(row: Dict[str, Any]) -> Dict[str, Any]:
    mapped: Dict[str, Any] = {}
    for k in TABLE1_FIELDS:
        if k == 'attribute':
            mapped[k] = build_attribute(row)
        elif k == 'bg_img':
            mapped[k] = row.get('bg_img')
        else:
            # Find the mongo key for this lis_en key
            mongo_key: str | None = None
            for mk, lk in MONGO_TO_MYSQL_MAP_T1.items():
                if lk == k:
                    mongo_key = mk
                    break
            if mongo_key:
                mapped[k] = row.get(mongo_key)
            else:
                mapped[k] = row.get(k)
    return mapped



def map_flattened_to_table2(row):
    mapped = {}
    for k in TABLE2_FIELDS:
        # Find the mongo key for this lis_en2 key
        mongo_key = None
        for mk, lk in MONGO_TO_MYSQL_MAP_T2.items():
            if lk == k:
                mongo_key = mk
                break
        if mongo_key:
            mapped[k] = row.get(mongo_key)
        else:
            mapped[k] = row.get(k)
    return mapped


INSERT_MODE = 'both'  # Options: 'product', 'stock', 'both'



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
    for i, row in enumerate(flattened_data[:2]):
        mapped = map_flattened_to_table1(row)
        mapped_p = map_flattened_to_table2(row)
        print(f"\nMapped product record {i+1}: {mapped}\nMapped stock/price record {i+1}: {mapped_p}\n\n\n")
    success_count = 0
    fail_count = 0
    success_count_p = 0
    fail_count_p = 0
    print(f"length: {len(flattened_data)}"+'\n'*100)
    # for i, row in enumerate(flattened_data):
    #     # time.sleep(3)
    #     if INSERT_MODE in ('product', 'both'):
    #         mapped = map_flattened_to_table1(row)
    #         try:
    #             insert_product_data(mapped)
    #             logger.info(f"[product] Inserted row {i+1} into MySQL: {mapped.get('sku', mapped.get('id', 'N/A'))}")
    #             success_count += 1
    #         except Exception as e:
    #             logger.error(f"[product] Failed to insert row {i+1}: {e}\nData: {mapped}")
    #             fail_count += 1
    #     if INSERT_MODE in ('stock', 'both'):
    #         mapped_p = map_flattened_to_table2(row)
    #         try:
    #             insert_stock_price(mapped_p)
    #             logger.info(f"[stock] Inserted row {i+1} into MySQL: {mapped_p.get('sku', mapped_p.get('id', 'N/A'))}")
    #             success_count_p += 1
    #         except Exception as e:
    #             logger.error(f"[stock] Failed to insert row {i+1}: {e}\nData: {mapped_p}")
    #             fail_count_p += 1
    # if INSERT_MODE in ('product', 'both'):
    #     logger.info(f"[product] Inserted {success_count} rows into MySQL. Failed: {fail_count}")
    # if INSERT_MODE in ('stock', 'both'):
    #     logger.info(f"[stock] Inserted {success_count_p} rows into MySQL. Failed: {fail_count_p}")

    BATCH_SIZE = 100

    for i in range(0, len(flattened_data), BATCH_SIZE):
        batch = flattened_data[i:i+BATCH_SIZE]
        
        if INSERT_MODE in ('product', 'both'):
            try:
                product_batch = [map_flattened_to_table1(row) for row in batch]
                insert_many_product_data(product_batch)
                logger.info(f"[product] Batch {i//BATCH_SIZE+1}: Inserted {len(product_batch)} rows.")
            except Exception as e:
                logger.error(f"[product] Failed to insert batch: {e}")

        if INSERT_MODE in ('stock', 'both'):
            try:
                stock_batch = [map_flattened_to_table2(row) for row in batch]
                insert_many_stock_price(stock_batch)
                logger.info(f"[stock] Batch {i//BATCH_SIZE+1}: Inserted {len(stock_batch)} rows.")
            except Exception as e:
                logger.error(f"[stock] Failed to insert stock batch: {e}")


if __name__ == "__main__":
    main() 