import pandas as pd
from pymongo import MongoClient
from config import get_scraped_mongodb_config
from utils import flatten_dict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def connect_to_mongodb():
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

def fetch_and_flatten_data(collection):
    """Fetch all documents from MongoDB and flatten them using flatten_dict"""
    try:
        # Fetch all documents from the collection
        documents = list(collection.find({}))
        logger.info(f"Fetched {len(documents)} documents from MongoDB")
        
        # Flatten each document using the flatten_dict function
        flattened_data = []
        for doc in documents:
            # Convert MongoDB ObjectId to string for JSON serialization
            doc['_id'] = str(doc['_id'])
            
            # Check if the document has 'variants' field
            if 'variants' in doc and isinstance(doc['variants'], list):
                # Use flatten_dict to flatten the document
                flattened_docs = flatten_dict(doc, 'variants')
                # flattened_docs = list(map(lambda d: {**d, "product_id": f'{d["sku"]}_{d["product_id"]}'}, flattened_docs))
                flattened_data.extend(flattened_docs)
                logger.info(f"Flattened document with {len(doc['variants'])} variants")
            else:
                # If no variants, add the document as is
                flattened_data.append(doc)
                logger.info("Document has no variants, added as is")
        
        logger.info(f"Total flattened records: {len(flattened_data)}")
        return flattened_data
    
    except Exception as e:
        logger.error(f"Error fetching and flattening data: {e}")
        return []

def export_to_excel(data, filename="products_export.xlsx"):
    """Export the flattened data to an Excel file using pandas"""
    try:
        if not data:
            logger.warning("No data to export")
            return False
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data)
        
        # Export to Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        logger.info(f"Successfully exported {len(df)} records to {filename}")
        
        # Log some basic statistics
        logger.info(f"Excel file columns: {list(df.columns)}")
        logger.info(f"DataFrame shape: {df.shape}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error exporting to Excel: {e}")
        return False

def main():
    """Main function to run the export process"""
    logger.info("Starting MongoDB to Excel export process...")
    
    # Connect to MongoDB
    collection = connect_to_mongodb()
    if collection is None:
        logger.error("Failed to connect to MongoDB. Exiting.")
        return
    
    # Fetch and flatten data
    flattened_data = fetch_and_flatten_data(collection)
    if not flattened_data:
        logger.error("No data retrieved. Exiting.")
        return
    
    # Export to Excel
    success = export_to_excel(flattened_data)
    
    if success:
        logger.info("Export process completed successfully!")
    else:
        logger.error("Export process failed!")

if __name__ == "__main__":
    main() 