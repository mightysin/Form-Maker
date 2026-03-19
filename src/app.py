import streamlit as st
import json
import glob
import os

# 引入我們拆分出去的模組
from ui_layout import (
    render_css, 
    render_section_1_add_items, 
    render_section_2_preview, 
    render_section_3_notes, 
    render_section_4_export
)

def load_json(filename):
    # 1. 抓到 app.py 所在的資料夾 (現在是正常的 src 了)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. 退回上一層，並進入 notation and warning，然後強制轉成乾淨的絕對路徑
    target_dir = os.path.abspath(os.path.join(current_dir, "..", "notation and warning"))
    file_path = os.path.join(target_dir, filename)
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            # 暴力洗淨隱形空白
            content = content.replace('\xa0', ' ').replace('　', ' ')
            try:
                return json.loads(content)
            except Exception as e:
                st.error(f"❌ JSON 格式有誤【{filename}】：{e}")
                return {}
    else:
        st.error(f"❌ 找不到檔案，請確認路徑：\n{file_path}")
        return {}

# 重新載入您的雙資料庫
notation_db = load_json("notation.json")
warning_db = load_json("warning.json")

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

col_left, col_right = st.columns([1, 2])

# 渲染左半邊 (新增項目)
with col_left:
    # 第一區塊：新增項目
    render_section_1_add_items(items_by_category, all_items_flat)
    
with col_right:
    # 第二區塊：讓預覽表格獨佔右側巨大版面！
    render_section_2_preview()


st.divider() # 區塊之間可以用分隔線隔開，畫面比較整齊

# 第三區塊：注意事項 (一開始就會顯示)
render_section_3_notes(notation_db, warning_db)

st.divider()

# 第四區塊：匯出估價單 (一開始就會顯示)
render_section_4_export()
