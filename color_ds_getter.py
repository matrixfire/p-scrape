import re
import requests
from typing import Dict, List

EN_COLORS = [
    "Black", "White", "Beige", "Khaki", "Camel", "Apricot", "Dark Grey", "Grey", "Light Grey", "Silver",
    "Burgundy", "Maroon", "Redwood", "Red", "Rose Red", "Rusty Rose", "Coral Orange", "Orange",
    "Burnt Orange", "Mustard Yellow", "Yellow", "Champagne", "Gold", "Mint Green", "Green", "Dark Green",
    "Olive Green", "Army Green", "Lime Green", "Navy Blue", "Royal Blue", "Blue", "Dusty Blue", "Baby Blue",
    "Mint Blue", "Cadet Blue", "Teal Blue", "Purple", "Red Violet", "Violet Purple", "Lilac Purple",
    "Mauve Purple", "Dusty Purple", "Hot Pink", "Pink", "Watermelon Pink", "Coral Pink", "Dusty Pink",
    "Baby Pink", "Chocolate Brown", "Bronze", "Rust Brown", "Coffee Brown", "Mocha Brown", "Brown", "Ginger",
    "Multicolor", "Black and White", "Blue and White", "Red and White"
]

CH_COLORS = [
    "黑色", "白色", "米色", "卡其色", "驼色", "杏色", "深灰色", "灰色", "浅灰色", "银色", "酒红色", "栗色",
    "红木色", "红色", "玫瑰红色", "枯玫瑰色", "珊瑚橙色", "橙色", "燃橙色", "芥末黄", "黄色", "香槟色",
    "金色", "薄荷绿", "绿色", "墨绿色", "橄榄绿", "军绿色", "青柠色", "藏蓝色", "宝蓝色", "蓝色", "雾霾蓝",
    "淡蓝色", "薄荷蓝", "青碧色", "水鸭蓝", "紫色", "中紫红色", "紫罗兰色", "紫丁香色", "淡紫色", "浅灰紫",
    "玫红色", "粉色", "西瓜粉色", "珊瑚粉", "藕粉色", "浅粉色", "巧克力棕", "古铜色", "锈棕色", "咖啡棕",
    "摩卡棕", "棕色", "姜色", "多色", "黑白色", "蓝白色", "红白色"
]

COLORS_FILE = '匹配颜色.txt'
API_URL = "http://43.138.243.218:3000/v1/chat/completions"
API_KEY = "sk-jYMnHWfEiFJDjpcFiB1TcVtvIxSAx1a267MzPxRjD3ShZcu8"


def load_color_mappings(filename: str) -> Dict[str, str]:
    mappings = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('_', 1)
                if len(parts) == 2:
                    key, val = parts
                    mappings[key] = val
    except FileNotFoundError:
        pass
    return mappings



def save_color_mapping(filename: str, original: str, mapped: str):
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{original}_{mapped}\n")


def fix_encoding(garbled_text: str) -> str:
    try:
        return bytes([ord(c) for c in garbled_text]).decode('utf-8')
    except UnicodeDecodeError:
        return "无法还原文本，可能使用了其他编码"


import requests
import json
import re

def fetch_closest_color2(query_color: str) -> str:
    # API_URL = "https://api.deepseek.com/v1/chat/completions"
    # API_KEY = "sk-your-api-key-here"  # 替换为实际API密钥
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-reasoner",  # 推荐使用推理专用模型
        "temperature": 0.3,
        "messages": [
            {
                "role": "system",
                "content": "你从给定的颜色列表中严格选择最接近用户描述的颜色。仅返回颜色名称，用**包裹"
            },
            {
                "role": "user",
                "content": f"目标颜色描述：'{query_color}'。候选颜色列表：{CH_COLORS}。直接返回最接近的颜色名称，不要解释。"
            }
        ]
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # 自动抛出HTTP错误
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # 优先提取**包裹内容，否则返回整个响应
        match = re.search(r'\*\*(.*?)\*\*', content)
        return match.group(1) if match else content
    
    except requests.exceptions.HTTPError as e:
        error_code = response.status_code
        if error_code == 401:
            return "错误：API密钥无效 [6](@ref)"
        elif error_code == 402:
            return "错误：账户余额不足 [6](@ref)"
        else:
            return f"API错误：{e}"
    
    except Exception as e:
        return f"处理失败：{str(e)}"



def fetch_closest_color(query_color: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": API_KEY
    }
    payload = {
        "model": "deepseek-r1",
        "temperature": 0.3,
        "stream": True,
        "messages": [
            {"role": "system", "content": "you help me choice one type"},
            {"role": "user", "content": f"需要判断的颜色是{query_color},从列表中的颜色{CH_COLORS}中返回一个颜色，最接近需要判断的颜色，结果两边加**,直接给出答案，不需要解释"}
        ]
    }

    response = requests.post(API_URL, headers=headers, json=payload, stream=True)
    response_text = ''.join(
        eval(chunk)['choices'][0]['delta']['content']
        for chunk in response.text.strip().strip('[DONE]').split('data: ') if chunk.strip()
    )
    result = fix_encoding(response_text)
    match = re.search(r'\*\*(.*?)\*\*', result)
    # return match.group(1) if match else "多色"
    print(result)
    return result


def map_color(input_color: str, en_colors: List[str], ch_colors: List[str], color_dict: Dict[str, str]) -> str:
    if input_color in en_colors:
        return ch_colors[en_colors.index(input_color)]
    elif input_color in color_dict:
        return color_dict[input_color]
    else:
        closest_color = fetch_closest_color2(input_color)
        save_color_mapping(COLORS_FILE, input_color, closest_color)
        color_dict[input_color] = closest_color
        return closest_color


if __name__ == "__main__":
    color_dict = load_color_mappings(COLORS_FILE)
    input_color = 'yello1'
    mapped_color = map_color(input_color, EN_COLORS, CH_COLORS, color_dict)
    print(mapped_color)
