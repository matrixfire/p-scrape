import logging
from pymongo import MongoClient
from config import get_scraped_mongodb_config
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
    config = get_scraped_mongodb_config()
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
'weight_unit','length','width','height','length_unit','color','attribute','category', 'size', 'country', 'other_data']


# For insert_stock_price, map to lis_en2
TABLE2_FIELDS = ['sku', 'id', 'stock', 'price', 'status', 
'update_time', 'stock2', 'currency', 'country',
'color', 'shipping_fee', 'delivery_time', 'shipping_method']




# Mapping from lis_en keys to flattened_data keys (MySQL to MongoDB)
MYSQL_TO_MONGO_MAP_T1 = {
    'sku': 'product_id',
    'id': 'sku',
    'default_product_name_en': 'name',
    'multi_product_name_es': 'multi_product_name_es',
    'default_product_desc_en': 'description',
    'multi_product_desc_es': 'multi_product_desc_es',
    'main_img': 'variant_image',
    'weight': 'weight',
    'weight_unit': 'weight_unit',
    'length': 'length',
    'width': 'width',
    'height': 'height',
    'length_unit': 'size_unit',
    'color': 'color',
    'category': 'category',
    'currency': 'currency',
    'stock': 'factoryInventory',
    'size': 'size',
    'country': 'country',
    'other_data': 'description'
}

MYSQL_TO_MONGO_MAP_T2 = {
    'sku': 'product_id',
    'id': 'sku',
    'stock2': 'cjInventory',
    'stock': 'factoryInventory',
    'price': 'price',
    'status': 'status',
    'currency': 'currency',
    'country': 'country',
    'shipping_fee': 'shipping_fee',
    'delivery_time': 'delivery_time',
    'shipping_method': 'shipping_method',
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
    for mysql_field in TABLE1_FIELDS:
        if mysql_field == 'attribute':
            mapped[mysql_field] = build_attribute(row)
        elif mysql_field == 'bg_img':
            mapped[mysql_field] = row.get('bg_img')
        else:
            mongo_key = MYSQL_TO_MONGO_MAP_T1.get(mysql_field, mysql_field)
            mapped[mysql_field] = row.get(mongo_key)
    return mapped



def map_flattened_to_table2(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps a flattened MongoDB document (row) to the MySQL table2 schema.

    Args:
        row (Dict[str, Any]): The flattened MongoDB document.

    Returns:
        Dict[str, Any]: A dictionary with keys matching TABLE2_FIELDS and values mapped from the MongoDB document.
    """
    mapped: Dict[str, Any] = {}
    for mysql_field in TABLE2_FIELDS:
        mongo_key = MYSQL_TO_MONGO_MAP_T2.get(mysql_field, mysql_field)
        mapped[mysql_field] = row.get(mongo_key)
    # Debug print for shipping_fee
    # print(f"[DEBUG] shipping_fee in mapped row: {mapped.get('shipping_fee')}")
    return mapped


INSERT_MODE = 'both'  # Options: 'product', 'stock', 'both'



def main():
    """
    Main function to export data from MongoDB to MySQL.
    Steps:
    1. Connect to MongoDB.
    2. Fetch and flatten data from MongoDB.
    3. Map and print sample records for debugging.
    4. Batch insert mapped data into MySQL tables.
    """
    logger.info("Starting MongoDB to MySQL export process...")
    print("[DEBUG] Connecting to MongoDB...")
    collection = connect_to_mongodb()
    if collection is None:
        logger.error("Failed to connect to MongoDB. Exiting.")
        print("[DEBUG] MongoDB connection failed. Exiting.")
        return

    print("[DEBUG] Fetching and flattening data from MongoDB...")
    flattened_data = fetch_and_flatten_data(collection)
    if not flattened_data:
        logger.error("No data retrieved. Exiting.")
        print("[DEBUG] No data retrieved from MongoDB. Exiting.")
        return

    # Map and print the first 2 mapped records for debugging
    print("[DEBUG] Mapping and printing first 2 records for verification...")
    for idx, flattened_row in enumerate(flattened_data[:2]):
        mapped_product = map_flattened_to_table1(flattened_row)
        mapped_stock = map_flattened_to_table2(flattened_row)
        print(f"\nMapped product record {idx+1}: {mapped_product}\nMapped stock/price record {idx+1}: {mapped_stock}\n\n\n")

    print(f"[DEBUG] Total records to process: {len(flattened_data)}\n" + '\n'*2)

    BATCH_SIZE = 100
    print(f"[DEBUG] Inserting data in batches of {BATCH_SIZE}...")

    for batch_start in range(0, len(flattened_data), BATCH_SIZE):
        batch = flattened_data[batch_start:batch_start+BATCH_SIZE]
        print(f"[DEBUG] Processing batch {batch_start//BATCH_SIZE+1} (records {batch_start+1} to {batch_start+len(batch)})")
        
        if INSERT_MODE in ('product', 'both'):
            try:
                product_batch = [map_flattened_to_table1(flattened_row) for flattened_row in batch]
                print(f"[DEBUG] Inserting product batch of size {len(product_batch)}...")
                insert_many_product_data(product_batch)
                logger.info(f"[product] Batch {batch_start//BATCH_SIZE+1}: Inserted {len(product_batch)} rows.")
            except Exception as exc:
                logger.error(f"[product] Failed to insert batch: {exc}")
                print(f"[DEBUG] Exception during product batch insert: {exc}")

        if INSERT_MODE in ('stock', 'both'):
            try:
                stock_batch = [map_flattened_to_table2(flattened_row) for flattened_row in batch]
                print(f"[DEBUG] Inserting stock batch of size {len(stock_batch)}...")
                insert_many_stock_price(stock_batch)
                logger.info(f"[stock] Batch {batch_start//BATCH_SIZE+1}: Inserted {len(stock_batch)} rows.")
            except Exception as exc:
                logger.error(f"[stock] Failed to insert stock batch: {exc}")
                print(f"[DEBUG] Exception during stock batch insert: {exc}")


if __name__ == "__main__":
    main() 