import threading
import traceback
import mysql.connector
import datetime


mutex = threading.Lock()


# 数据库配置，根据实际情况修改
db_config = {
    "host": "gz-cdb-qex076ap.sql.tencentcdb.com",
    "user": "root",
    "password": "shgj123456",
    "database": "rpa",
    "port":28745,
}
conn = mysql.connector.connect(**db_config)
# 创建游标对象
cursor = conn.cursor()
lis_en = ['sku','id','default_product_name_en','multi_product_name_es','default_product_desc_en','multi_product_desc_es','main_img','bg_img','weight','weight_unit','length','width','height','length_unit','color','attribute','category']
# lis_ch = ['货号','id','默认商品名称[en]','多语言商品名称[es]','默认商品描述[en]','多语言商品描述[es]','主图','副图','重量','重量单位','长','宽','高','长宽高单位','颜色','属性','种类']

def insertt(dic:dict):
    global cursor,conn
    dic_new = {}
    for i in dic:
        if i in lis_en and i is not None and i != '':
            dic_new[i] = dic[i]
    # Remove any None or empty string keys from dic_new
    dic_new = {k: v for k, v in dic_new.items() if k is not None and k != ''}
    k = list(dic_new.keys())
    k = [i for i in k]
    k_str = str(k).strip('[').strip(']').replace('"','`').replace("'", "`")
    def sql_value(val):
        if val is None:
            return 'NULL'
        if isinstance(val, (int, float)):
            return str(val)
        # Escape single quotes in strings
        return "'" + str(val).replace("'", "''") + "'"
    v = list(dic_new.values())
    v_str = ', '.join([sql_value(val) for val in v])
    query = f'''INSERT INTO pallet_product_data ({k_str})\n     VALUES ({v_str});'''
    print(f"[DEBUG] Insert keys: {k}")
    with mutex:
        try:
            s = cursor.execute(query)
        except Exception as e:
            print(f"[ERROR] Query failed: {query}")
            print(f"[ERROR] Keys: {k}")
            print(f"[ERROR] Values: {v}")
            if 'Lost connection to MySQL server during query' in str(e):
                conn = mysql.connector.connect(**db_config)
                # 创建游标对象
                cursor = conn.cursor()
                s = cursor.execute(query)
            else:
                if 'Duplicate entry' in str(e):
                    print('Duplicate')
                    return 0
                if 'Data too long for column' in  str(e):
                    with open('ma.txt','w',encoding='utf-8') as f:
                        f.write(dic.get('主图','')+'\n')
                traceback.print_exc()

        conn.commit()


def insertt_p(dic_p: dict):
    #sku id stock price
    global cursor, conn
    now = datetime.datetime.now()
    now = now.strftime('%Y-%m-%d %H:%M:%S')
    dic_p['update_time'] = now
    k = list(dic_p.keys())
    k = str(k).strip('[').strip(']').replace('\'', '`')
    v = list(dic_p.values())
    v = str(v).strip('[').strip(']')
    query = f'''INSERT INTO pallet_stock_price ({k})
     VALUES ({v});'''

    with mutex:
        try:
            s = cursor.execute(query)
        except Exception as e:
            if 'Lost connection to MySQL server during query' in str(e):
                conn = mysql.connector.connect(**db_config)
                # 创建游标对象
                cursor = conn.cursor()
                s = cursor.execute(query)
                conn.commit()
                return 0
            else:
                if 'Duplicate entry' in str(e):
                    return 0
                traceback.print_exc()
                print(query)

        conn.commit()


def update_p(dic_p:dict):
    global cursor,conn
    now = datetime.datetime.now()
    now = now.strftime('%Y-%m-%d %H:%M:%S')
    dic_p['update_time'] = now

    query = f'''UPDATE pallet_stock_price SET price = '{dic_p['price']}', stock = '{dic_p['stock']}', update_time = '{dic_p['update_time']}' where sku ='{dic_p['sku']}' ;'''
    with mutex:

        try:
            s = cursor.execute(query)
        except Exception as e:

            if 'Lost connection to MySQL server during query' in str(e):
                conn = mysql.connector.connect(**db_config)
                # 创建游标对象
                cursor = conn.cursor()
                s = cursor.execute(query)
                conn.commit()
                print(cursor.fetchall())
                return 0
            else:
                if 'Duplicate entry' in str(e):
                    return 0
                traceback.print_exc()
                print(query)

        conn.commit()



    #query = 'DROP TABLE IF EXISTS appoint;'





if __name__ == "__main__":
   pass