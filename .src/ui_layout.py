import streamlit as st
import pandas as pd
import datetime
from llm_service import generate_notes_by_llm
from excel_export import generate_excel

# === 🛡️ 神主牌注意事項 (鎖死不可刪除) ===
SACRED_NOTES = [
    "本估價單30天內有效，如經同意施作，請簽名回傳。",
    "本工程施工時間為正常上班日 (星期一至五，上午九點至下午五點)，如需特殊時段施工，需另行報價。"
]

def render_css():
    st.markdown(
        """
        <style>
        [data-testid="stDataFrame"], [data-testid="stDataEditor"], .stButton > button {
            opacity: 1 !important;
            pointer-events: auto !important;
            transition: none !important;
        }
        [data-testid="stStatusWidget"] {
            display: none !important;
        }
        </style>    
        """,
        unsafe_allow_html=True
    )

# --- 操作邏輯 Callback ---
def delete_selected_items():
    st.session_state.cart = [item for item in st.session_state.cart if not item.get("選取", False)]

def add_to_cart(name, price, unit, qty=1):
    cart = st.session_state.cart
    selected_indices = [i for i, item in enumerate(cart) if item.get("選取", False)]
    insert_idx = selected_indices[-1] + 1 if selected_indices else len(cart)
    
    for item in cart:
        item["選取"] = False
        
    new_item = {
        "選取": True, 
        "品名": name,
        "數量": qty,
        "單位": unit,
        "單價": int(price),
        "金額": int(price) * qty
    }
    cart.insert(insert_idx, new_item)

def add_category_to_cart(category_name, items_by_category):
    cart = st.session_state.cart
    selected_indices = [i for i, item in enumerate(cart) if item.get("選取", False)]
    insert_idx = selected_indices[-1] + 1 if selected_indices else len(cart)
    
    for item in cart:
        item["選取"] = False

    items_in_cat = items_by_category[category_name]
    for name, details in items_in_cat.items():
        new_item = {
            "選取": False,
            "品名": name,
            "數量": 1,
            "單位": details["unit"],
            "單價": int(details["price"]),
            "金額": int(details["price"])
        }
        cart.insert(insert_idx, new_item)
        insert_idx += 1  
        
    if len(items_in_cat) > 0:
        cart[insert_idx - 1]["選取"] = True

def clear_items():
    st.session_state.cart = []

def reset_notes():
    st.session_state.selected_notes = []


# ==========================================
# 畫面渲染區塊 (四大 Section 完全解耦模組化)
# ==========================================

# 🔹 Section 1: 新增項目
def render_section_1_add_items(items_by_category, all_items_flat):
    st.header("1. 新增項目")
    
    st.subheader("🔍 快速搜尋")
    search_options = list(all_items_flat.keys())
    selected_item_search = st.selectbox("輸入關鍵字搜尋品名：", [""] + search_options, key="search_box")
    
    if selected_item_search != "":
        item_info = all_items_flat[selected_item_search]
        st.caption(f"📍 分類來源：{item_info['category']}")
        s_col1, s_col2, s_col3 = st.columns([3, 1, 2])
        mod_name_s = s_col1.text_input("品名", value=selected_item_search, key=f"mod_name_s_{selected_item_search}")
        mod_qty_s = s_col2.number_input("數量", value=1, min_value=1, step=1, key=f"mod_qty_s_{selected_item_search}")
        mod_price_s = s_col3.number_input(f"單價 (/{item_info['unit']})", value=int(item_info['price']), min_value=0, step=100, key=f"mod_price_s_{selected_item_search}")
        
        st.button("➕ 從搜尋加入", key="btn_search_add", type="primary", use_container_width=True, 
                  on_click=add_to_cart, args=(mod_name_s, mod_price_s, item_info['unit'], mod_qty_s))

    st.subheader("📁 依分類選擇")
    category_list = list(items_by_category.keys())
    selected_category = st.selectbox("步驟 1：選擇分類", ["請選擇分類..."] + category_list)
    
    if selected_category != "請選擇分類...":
        items_in_cat = items_by_category[selected_category]
        item_names = list(items_in_cat.keys())
        
        st.button(f"⚡ 一鍵加入【{selected_category}】全品項", key="btn_add_all_cat", type="secondary", use_container_width=True, 
                  on_click=add_category_to_cart, args=(selected_category, items_by_category))
        
        st.markdown("<p style='text-align: center; color: gray; margin-top: 10px; margin-bottom: 10px;'>— 或挑選單項 —</p>", unsafe_allow_html=True)
        
        selected_item_cat = st.selectbox("步驟 2：選擇單一品項", ["請選擇品項..."] + item_names)
        if selected_item_cat != "請選擇品項...":
            details = items_in_cat[selected_item_cat]
            c_col1, c_col2, c_col3 = st.columns([3, 1, 2])
            mod_name_c = c_col1.text_input("品名", value=selected_item_cat, key=f"mod_name_c_{selected_item_cat}")
            mod_qty_c = c_col2.number_input("數量", value=1, min_value=1, step=1, key=f"mod_qty_c_{selected_item_cat}")
            mod_price_c = c_col3.number_input(f"單價 (/{details['unit']})", value=int(details['price']), min_value=0, step=100, key=f"mod_price_c_{selected_item_cat}")
            
            st.button("➕ 從分類加入單項", key="btn_cat_add", type="primary", use_container_width=True, 
                      on_click=add_to_cart, args=(mod_name_c, mod_price_c, details['unit'], mod_qty_c))

