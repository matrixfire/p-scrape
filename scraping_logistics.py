import requests
import json

url = "https://www.cjdropshipping.com/product-api/assign/batchUnionLogisticsFreightV355"

headers = {
    "accept": "application/json;charset=utf-8",
    "accept-language": "zh-CN,zh;q=0.9",
    "cj-area": "86057101",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://www.cjdropshipping.com",
    "referer": "https://www.cjdropshipping.com/product/cooling-blankets-pure-color-summer-quilt-plain-summer-cool-quilt-compressible-air-conditioning-quilt-quilt-blanket-p-01E333BC-92ED-440E-A783-E10F319B3273.html?tiktokUsZone=1&warehouse=CN",
    "token": "USR@CJ4234984@L0@CJ:caf19533fd6c476897a99e580d53af291",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}


payload = [
    {
    "countryCode": "MX",
    "customerCode": "1916507382012452864",
    "height": 5,
    "length": 35,
    "pid": "01E333BC-92ED-440E-A783-E10F319B3273",
    "platform": "shopify",
    "productType": "0",
    "property": "Clothes",
    "quantity": 1,
    "sku": "CJJJJFCS00602-Sky Blue-1.8x2.2m",
    "skus": ["CJJJJFCS00602-Sky Blue-1.8x2.2m"],
    "startCountryCode": "CN",
    "volume": 7000,
    "weight": 790,
    "width": 40
},
{
    "countryCode": "MX",
    "customerCode": "1916507382012452864",
    "height": 5,
    "length": 35,
    "pid": "01E333BC-92ED-440E-A783-E10F319B3273",
    "platform": "shopify",
    "productType": "0",
    "property": "Clothes",
    "quantity": 1,
    "sku": "CJJJJFCS00602-Sky Blue-1.8x2.2m",
    "skus": ["CJJJJFCS00602-Sky Blue-1.8x2.2m"],
    "startCountryCode": "CN",
    "volume": 7000,
    "weight": 1790,
    "width": 40
},
{
    "countryCode": "MX",
    "customerCode": "1916507382012452864",
    "height": 5,
    "length": 35,
    "pid": "01E333BC-92ED-440E-A783-E10F319B3273",
    "platform": "shopify",
    "productType": "0",
    "property": "Clothes",
    "quantity": 1,
    "sku": "CJJJJFCS00602-Water green-2x2.3m",
    "skus": ["CJJJJFCS00602-Water green-2x2.3m"],
    "startCountryCode": "CN",
    "volume": 7000,
    "weight": 1190,
    "width": 40
}

]

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.status_code)
data = response.json()


prices = [item.get("price") for item in data.get("data", [])]
print(prices)