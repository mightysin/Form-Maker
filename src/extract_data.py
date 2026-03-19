import pandas as pd
import glob
import re
import json
import os

excel_files = glob.glob("Examples/*.xlsx")

for file in excel_files:
    try:
        # sheet_name=None：讀取所有工作表
        # header=None：將所有內容視為純資料，避免 Pandas 把第一列吃掉當作標題
        sheets_dict = pd.read_excel(file, sheet_name=None, header=None)
        
        # 迴圈處理每一個工作表 (sheet_name 就是底部的標籤名稱)
        for sheet_name, df in sheets_dict.items():
            df = df.fillna("").astype(str)
            items_dict = {}
            
            name_col, price_col, unit_col = -1, -1, -1
            
            for idx, row in df.iterrows():
                # 將整列轉為字串清單並去除前後空白
                row_vals = [str(val).strip() for val in row.tolist()]
                
                # 判斷這列是否為「表頭列」（同時包含品名與單價）
                if any("品名" in val for val in row_vals) and any("單價" in val for val in row_vals):
                    for c, val in enumerate(row_vals):
                        if "品名" in val: name_col = c
                        if "單價" in val: price_col = c
                        if "單位" in val: unit_col = c
                    
                    # 容錯處理：如果表格沒有寫「單位」的標題，推測單位通常在單價的前一格
                    if unit_col == -1 and price_col > 0:
                        unit_col = price_col - 1
                    continue
                
                # 如果還沒遇到表頭，就先跳過這列
                if name_col == -1 or price_col == -1:
                    continue
                
                # 抓取品名
                name = row_vals[name_col]
                
                # 處理「合併儲存格錯位」：如果抓到的品名是純數字 (1, 2, 3...)，就抓下一格
                if name.isdigit() and (name_col + 1) < len(row_vals):
                    name = row_vals[name_col + 1]
                
                # 過濾無效列 (如空白列、小計、總計、營業稅、日期等)
                if not name or "計" in name or name == "TO" or "日期" in name or "營業稅" in name:
                    continue
                
                # 抓取單價與單位
                price_str = row_vals[price_col]
                unit = row_vals[unit_col] if unit_col != -1 and unit_col < len(row_vals) else ""
                
                # 用正則表達式提取價格數字
                price_match = re.search(r'\d+', price_str.replace(',', ''))
                
                if price_match:
                    price = int(price_match.group())
                    
                    # 存入該工作表的字典中
                    items_dict[name] = {
                        "price": price,
                        "unit": unit
                    }
            
            # 如果這個工作表有成功抓到資料，就輸出為專屬的 JSON 檔
            if items_dict:
                # 組合檔名，例如：探漏 防爆栓_item.json
                output_filename = f"{sheet_name}_item.json"
                
                with open(output_filename, "w", encoding="utf-8") as f:
                    json.dump(items_dict, f, ensure_ascii=False, indent=4)
                    
                print(f"🎉 成功從工作表 [{sheet_name}] 萃取 {len(items_dict)} 個項目，並存成 {output_filename}")

    except Exception as e:
        print(f"檔案 {file} 處理失敗: {e}")