# 🔹 Section 2: 目前估價單預覽
def render_section_2_preview():
    st.header("2. 目前估價單預覽")
    
    if len(st.session_state.cart) > 0:
        for item in st.session_state.cart:
            if "選取" not in item:
                item["選取"] = False

        st.write("💡 提示：勾選「選取」框，可將新項目插在該列下方；點擊最左側數字旁的小框並按鍵盤 Delete 亦可刪除該列。")
        
        col_del, col_clear = st.columns([1, 1])
        col_del.button("🗑️ 刪除選取項目", use_container_width=True, on_click=delete_selected_items)
        col_clear.button("🧹 清空所有品項", type="primary", use_container_width=True, on_click=clear_items)
        
        df = pd.DataFrame(st.session_state.cart)
        
        if not df.empty:
            df.index = df.index + 1
        
        edited_df = st.data_editor(
            df,
            column_config={
                "選取": st.column_config.CheckboxColumn("選取", default=False, width="small"),
                "品名": st.column_config.TextColumn(disabled=False),
                "單價": st.column_config.NumberColumn(disabled=False, step=100, min_value=0),
                "單位": st.column_config.TextColumn(disabled=False),
                "數量": st.column_config.NumberColumn(disabled=False, step=1, min_value=1),
                "金額": st.column_config.NumberColumn(disabled=True)
            },
            column_order=("選取", "品名", "數量", "單位", "單價", "金額"),
            hide_index=False, 
            use_container_width=True,
            num_rows="dynamic",
            key="cart_editor"
        )
        
        new_cart = edited_df.to_dict('records')
        valid_cart = []
        needs_rerun = False
        total_price = 0
        
        for item in new_cart:
            if pd.isna(item.get('品名')) or str(item.get('品名')).strip() == "":
                continue
                
            if pd.isna(item.get('數量')): item['數量'] = 1
            if pd.isna(item.get('單價')): item['單價'] = 0
            if pd.isna(item.get('單位')): item['單位'] = "式"
            item['選取'] = bool(item.get('選取', False)) 
            
            calc_total = int(item['數量'] * item['單價'])
            item['金額'] = calc_total
            total_price += calc_total
            
            valid_cart.append(item)

        if len(valid_cart) != len(st.session_state.cart):
            needs_rerun = True
        else:
            for i in range(len(valid_cart)):
                old_item = st.session_state.cart[i]
                if (valid_cart[i].get('品名') != old_item.get('品名') or 
                    valid_cart[i].get('單位') != old_item.get('單位') or
                    valid_cart[i].get('單價') != old_item.get('單價') or
                    valid_cart[i].get('數量') != old_item.get('數量') or
                    valid_cart[i].get('選取', False) != old_item.get('選取', False)):
                    needs_rerun = True
                    break

        st.session_state.cart = valid_cart
        if needs_rerun:
            st.rerun() 
        
        st.markdown(f"### 總計金額： **${total_price:,}**")

    else:
        st.info("👈 請從左側選擇分類加入項目，或在下方直接新增")

