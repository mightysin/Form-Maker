import pandas as pd
import glob
import re
import os

# 1. 抓取所有 xls 與 xlsx 檔案
# 使用 *.xls* 可以同時捕捉到 .xls 與 .xlsx
excel_files = glob.glob("Examples/1通用範本.xls*")

# 用來儲存所有的「購物籃」（每張估價單的項目清單）
all_transactions = []

print("開始萃取歷史估價單資料...")

for file in excel_files:
    try:
        # 讀取所有工作表
        sheets_dict = pd.read_excel(file, sheet_name=None, header=None)
        
        for sheet_name, df in sheets_dict.items():
            df = df.fillna("").astype(str)
            
            # 這個 List 用來裝「這一個工作表（這張估價單）」裡的所有項目
            current_basket = []
            name_col, price_col = -1, -1
            
            for idx, row in df.iterrows():
                row_vals = [str(val).strip() for val in row.tolist()]
                
                # 尋找表頭
                if any("品名" in val for val in row_vals) and any("單價" in val for val in row_vals):
                    for c, val in enumerate(row_vals):
                        if "品名" in val: name_col = c
                        if "單價" in val: price_col = c
                    continue
                
                if name_col == -1 or price_col == -1:
                    continue
                
                # 抓取品名與處理合併錯位
                name = row_vals[name_col]
                if name.isdigit() and (name_col + 1) < len(row_vals):
                    name = row_vals[name_col + 1]
                
                # 過濾無效列
                if not name or "計" in name or name == "TO" or "日期" in name or "營業稅" in name:
                    continue
                
                # 確保這列真的有金額，才算是有效項目
                price_str = row_vals[price_col]
                price_match = re.search(r'\d+', price_str.replace(',', ''))
                
                if price_match:
                    # ✅ 將有效的品名加入目前的購物籃中
                    current_basket.append(name)
            
            # 如果這張表有抓到東西，就把這個購物籃加入總紀錄中
            if current_basket:
                all_transactions.append(current_basket)
                print(f"成功從 [{os.path.basename(file)} - {sheet_name}] 萃取 {len(current_basket)} 個項目")

    except Exception as e:
        print(f"檔案 {file} 處理失敗: {e}")

# 3. 將結果輸出成 txt 檔 (一行代表一張估價單)
output_file = "standard_name.txt"
with open(output_file, "w", encoding="utf-8") as f:
    for basket in all_transactions:
        # 將 List 裡的字串用逗號連接成一行
        line = ",".join(basket)
        f.write(line + "\n")

print(f"\n🎉 萃取完成！共收集了 {len(all_transactions)} 筆交易紀錄，已存為 {output_file}")