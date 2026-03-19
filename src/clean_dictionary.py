import json

# 1. 讀取我們剛剛建立的同義詞字典
with open('name_mapping.json', 'r', encoding='utf-8') as f:
    name_mapping = json.load(f)

cleaned_transactions = []

# 2. 讀取原本的歷史交易紀錄
with open('historical_transactions.txt', 'r', encoding='utf-8') as f:
    for line in f:
        # 去除換行符號並將字串切割成 List
        basket = line.strip().split(',')
        
        cleaned_basket = []
        for item in basket:
            item = item.strip()
            if not item: continue
            
            # 如果這個品名在字典裡有對應的標準名稱，就替換掉；如果沒有，就保留原本的名稱
            standard_name = name_mapping.get(item, item)
            cleaned_basket.append(standard_name)
        
        # 去除購物籃內可能重複的項目 (例如原本寫了兩項，但標準化後變成同一項)
        cleaned_basket = list(set(cleaned_basket))
        
        if cleaned_basket:
            cleaned_transactions.append(cleaned_basket)

# 3. 輸出乾淨、可用於 FP-Growth 的資料集
with open('clean_transactions.txt', 'w', encoding='utf-8') as f:
    for basket in cleaned_transactions:
        f.write(",".join(basket) + "\n")

print("✨ 資料清理完成！已產生 clean_transactions.txt")