# 🔹 Section 3: 專屬注意事項
def render_section_3_notes(notes_db, all_available_notes):
    st.header("3. 專屬注意事項")
    
    st.markdown("**(固定條款)**")
    for sacred_note in SACRED_NOTES:
        st.markdown(f"🔒 `{sacred_note}`")
        if sacred_note in all_available_notes:
            all_available_notes.remove(sacred_note)
            
    st.markdown("<br>", unsafe_allow_html=True) 

    if 'selected_notes' not in st.session_state:
        st.session_state.selected_notes = []

    if st.button("✨ 讓 AI 判斷額外注意事項", type="secondary", use_container_width=True):
        if len(st.session_state.cart) == 0:
            st.warning("⚠️ 請先加入估價品項，AI 才能幫您判斷喔！")
        else:
            with st.spinner('AI 正在分析最適合的條款...'):
                try:
                    ai_notes = generate_notes_by_llm(st.session_state.cart, notes_db, all_available_notes)
                    combined = st.session_state.selected_notes.copy()
                    for note in ai_notes:
                        if note not in combined and note not in SACRED_NOTES:
                            combined.append(note)
                    st.session_state.selected_notes = combined
                except Exception as e:
                    st.error(str(e))
    
    st.session_state.selected_notes = st.multiselect(
        "➕ 點擊下方框框，手動新增或刪除【額外】注意事項：",
        options=all_available_notes,
        default=st.session_state.selected_notes
    )
    
    st.button("🧹 清空額外注意事項", type="secondary", use_container_width=True, on_click=reset_notes)

# 🔹 Section 4: 匯出估價單
def render_section_4_export():
    st.header("4. 匯出估價單")

    # 一開始就顯示介面，與購物車狀態解耦
    actual_total = sum(int(item.get('數量', 0)) * int(item.get('單價', 0)) for item in st.session_state.cart)
    
    col_ex1, col_ex2, col_ex3 = st.columns(3)
    with col_ex1:
        client_name = st.text_input("客戶名稱 (TO)：", placeholder="例如：王大明 先生")
    with col_ex2:
        export_date = st.date_input("報價日期：", datetime.date.today())
    with col_ex3:
        tax_type = st.radio("營業稅計算：", ["已含稅", "未稅 (+5% 營業稅)"], horizontal=True)

    subtotal = actual_total
    if tax_type == "未稅 (+5% 營業稅)":
        tax = int(subtotal * 0.05)
        grand_total = subtotal + tax
    else:
        grand_total = subtotal
        subtotal = int(grand_total / 1.05)
        tax = grand_total - subtotal
        
    st.info(f"📊 估價單試算 ➡️ 小計：${subtotal:,} | 營業稅：${tax:,} | 總計：${grand_total:,}")

    st.markdown("##### 📂 附加到客戶歷史檔案 (選填)")
    uploaded_file = st.file_uploader(
        "如果您想將這份估價單作為「新工作表」加入現有的 Excel，請在此上傳：", 
        type=["xlsx"]
    )
    
    if uploaded_file:
        st.success(f"✅ 已載入歷史檔案：{uploaded_file.name}")

    final_notes_to_export = SACRED_NOTES + st.session_state.selected_notes

    if len(st.session_state.cart) > 0:
        excel_data = generate_excel(
            client_name, export_date, subtotal, tax, grand_total, 
            st.session_state.cart, final_notes_to_export, uploaded_file
        )
        
        if uploaded_file:
            file_name = f"{uploaded_file.name.replace('.xlsx', '')}_更新版.xlsx"
        else:
            file_name = f"{client_name if client_name else '未命名'}_估價單.xlsx"
            
        st.download_button(
            label="📥 匯出並下載 Excel",
            data=excel_data,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
    else:
        st.warning("⚠️ 請先新增項目，方可匯出估價單。")