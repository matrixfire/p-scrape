import threading
import traceback
import mysql.connector
import datetime
from handle_imgs import process_images
import asyncio

# Thread-safe database handler with connection retry and error handling
class DatabaseHandler:
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        self.mutex = threading.Lock()
        self.connect()

    def connect(self):
        self.conn = mysql.connector.connect(**self.db_config)
        self.cursor = self.conn.cursor()

    def reconnect_if_needed(self, error):
        if 'Lost connection to MySQL server during query' in str(error):
            self.connect()
            return True
        return False

    def commit(self):
        self.conn.commit()

    def execute(self, query):
        with self.mutex:
            try:
                self.cursor.execute(query)
                self.commit()
            except Exception as e:
                if not self.reconnect_if_needed(e):
                    raise e
                self.cursor.execute(query)
                self.commit()

    def escape_value(self, val):
        if val is None:
            return 'NULL'
        if isinstance(val, (int, float)):
            return str(val)
        return "'" + str(val).replace("'", "''") + "'"

    def build_insert_query(self, table_name, data):
        keys = [k for k in data if k and data[k] != '']
        values = [self.escape_value(data[k]) for k in keys]
        keys_str = ', '.join(f'`{k}`' for k in keys)
        values_str = ', '.join(values)
        return f"INSERT IGNORE INTO {table_name} ({keys_str}) VALUES ({values_str});"

    def insert(self, table_name, data):
        query = self.build_insert_query(table_name, data)
        print(f"[DEBUG] Insert query: {query}")
        try:
            self.execute(query)
        except Exception as e:
            if 'Duplicate entry' in str(e):
                print('[INFO] Duplicate entry ignored.')
                return 0
            if 'Data too long for column' in str(e) and 'main_img' in data:
                with open('ma.txt', 'w', encoding='utf-8') as f:
                    f.write(data.get('main_img', '') + '\n')
            traceback.print_exc()

    def update_stock_price(self, data):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['update_time'] = now
        query = (
            f"UPDATE pallet_stock_price SET "
            f"price = '{data['price']}', "
            f"stock = '{data['stock']}', "
            f"update_time = '{data['update_time']}' "
            f"WHERE sku = '{data['sku']}';"
        )
        try:
            self.execute(query)
        except Exception as e:
            if 'Duplicate entry' in str(e):
                print('[INFO] Duplicate entry on update.')
                return 0
            traceback.print_exc()
            print(query)

    def insert_many(self, table_name, data_list):
        if not data_list:
            return

        # Use the full set of fields for pallet_stock_price
        if table_name == 'pallet_stock_price':
            from export_to_db import TABLE2_FIELDS
            keys = TABLE2_FIELDS
        else:
            keys = [k for k in data_list[0].keys()]

        keys_str = ', '.join(f'`{k}`' for k in keys)

        values_str_list = []
        for data in data_list:
            values = [self.escape_value(data.get(k)) for k in keys]
            values_str = '(' + ', '.join(values) + ')'
            values_str_list.append(values_str)

        query = f"INSERT IGNORE INTO {table_name} ({keys_str}) VALUES {', '.join(values_str_list)};"
        print(f"[DEBUG] Multi-row Insert Query:\n{query[:500]}...")  # truncate for long queries

        try:
            self.execute(query)
        except Exception as e:
            print("[ERROR] Bulk insert failed.")
            traceback.print_exc()




# Configuration and shared instance
db_config = {
    "host": "gz-cdb-qex076ap.sql.tencentcdb.com",
    "user": "root",
    "password": "shgj123456",
    "database": "rpa",
    "port": 28745,
}

db_handler = DatabaseHandler(db_config)

# Fields list
lis_en = [
    'sku','id','default_product_name_en','multi_product_name_es','default_product_desc_en',
    'multi_product_desc_es','main_img','bg_img','weight','weight_unit',
    'length','width','height','length_unit','color','attribute','category'
]

TABLE1_FIELDS = ['sku','id','default_product_name_en','multi_product_name_es',
'default_product_desc_en','multi_product_desc_es','main_img','bg_img','weight',
'weight_unit','length','width','height','length_unit','color','attribute','category', 'size', 'country']


def insert_product_data(dic: dict):
    data = {k: dic[k] for k in TABLE1_FIELDS if k in dic and dic[k] not in [None, '']}
    db_handler.insert('pallet_product_data', data)

def insert_stock_price(dic_p: dict):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dic_p['update_time'] = now
    data = {k: v for k, v in dic_p.items() if k and v != ''}
    db_handler.insert('pallet_stock_price', data)

def update_stock_price(dic_p: dict):
    db_handler.update_stock_price(dic_p)

def query_product_data(limit: int = 3) -> list[dict]:
    if db_handler.cursor is None:
        return []
    query = f"SELECT * FROM pallet_product_data LIMIT {limit};"
    db_handler.cursor.execute(query)
    results = db_handler.cursor.fetchall()
    columns = [desc[0] for desc in db_handler.cursor.description] if db_handler.cursor.description else []
    return [dict(zip(columns, row)) for row in results] if results and columns else []

