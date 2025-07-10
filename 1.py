import re
import requests
en_col = ["Black", "White", "Beige", "Khaki", "Camel", "Apricot", "Dark Grey", "Grey", "Light Grey", "Silver",
              "Burgundy", "Maroon", "Redwood", "Red", "Rose Red", "Rusty Rose", "Coral Orange", "Orange",
              "Burnt Orange", "Mustard Yellow", "Yellow", "Champagne", "Gold", "Mint Green", "Green", "Dark Green",
              "Olive Green", "Army Green", "Lime Green", "Navy Blue", "Royal Blue", "Blue", "Dusty Blue", "Baby Blue",
              "Mint Blue", "Cadet Blue", "Teal Blue", "Purple", "Red Violet", "Violet Purple", "Lilac Purple",
              "Mauve Purple", "Dusty Purple", "Hot Pink", "Pink", "Watermelon Pink", "Coral Pink", "Dusty Pink",
              "Baby Pink", "Chocolate Brown", "Bronze", "Rust Brown", "Coffee Brown", "Mocha Brown", "Brown", "Ginger",
              "Multicolor", "Black and White", "Blue and White", "Red and White"]
ch_col = ["黑色", "白色", "米色", "卡其色", "驼色", "杏色", "深灰色", "灰色", "浅灰色", "银色", "酒红色", "栗色",
          "红木色", "红色", "玫瑰红色", "枯玫瑰色", "珊瑚橙色", "橙色", "燃橙色", "芥末黄", "黄色", "香槟色",
          "金色", "薄荷绿", "绿色", "墨绿色", "橄榄绿", "军绿色", "青柠色", "藏蓝色", "宝蓝色", "蓝色", "雾霾蓝",
          "淡蓝色", "薄荷蓝", "青碧色", "水鸭蓝", "紫色", "中紫红色", "紫罗兰色", "紫丁香色", "淡紫色", "浅灰紫",
          "玫红色", "粉色", "西瓜粉色", "珊瑚粉", "藕粉色", "浅粉色", "巧克力棕", "古铜色", "锈棕色", "咖啡棕",
          "摩卡棕", "棕色", "姜色", "多色", "黑白色", "蓝白色", "红白色"]
with open('匹配颜色.txt','r',encoding='utf-8') as f:
    lis = f.readlines()
    lis = [i.split('_') for i in lis]

dic_col = {}
for i in lis:
    dic_col[i[0]] = i[1]
def get_col(col):

        url = "http://43.138.243.218:3000/v1/chat/completions"

        # 请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": "sk-jYMnHWfEiFJDjpcFiB1TcVtvIxSAx1a267MzPxRjD3ShZcu8"
        }

        # 请求体
        data = {
            "model": "deepseek-r1",
            "temperature": 0.3,
            "stream": True,
            "messages": [
                {
                    "role": "system",
                    "content": "you help me choice one type"
                },
                {
                    "role": "user",
                    "content": f"需要判断的颜色是{col},从列表中的颜色{ch_col}中返回一个颜色，最接近需要判断的颜色，结果两边加**,直接给出答案，不需要解释",
                }
            ]
        }

        # 发送请求
        response = requests.post(url, headers=headers, json=data, stream=True)
        lis = response.text.strip().strip('[DONE]').split('data: ')
        lis = [i for i in lis if i != '']
        strr = ''
        for i in lis:
            i = eval(i)
            a = i['choices'][0]['delta']['content']
            strr += a

        def fix_encoding(garbled_text):
            """将编码错误的文本还原为中文"""
            try:
                # 假设文本是被错误解码的UTF-8
                # 首先将每个字符转回原始字节
                bytes_data = bytes([ord(c) for c in garbled_text])

                # 然后尝试用正确的编码解码
                return bytes_data.decode('utf-8')
            except UnicodeDecodeError:
                return "无法还原文本，可能使用了其他编码"

        # 测试

        res = fix_encoding(strr)
        res_lis = re.search('\*\*(.*?)\*\*', res)
        if res_lis:
            res = res_lis.group(1)
        else:
            res = '多色'
        return res
    # x = get_col('Cream')
    # print(x)
col = '象牙色'
if col in en_col :
    col = ch_col[en_col.index(col)]
elif col in dic_col:
    col = dic_col[col]
else:
    cc = get_col(col)
    with open('匹配颜色.txt','a',encoding='utf-8') as f:
        f.write(col+'_'+cc+'\n')
    dic_col[col] = cc
    col = cc
print(col)