import os
import json
import streamlit as st
import re

# 引入模組
from ui_layout import (
    render_css, 
    render_section_1_add_items, 
    render_section_2_preview, 
    render_section_3_notes, 
    render_section_4_export
)

# --- 1. JSON 讀取工具 ---
def load_json(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.abspath(os.path.join(current_dir, "..", "notation and warning"))
    file_path = os.path.join(target_dir, filename)
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read().replace('\xa0', ' ').replace('　', ' ')
            try:
                return json.loads(content)
            except Exception as e:
                st.error(f"❌ JSON 格式有誤【{filename}】：{e}")
                return {}
    return {}

# --- 2. 核心資料載入 (包含排序與讀取內容) ---
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(current_dir, "..", "Item_Price"))
    
    items_by_category = {}
    all_items_flat = {}
    
    if os.path.exists(data_dir):
        # 🛡️ 確保排序
        for f in sorted(os.listdir(data_dir)):
            if f.endswith(".json"):
                file_path = os.path.join(data_dir, f)
                try:
                    with open(file_path, 'r', encoding='utf-8') as json_file:
                        data = json.load(json_file)
                        
                        # ✨ 修正點：同時拿掉 .json 和 _item，讓 Key 變得很乾淨
                        # 例如 01_探漏 防爆栓_item.json -> 01_探漏 防爆栓
                        category_name = f.replace("_item.json", "").replace(".json", "")
                        
                        items_by_category[category_name] = data
                        
                        for item_name, details in data.items():
                            details['category'] = category_name
                            all_items_flat[item_name] = details
                except Exception as e:
                    st.error(f"讀取檔案 {f} 出錯：{e}")
    return items_by_category, all_items_flat

# --- 3. 初始化設定 ---
st.set_page_config(page_title="Form Maker 估價單系統", layout="wide")
render_css()

# 載入資料庫
notation_db = load_json("notation.json")
warning_db = load_json("warning.json")

# 這裡接住 load_data 回傳的兩個變數
items_by_category, all_items_flat = load_data()

# 初始化 Session State
if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- 4. 畫面 UI 佈局 ---
st.title("📝 Form Maker 智慧估價單")

col_left, col_right = st.columns([1, 2])

with col_left:
    # 第一區塊：新增項目
    render_section_1_add_items(items_by_category, all_items_flat)
    
with col_right:
    # 第二區塊：預覽表格
    render_section_2_preview()

st.divider()

# 第三區塊：注意事項 (傳入剛載入的資料庫)
render_section_3_notes(notation_db, warning_db)

st.divider()

# 第四區塊：匯出估價單
render_section_4_export()