def query_stock_price(limit: int = 3) -> list[dict]:
    if db_handler.cursor is None:
        return []
    query = f"SELECT * FROM pallet_stock_price LIMIT {limit};"
    db_handler.cursor.execute(query)
    results = db_handler.cursor.fetchall()
    columns = [desc[0] for desc in db_handler.cursor.description] if db_handler.cursor.description else []
    return [dict(zip(columns, row)) for row in results] if results and columns else []


def insert_many_product_data(rows: list[dict]):
    if not rows:
        return
    data_list = [
        {k: row[k] for k in TABLE1_FIELDS if k in row and row[k] not in [None, '']}
        for row in rows
    ]
    db_handler.insert_many('pallet_product_data', data_list)


def insert_many_stock_price(rows: list[dict]):
    if not rows:
        return
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data_list = []
    for row in rows:
        row['update_time'] = now
        data = {k: v for k, v in row.items() if k and v != ''}
        data_list.append(data)
    db_handler.insert_many('pallet_stock_price', data_list)


def delete_products_by_categories(categories: list[str]):
    """Delete rows from pallet_product_data where category is in the provided list."""
    if not categories:
        print("[INFO] No categories provided for deletion.")
        return
    # Escape and quote each category for SQL
    escaped_cats = [db_handler.escape_value(cat) for cat in categories]
    cats_str = ', '.join(escaped_cats)
    query = f"DELETE FROM pallet_product_data WHERE category IN ({cats_str});"
    print(f"[DEBUG] Delete Query: {query}")
    try:
        db_handler.execute(query)
        print(f"[INFO] Deleted rows where category in {categories}")
    except Exception as e:
        print(f"[ERROR] Failed to delete rows: {e}")


def img_handle(input_txt: str) -> str:
    # Process the image and return a new URL or base64, etc.
    return asyncio.run(process_images(input_txt))




def process_and_update_images(categories: list[str]):
    if not categories:
        print("[INFO] No categories provided.")
        return

    for category in categories:
        try:
            # Step 1: Fetch records for the current category
            query = f"""
                SELECT id, main_img, bg_img 
                FROM pallet_product_data 
                WHERE category = {db_handler.escape_value(category)};
            """
            db_handler.cursor.execute(query)
            results = db_handler.cursor.fetchall()
            columns = [desc[0] for desc in db_handler.cursor.description]
            records = [dict(zip(columns, row)) for row in results]

            print(f"[INFO] Found {len(records)} records for category: {category}")

            # Step 2: Process and update each record
            for record in records:
                record_id = record['id']
                main_img_url = record.get('main_img')
                bg_img_url = record.get('bg_img')

                # Apply your image processing function
                new_main_img = img_handle(main_img_url) if main_img_url else None
                new_bg_img = img_handle(bg_img_url) if bg_img_url else None

                # Step 3: Build and execute UPDATE query
                update_fields = []
                if new_main_img is not None:
                    update_fields.append(f"main_img_upload = {db_handler.escape_value(new_main_img)}")
                if new_bg_img is not None:
                    update_fields.append(f"bg_img_upload = {db_handler.escape_value(new_bg_img)}")

                if update_fields:
                    update_query = (
                        f"UPDATE pallet_product_data SET {', '.join(update_fields)} "
                        f"WHERE id = {db_handler.escape_value(record_id)};"
                    )
                    db_handler.execute(update_query)
                    print(f"[INFO] Updated record ID {record_id}")

        except Exception as e:
            print(f"[ERROR] Failed to process category '{category}': {e}")
            traceback.print_exc()




if __name__ == "__main__":
    # qs = query_stock_price()
    # print(qs)
    # c_lt = ['围巾和披肩', '口罩', '腰带和腰带', '女士手套和连指手套', '女袜', '女帽', '紧身裤', '半身裙', '女士牛仔裤', '女短裤', '裤子和长裤', '阔腿裤', 'Ladies Short Sleeve', '女式吊带', '女士马甲', '女士短袖', '女士长袖', '衬衫和衬衣', '女性帽衫和运动衫', '连体裤', '连裤装', '女士礼服', '毛衣', '西服套装', '鸡尾酒礼服', '晚礼服', '伴娘礼服', '舞会礼服', '婚礼服', '花童礼服', '睡衣', '短裤', '内裤', '长袍', '睡衣套装', '四角裤', '长内衣裤', '男士长袖', '条纹类', '纯色类', '立体图案类', '印花类', '西服和西装外套', '男士毛衣', '真皮', '风衣', '男式衬衫', '男式夹克', '男士套装', '运动衫', '羊毛和混纺纱', '大衣', '羽绒服', '棒球帽', '轰炸机帽', '贝雷帽', '软呢帽', '女童内衣', '亲子装', '睡衣和长袍', '上衣和T恤', '套装', '礼服', '球衣', '户外短裤', '夹克', '裤子', '骑行服', '儿童鞋', '男童鞋', '女童鞋', '跑鞋', '舞蹈鞋', '滑板鞋', '远足鞋', '足球鞋', '篮球鞋']
    # delete_products_by_categories(c_lt)
    cs = ['阔腿裤']
    process_and_update_images(cs)