import google.generativeai as genai
import json
import os
import streamlit as st

# ================= 讀取 API 金鑰 =================
def load_api_key():
    key_path = "api_key"
    
    # 🕵️ 印出 Python 目前到底站在哪個資料夾找東西
    print(f"🔍 [Debug] Python 目前的執行目錄: {os.getcwd()}")
    
    # 檢查 "api_key" 存不存在
    if os.path.exists(key_path):
        print(f"✅ [Debug] 找到 '{key_path}' 檔案了！")
        with open(key_path, "r", encoding="utf-8") as f:
            key_content = f.read().strip()
            print(f"✅ [Debug] 金鑰長度: {len(key_content)}")
            return key_content
            
    # 如果找不到，試試看是不是被加上了 .txt
    elif os.path.exists(key_path + ".txt"):
        print(f"⚠️ [Debug] 找不到 'api_key'，但找到了 'api_key.txt'！已被 Windows 隱藏附檔名。")
        with open(key_path + ".txt", "r", encoding="utf-8") as f:
            key_content = f.read().strip()
            print(f"✅ [Debug] 金鑰長度: {len(key_content)}")
            return key_content
            
    else:
        print(f"❌ [Debug] 徹底找不到檔案！請確認檔案真的放在 {os.getcwd()} 底下。")
        return os.environ.get("GEMINI_API_KEY", "")

# 取得金鑰並設定
API_KEY = load_api_key()

print(f"👀 [Debug] 讀到的金鑰長度: {len(API_KEY)}")
print(f"👀 [Debug] 實際字串: '{API_KEY}'")

if not API_KEY:
    # 提醒開發者
    print("⚠️ 警告：找不到名為 'api_key' 的檔案，或環境變數未設定！請確認金鑰是否存在。")

genai.configure(api_key=API_KEY)

# 初始化模型
model = genai.GenerativeModel('gemini-2.5-flash')
# =================================================

def generate_notes_by_llm(cart, notes_db, all_available_notes):
    """
    接收目前的購物車內容與注意事項庫，回傳 AI 挑選的注意事項清單
    """
    if not cart:
        return []
    
    if not API_KEY:
        raise Exception("系統尚未設定 API 金鑰，請聯絡管理員確認 'api_key' 檔案設定。")
    
    # 將購物車內容簡化為字串，方便餵給 LLM
    cart_summary = ", ".join([f"{item['品名']} ({item['數量']} {item['單位']})" for item in cart])
    
    # 設計給 LLM 的 Prompt
    prompt = f"""
    你是一位專業的空調工程估價師。請根據客戶即將施作的【工程項目】，從【注意事項資料庫】中挑選出最相關且必須提醒客戶的條款。
    
    【注意事項資料庫】：
    {json.dumps(notes_db, ensure_ascii=False, indent=2)}
    
    【客戶的工程項目】：
    {cart_summary}
    
    規則：
    1. 「通用條款」分類下的所有條款必須無條件加入。
    2. 根據工程項目，挑選其他分類中適合的條款。
    3. 嚴格只能輸出挑選出的條款，每個條款佔一行，不要有前言、標號、項目符號或任何多餘解釋。
    """
    
    try:
        # 呼叫 LLM
        response = model.generate_content(prompt)
        
        # 整理回傳的結果，將字串切分成清單並過濾空白行
        generated_lines = [line.strip() for line in response.text.split('\n') if line.strip()]
        
        # 防呆：比對資料庫，避免 AI 產生幻覺 (自己發明條文)
        matched_notes = []
        for line in generated_lines:
            for valid_note in all_available_notes:
                if valid_note[:10] in line or line[:10] in valid_note: # 模糊比對前10個字
                    if valid_note not in matched_notes:
                        matched_notes.append(valid_note)
                    break
        return matched_notes
        
    except Exception as e:
        raise Exception(f"AI 生成失敗，請檢查 API 或是網路。錯誤: {e}")