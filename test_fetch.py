import requests
import json

url = "https://www.cjdropshipping.com/product-api/assign/batchUnionLogisticsFreightV355"

headers = {
    "accept": "application/json;charset=utf-8",
    "accept-language": "zh-CN,zh;q=0.9",
    "cj-area": "86057101",
    "content-type": "application/json;charset=UTF-8",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "token": "USR@CJ4234984@L0@CJ:af87feae2fd542c8935828cf282dc0791",
    "referer": "https://www.cjdropshipping.com/product/childrens-toddler-shoes-p-1812AC0A-35C1-46CA-B956-D496CABB1702.html"
}

# 读取 JSON 数据（强烈建议将 body 提取为独立 payload.json 文件）
with open("payload_t.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

response = requests.post(url, headers=headers, json=payload)
print(response.status_code)
print(response.json())
