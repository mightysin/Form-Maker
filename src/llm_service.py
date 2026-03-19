import google.generativeai as genai
import json
import os
import streamlit as st

# ================= 讀取 API 金鑰 =================
def load_api_key():
    # 1. 優先嘗試讀取 Streamlit Cloud 專屬的「保險箱 (Secrets)」
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass # 本地端如果沒有保險箱，就忽略錯誤繼續往下找

    # 2. 如果保險箱沒有，嘗試尋找本地端的實體檔案
    key_path = "api_key"
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as f:
            return f.read().strip()
            
    # 3. 最後的備案：讀取系統環境變數
    return os.environ.get("GEMINI_API_KEY", "")

# 取得金鑰並設定
API_KEY = load_api_key()

if not API_KEY:
    # 提醒開發者
    print("⚠️ 警告：找不到名為 'api_key' 的檔案，或環境變數未設定！請確認金鑰是否存在。")

genai.configure(api_key=API_KEY)

# 初始化模型 (統一在這裡宣告一次就好)
model = genai.GenerativeModel('gemini-2.5-flash')
# =================================================

def generate_notations_by_llm(cart, notation_db):
    """專門負責挑選【注意事項】的 AI 引擎"""
    cart_text = json.dumps(cart, ensure_ascii=False)
    db_text = json.dumps(notation_db, ensure_ascii=False)
    
    prompt = f"""
    你是一位專業的空調工程師。請根據客戶的【估價單品項】，從【注意事項資料庫】中挑選出絕對必要的注意事項。
    
    【估價單品項】：
    {cart_text}
    
    【注意事項資料庫】：
    {db_text}
    
    規則：
    1. 只要回傳一個 JSON 陣列 (Array of Strings)，內容是挑選出的完整條文。
    2. 不要改變原本資料庫裡的字句。
    3. 判斷要精準，不要加入無關的條文。
    4. 如果沒有適合的，請回傳空陣列 []。
    5. 嚴格警告：只允許輸出 JSON 陣列，絕對不准包含任何前言、後語或其他文字！
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 暴力清除可能殘留的 Markdown 標記
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        text = text.strip()
        return json.loads(text)
        
    except Exception as e:
        # ✨ 終極防護：就算解析失敗，也絕對不讓系統當機，直接回傳空陣列
        print(f"⚠️ 注意事項 AI 解析失敗: {e}")
        return []

def generate_warnings_by_llm(cart, warning_db):
    """專門負責挑選【施工免責與警語】的 AI 引擎"""
    cart_text = json.dumps(cart, ensure_ascii=False)
    db_text = json.dumps(warning_db, ensure_ascii=False)
    
    prompt = f"""
    你是一位專業的空調工程師。請根據客戶的【估價單品項】，從【免責警語資料庫】中挑選出絕對必要的施工免責與賠償警語。
    
    【估價單品項】：
    {cart_text}
    
    【免責警語資料庫】：
    {db_text}
    
    規則：
    1. 只要回傳一個 JSON 陣列 (Array of Strings)，內容是挑選出的完整條文。
    2. 不要改變原本資料庫裡的字句。
    3. 判斷要極度精準，特別注意「洗管破洞」、「舊管路老化」、「舊主機免責」等對應項目。
    4. 如果沒有適合的，請回傳空陣列 []。
    5. 嚴格警告：只允許輸出 JSON 陣列，絕對不准包含任何前言、後語或其他文字！
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        text = text.strip()
        return json.loads(text)
        
    except Exception as e:
        # ✨ 終極防護
        print(f"⚠️ 警語 AI 解析失敗: {e}")
        return []