import streamlit as st
import pandas as pd
import datetime
from llm_service import generate_notes_by_llm
from excel_export import generate_excel

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

# --- 購物車操作邏輯 ---
def add_to_cart(name, price, unit, qty=1):
    st.session_state.cart.append({
        "品名": name,
        "數量": qty,
        "單位": unit,
        "單價": int(price),
        "金額": int(price) * qty
    })

def add_category_to_cart(category_name, items_by_category):
    items_in_cat = items_by_category[category_name]
    for name, details in items_in_cat.items():
        add_to_cart(name, details["price"], details["unit"], 1)

def clear_cart():
    st.session_state.cart = []

# --- 畫面渲染區塊 ---
def render_left_column(items_by_category, all_items_flat):
    st.header("1. 新增項目")
    
    st.subheader("🔍 快速搜尋")
    search_options = list(all_items_flat.keys())
    selected_item_search = st.selectbox("輸入關鍵字搜尋品名：", [""] + search_options, key="search_box")
    
    if selected_item_search != "":
        item_info = all_items_flat[selected_item_search]
        st.caption(f"📍 分類來源：{item_info['category']}")
        s_col1, s_col2, s_col3 = st.columns([3, 1, 2])
        mod_name_s = s_col1.text_input("品名", value=selected_item_search, key="mod_name_s")
        mod_qty_s = s_col2.number_input("數量", value=1, min_value=1, step=1, key="mod_qty_s")
        mod_price_s = s_col3.number_input(f"單價 (/{item_info['unit']})", value=int(item_info['price']), min_value=0, step=100, key="mod_price_s")
        
        st.button("➕ 從搜尋加入", key="btn_search_add", type="primary", use_container_width=True, 
                  on_click=add_to_cart, args=(mod_name_s, mod_price_s, item_info['unit'], mod_qty_s))

    st.divider()

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
            mod_name_c = c_col1.text_input("品名", value=selected_item_cat, key="mod_name_c")
            mod_qty_c = c_col2.number_input("數量", value=1, min_value=1, step=1, key="mod_qty_c")
            mod_price_c = c_col3.number_input(f"單價 (/{details['unit']})", value=int(details['price']), min_value=0, step=100, key="mod_price_c")
            
            st.button("➕ 從分類加入單項", key="btn_cat_add", type="primary", use_container_width=True, 
                      on_click=add_to_cart, args=(mod_name_c, mod_price_c, details['unit'], mod_qty_c))

def render_right_column(notes_db, all_available_notes):
    st.header("2. 目前估價單預覽")
    
    if len(st.session_state.cart) > 0:
        df = pd.DataFrame(st.session_state.cart)
        st.write("💡 提示：雙擊數字即可出現上下微調按鈕，或點選後直接使用鍵盤「上下方向鍵」修改。")
        
        edited_df = st.data_editor(
            df,
            column_config={
                "品名": st.column_config.TextColumn(disabled=False),
                "單價": st.column_config.NumberColumn(disabled=False, step=100, min_value=0),
                "單位": st.column_config.TextColumn(disabled=False),
                "數量": st.column_config.NumberColumn(disabled=False, step=1, min_value=1),
                "金額": st.column_config.NumberColumn(disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="cart_editor"
        )
        
        new_cart = edited_df.to_dict('records')
        needs_rerun = False
        total_price = 0
        
        for i, item in enumerate(new_cart):
            if pd.isna(item.get('品名')): item['品名'] = ""
            if pd.isna(item.get('數量')): item['數量'] = 1
            if pd.isna(item.get('單價')): item['單價'] = 0
            if pd.isna(item.get('單位')): item['單位'] = "式"
            
            calc_total = int(item['數量'] * item['單價'])
            if calc_total != item.get('金額'):
                item['金額'] = calc_total
                needs_rerun = True
            
            if i < len(st.session_state.cart):
                old_item = st.session_state.cart[i]
                if item['品名'] != old_item['品名'] or item['單位'] != old_item['單位']:
                    needs_rerun = True
                    
            total_price += calc_total

        if len(new_cart) != len(st.session_state.cart):
            needs_rerun = True

        if needs_rerun:
            st.session_state.cart = new_cart
            st.rerun() 
        else:
            st.session_state.cart = new_cart
        
        st.divider()
        st.markdown(f"### 總計金額： ${total_price:,}")
        
        # --- AI 注意事項區塊 ---
        st.subheader("📝 專屬注意事項")
        if 'selected_notes' not in st.session_state:
            st.session_state.selected_notes = notes_db.get("通用條款", [])

        if st.button("✨ 讓 AI 判斷注意事項", type="secondary", use_container_width=True):
            with st.spinner('AI 正在分析最適合的條款...'):
                try:
                    st.session_state.selected_notes = generate_notes_by_llm(
                        st.session_state.cart, notes_db, all_available_notes
                    )
                except Exception as e:
                    st.error(str(e))
        
        st.session_state.selected_notes = st.multiselect(
            "目前的注意事項清單 (可手動增刪)：",
            options=all_available_notes,
            default=st.session_state.selected_notes,
            key="notes_selector"
        )
        
        st.button("🗑️ 清空估價單", type="primary", on_click=clear_cart)
        return total_price
    else:
        st.info("👈 請從左側選擇分類加入項目，或在下方直接新增")
        return 0

def render_export_section(total_price):
    st.divider()
    st.header("3. 匯出估價單")

    if len(st.session_state.cart) > 0:
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        with col_ex1:
            client_name = st.text_input("客戶名稱 (TO)：", placeholder="例如：王大明 先生")
        with col_ex2:
            export_date = st.date_input("報價日期：", datetime.date.today())
        with col_ex3:
            tax_type = st.radio("營業稅計算：", ["已含稅", "未稅 (+5% 營業稅)"], horizontal=True)

        subtotal = total_price
        if tax_type == "未稅 (+5% 營業稅)":
            tax = int(subtotal * 0.05)
            grand_total = subtotal + tax
        else:
            grand_total = subtotal
            subtotal = int(grand_total / 1.05)
            tax = grand_total - subtotal
            
        st.info(f"📊 估價單試算 ➡️ 小計：${subtotal:,} | 營業稅：${tax:,} | 總計：${grand_total:,}")

        # 呼叫匯出檔案邏輯
        excel_data = generate_excel(
            client_name, export_date, subtotal, tax, grand_total, 
            st.session_state.cart, st.session_state.selected_notes
        )
        
        file_name = f"{client_name if client_name else '未命名'}_估價單.xlsx"
        st.download_button(
            label="📥 匯出並下載 Excel",
            data=excel_data,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )