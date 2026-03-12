import streamlit as st
import json
import glob
import os

# 引入我們拆分出去的模組
from ui_layout import render_css, render_left_column, render_right_column, render_export_section

# 設定網頁標題與寬度
st.set_page_config(page_title="Form Maker 估價單系統", layout="wide")

# 套用 CSS 優化 (消除載入遮罩)
render_css()

@st.cache_data
def load_data():
    items_by_category = {}
    all_items_flat = {}
    filepaths = glob.glob("Item_Price/*_item.json")
    for path in filepaths:
        category = os.path.basename(path).replace("_item.json", "")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            items_by_category[category] = data
            for item_name, details in data.items():
                all_items_flat[item_name] = {"price": details["price"], "unit": details["unit"], "category": category}
    return items_by_category, all_items_flat

@st.cache_data
def load_notes():
    if os.path.exists("notes_template.json"):
        with open("notes_template.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 1. 初始化資料字典
items_by_category, all_items_flat = load_data()
notes_db = load_notes()

all_available_notes = []
for cat, notes in notes_db.items():
    all_available_notes.extend(notes)

# 2. 初始化 Session State
if 'cart' not in st.session_state:
    st.session_state.cart = []

# ================= 畫面 UI 佈局 (完全模組化) =================
st.title("📝 Form Maker 智慧估價單")

col_left, col_right = st.columns([1, 1])

# 渲染左半邊 (新增項目)
with col_left:
    render_left_column(items_by_category, all_items_flat)

# 渲染右半邊 (預覽區與注意事項)，並取得總價
with col_right:
    total_price = render_right_column(notes_db, all_available_notes)

# 渲染底部 (匯出區)
render_export_section(total_price)