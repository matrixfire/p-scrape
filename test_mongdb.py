import requests
import datetime
from bs4 import BeautifulSoup
from pymongo.collection import Collection
from pymongo import MongoClient, errors
from typing import Optional, List, Dict, Any
from fake_useragent import UserAgent
from config import get_mongo_config

# ========== 配置 ==========
config = get_mongo_config()
MONGO_URI: str = config['MONGO_URI']
DB_NAME: str = config['DB_NAME']
COLLECTION_NAME: str = config['COLLECTION_NAME']
TARGET_URL: str = 'http://www.santostang.com/'

def get_headers() -> Dict[str, str]:
    ua = UserAgent()
    return {
        'User-Agent': ua.random
    }

# ========== 初始化 MongoDB ==========
def init_mongo() -> Optional[Collection]:
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print("✅ MongoDB connected.")
        return collection
    except errors.ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None

# ========== 获取网页内容 ==========
def fetch_page(url: str) -> Optional[str]:
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        print("✅ Page fetched successfully.")
        return response.text
    except requests.RequestException as e:
        print(f"❌ Error fetching page: {e}")
        return None

# ========== 解析网页并提取标题信息 ==========
def parse_articles(html: str) -> List[Dict[str, Any]]:
    try:
        soup = BeautifulSoup(html, "lxml")  # 不依赖 lxml
        title_list = soup.find_all("h1", class_="post-title")
        results: List[Dict[str, Any]] = []
        for each in title_list:
            a_tag = each.find("a")
            if a_tag and a_tag.get("href"):
                title = a_tag.text.strip()
                url = a_tag["href"]
                results.append({
                    "title": title,
                    "url": url,
                    "date": datetime.datetime.utcnow()
                })
        print(f"✅ Parsed {len(results)} articles.")
        return results
    except Exception as e:
        print(f"❌ Error parsing HTML: {e}")
        return []

# ========== 插入数据库（避免重复） ==========
def save_to_mongo(collection: Collection, articles: List[Dict[str, Any]]) -> None:
    for article in articles:
        if collection.find_one({"url": article["url"]}):
            print(f"⚠️ Already exists: {article['url']}")
        else:
            collection.insert_one(article)
            print(f"✅ Inserted: {article['title']}")

# ========== 主流程 ==========
def main() -> None:
    collection = init_mongo()
    if collection is None:
        return

    html = fetch_page(TARGET_URL)
    if not html:
        return

    articles = parse_articles(html)
    if articles:
        save_to_mongo(collection, articles)
    else:
        print("⚠️ No articles to insert.")

if __name__ == "__main__":
    main()




'''
import requests
import datetime
from bs4 import BeautifulSoup
from pymongo import MongoClient, errors

# ========== 配置 ==========
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'blog_database'
COLLECTION_NAME = 'blog'
TARGET_URL = 'http://www.santostang.com/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0'
}

# ========== 初始化 MongoDB ==========
def init_mongo():
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print("✅ MongoDB connected.")
        return collection
    except errors.ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None

# ========== 获取网页内容 ==========
def fetch_page(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        print("✅ Page fetched successfully.")
        return response.text
    except requests.RequestException as e:
        print(f"❌ Error fetching page: {e}")
        return None

# ========== 解析网页并提取标题信息 ==========
def parse_articles(html):
    try:
        soup = BeautifulSoup(html, "html.parser")  # 不依赖 lxml
        title_list = soup.find_all("h1", class_="post-title")
        results = []
        for each in title_list:
            a_tag = each.find("a")
            if a_tag and a_tag.get("href"):
                title = a_tag.text.strip()
                url = a_tag["href"]
                results.append({
                    "title": title,
                    "url": url,
                    "date": datetime.datetime.utcnow()
                })
        print(f"✅ Parsed {len(results)} articles.")
        return results
    except Exception as e:
        print(f"❌ Error parsing HTML: {e}")
        return []

# ========== 插入数据库（避免重复） ==========
def save_to_mongo(collection, articles):
    for article in articles:
        if collection.find_one({"url": article["url"]}):
            print(f"⚠️ Already exists: {article['url']}")
        else:
            collection.insert_one(article)
            print(f"✅ Inserted: {article['title']}")

# ========== 主流程 ==========
def main():
    collection = init_mongo()
    if collection is None:
        return

    html = fetch_page(TARGET_URL)
    if not html:
        return

    articles = parse_articles(html)
    if articles:
        save_to_mongo(collection, articles)
    else:
        print("⚠️ No articles to insert.")

if __name__ == "__main__":
    main()



'''