import Levenshtein

COLOR_TRANSLATION = {
    "Black": "黑色",
    "White": "白色",
    "Beige": "米色",
    "Khaki": "卡其色",
    "Camel": "驼色",
    "Apricot": "杏色",
    "Dark Grey": "深灰色",
    "Grey": "灰色",
    "Light Grey": "浅灰色",
    "Silver": "银色",
    "Burgundy": "酒红色",
    "Maroon": "栗色",
    "Redwood": "红木色",
    "Red": "红色",
    "Rose Red": "玫瑰红色",
    "Rusty Rose": "枯玫瑰色",
    "Coral Orange": "珊瑚橙色",
    "Orange": "橙色",
    "Burnt Orange": "燃橙色",
    "Mustard Yellow": "芥末黄",
    "Yellow": "黄色",
    "Champagne": "香槟色",
    "Gold": "金色",
    "Mint Green": "薄荷绿",
    "Green": "绿色",
    "Dark Green": "墨绿色",
    "Olive Green": "橄榄绿",
    "Army Green": "军绿色",
    "Lime Green": "青柠色",
    "Navy Blue": "藏蓝色",
    "Royal Blue": "宝蓝色",
    "Blue": "蓝色",
    "Dusty Blue": "雾霾蓝",
    "Baby Blue": "淡蓝色",
    "Mint Blue": "薄荷蓝",
    "Cadet Blue": "青碧色",
    "Teal Blue": "水鸭蓝",
    "Purple": "紫色",
    "Red Violet": "中紫红色",
    "Violet Purple": "紫罗兰色",
    "Lilac Purple": "紫丁香色",
    "Mauve Purple": "淡紫色",
    "Dusty Purple": "浅灰紫",
    "Hot Pink": "玫红色",
    "Pink": "粉色",
    "Watermelon Pink": "西瓜粉色",
    "Coral Pink": "珊瑚粉",
    "Dusty Pink": "藕粉色",
    "Baby Pink": "浅粉色",
    "Chocolate Brown": "巧克力棕",
    "Bronze": "古铜色",
    "Rust Brown": "锈棕色",
    "Coffee Brown": "咖啡棕",
    "Mocha Brown": "摩卡棕",
    "Brown": "棕色",
    "Ginger": "姜色",
    "Multicolor": "多色",
    "Black and White": "黑白色",
    "Blue and White": "蓝白色",
    "Red and White": "红白色"
}    

def guess_closest_match(word, candidates):
    return min(candidates, key=lambda x: Levenshtein.distance(word, x))

def get_color_name(input_str):
    normalized_input = input_str.strip().lower()

    # Step 1: Exact match ignoring case
    for eng_color in COLOR_TRANSLATION:
        if normalized_input == eng_color.lower():
            return COLOR_TRANSLATION[eng_color]

    # Step 2: Length check
    if len(normalized_input) < 3:
        return "NOT FOUND"

    # Step 3: Split and check if any word matches any known color
    words = normalized_input.split()
    key_words_lower = [k.lower() for k in COLOR_TRANSLATION]

    # If more than 1 word and none match known keys, return "NOT FOUND"
    if len(words) > 1 and not any(word in key_words_lower for word in words):
        return "NOT FOUND"

    # Step 4: Fuzzy match using Levenshtein
    closest = guess_closest_match(input_str, COLOR_TRANSLATION.keys())
    guessed_value = COLOR_TRANSLATION[closest]

    # Cache the guess
    COLOR_TRANSLATION[input_str] = guessed_value

    return guessed_value
