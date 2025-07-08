import threading
import traceback
import mysql.connector
import datetime

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
        return f"INSERT INTO {table_name} ({keys_str}) VALUES ({values_str});"

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


def insert_product_data(dic: dict):
    data = {k: dic[k] for k in lis_en if k in dic and dic[k] not in [None, '']}
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


if __name__ == "__main__":
    qs = query_stock_price()
    print(qs)
