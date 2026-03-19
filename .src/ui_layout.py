import streamlit as st
import pandas as pd
import datetime
import re
from llm_service import generate_notes_by_llm
from excel_export import generate_excel

# === 🛡️ 神主牌注意事項 (鎖死不可刪除) ===
SACRED_NOTES = [
    "本估價單30天內有效，如經同意施作，請簽名回傳。",
    "本工程施工時間為正常上班日 (星期一至五，上午九點至下午五點)，如需特殊時段施工，需另行報價。"
]

# === ✨ 終極防護罩：無敵安全轉換 ===
def safe_int(val, default=0):
    """最暴力的攔截，吞下所有 None, NA, 空白，絕不報錯"""
    try:
        if val is None:
            return default
        val_str = str(val).strip()
        if val_str == "" or val_str.lower() in ["none", "nan", "<na>"]:
            return default
        return int(float(val))
    except Exception: # 攔截所有 TypeError, ValueError 等一切奇葩錯誤
        return default

# === ⚙️ 動態觸發條款引擎 ===
def get_dynamic_notes(cart):
    dynamic_notes = []
    has_water_cooling = False
    fan_coil_qty = 0

    for item in cart:
        name = str(item.get("品名", ""))
        qty = safe_int(item.get("數量"), 0)

        if "送風機" in name and "清洗" in name:
            fan_coil_qty += qty
            
        if "水冷" in name and ("清洗" in name or "保養" in name):
            has_water_cooling = True

    if fan_coil_qty > 0:
        dynamic_notes.append(f"送風機初估{fan_coil_qty}台.實際數量以現場為準.進行清洗保養作業時.會順便進行送風機馬達檢測.如發現馬達軸承有老化現象.會建議業主更新.")
        
    if has_water_cooling:
        dynamic_notes.append("清洗散熱管路,可能因主機老舊,造成管路腐蝕穿孔,導致管路漏水,冷氣無法運轉,若發生上述狀況,恕非屬本公司之責,敬請見諒.")
        dynamic_notes.append("舊有之關水閘閥 可能因年久老化無法完全關水 如有此種現象發生 更換銅閘閥費用另計")

    return dynamic_notes

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

def delete_selected_items():
    st.session_state.cart = [item for item in st.session_state.cart if not item.get("選取", False)]

def add_to_cart(name, price, unit, qty=1):
    cart = st.session_state.cart
    
    if any(item.get("品名") == name for item in cart):
        st.warning(f"⚠️ 「{name}」已存在估價單中！請直接在右側修改數量。")
        return
        
    selected_indices = [i for i, item in enumerate(cart) if item.get("選取", False)]
    insert_idx = selected_indices[-1] + 1 if selected_indices else len(cart)
    
    for item in cart:
        item["選取"] = False
        
    new_item = {
        "選取": True, 
        "品名": name,
        "數量": safe_int(qty, 1),
        "單位": unit,
        "單價": safe_int(price, 0),
        "金額": safe_int(price, 0) * safe_int(qty, 1)
    }
    cart.insert(insert_idx, new_item)

def add_category_to_cart(category_name, items_by_category):
    cart = st.session_state.cart
    selected_indices = [i for i, item in enumerate(cart) if item.get("選取", False)]
    insert_idx = selected_indices[-1] + 1 if selected_indices else len(cart)
    
    for item in cart:
        item["選取"] = False

    items_in_cat = items_by_category[category_name]
    added_count = 0
    
    for name, details in items_in_cat.items():
        if any(item.get("品名") == name for item in cart):
            continue
            
        p = safe_int(details["price"], 0)
        new_item = {
            "選取": False,
            "品名": name,
            "數量": 1,
            "單位": details["unit"],
            "單價": p,
            "金額": p
        }
        cart.insert(insert_idx, new_item)
        insert_idx += 1  
        added_count += 1
        
    if added_count > 0:
        cart[insert_idx - 1]["選取"] = True
    else:
        clean_cat = re.sub(r'^\d+_', '', category_name)
        st.warning(f"⚠️ 【{clean_cat}】的所有品項皆已在估價單中！")

def clear_items():
    st.session_state.cart = []

def reset_notes():
    st.session_state.selected_notes = []

# 🔹 Section 1: 新增項目
def render_section_1_add_items(items_by_category, all_items_flat):
    st.header("1. 新增項目")
    st.subheader("🔍 快速搜尋")
    search_options = list(all_items_flat.keys())
    selected_item_search = st.selectbox("輸入關鍵字搜尋品名：", [""] + search_options, key="search_box")
    
    if selected_item_search != "":
        item_info = all_items_flat[selected_item_search]
        clean_cat_source = re.sub(r'^\d+_', '', item_info['category'])
        st.caption(f"📍 分類來源：{clean_cat_source}")
        
        s_col1, s_col2, s_col3 = st.columns([3, 1, 2])
        mod_name_s = s_col1.text_input("品名", value=selected_item_search, key=f"mod_name_s_{selected_item_search}")
        mod_qty_s = s_col2.number_input("數量", value=1, min_value=1, step=1, key=f"mod_qty_s_{selected_item_search}")
        mod_price_s = s_col3.number_input(f"單價 (/{item_info['unit']})", value=int(item_info['price']), min_value=0, step=100, key=f"mod_price_s_{selected_item_search}")
        
        st.button("➕ 從搜尋加入", key="btn_search_add", type="primary", use_container_width=True, 
                  on_click=add_to_cart, args=(mod_name_s, mod_price_s, item_info['unit'], mod_qty_s))

    st.subheader("📁 依分類選擇")
    category_list = list(items_by_category.keys())
    
    def format_category_name(cat_name):
        if cat_name == "請選擇分類...": return cat_name
        return re.sub(r'^\d+_', '', cat_name)
        
    selected_category = st.selectbox(
        "步驟 1：選擇分類", 
        ["請選擇分類..."] + category_list,
        format_func=format_category_name 
    )
    
    if selected_category != "請選擇分類...":
        items_in_cat = items_by_category[selected_category]
        item_names = list(items_in_cat.keys())
        
        clean_selected_cat = format_category_name(selected_category)
        st.button(f"⚡ 一鍵加入【{clean_selected_cat}】全品項", key="btn_add_all_cat", type="secondary", use_container_width=True, 
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

        st.write("💡 提示：勾選「選取」框可定位插入點；點擊最左側數字旁小框並按 Delete 可刪除。")
        
        col_del, col_clear = st.columns([1, 1])
        col_del.button("🗑️ 刪除選取項目", use_container_width=True, on_click=delete_selected_items)
        col_clear.button("🧹 清空所有品項", type="primary", use_container_width=True, on_click=clear_items)
        
        df = pd.DataFrame(st.session_state.cart)
        
        if not df.empty:
            df.index = df.index + 1
            
        exact_height = (len(df) + 1) * 36 + 43
        
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
            height=exact_height, 
            key="cart_editor"
        )
        
        new_cart = edited_df.to_dict('records')
        valid_cart = []
        total_price = 0
        
        for item in new_cart:
            if item.get('品名') is None or str(item.get('品名')).strip() == "":
                continue
                
            qty = safe_int(item.get('數量'), 1)
            price = safe_int(item.get('單價'), 0)
            
            item['數量'] = qty
            item['單價'] = price
            
            if item.get('單位') is None or str(item.get('單位')).strip() == "": 
                item['單位'] = "式"
                
            item['選取'] = bool(item.get('選取', False)) 
            
            calc_total = qty * price
            item['金額'] = calc_total
            total_price += calc_total
            
            valid_cart.append(item)

        st.session_state.cart = valid_cart
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
            
    dynamic_notes = get_dynamic_notes(st.session_state.cart)
    if dynamic_notes:
        st.markdown("**(自動觸發條款)**")
        for d_note in dynamic_notes:
            st.markdown(f"⚙️ `{d_note}`")
            if d_note in all_available_notes:
                all_available_notes.remove(d_note)

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
                        if note not in combined and note not in SACRED_NOTES and note not in dynamic_notes:
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

    actual_total = sum(safe_int(item.get('數量'), 0) * safe_int(item.get('單價'), 0) for item in st.session_state.cart)
    
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

    current_notes = st.session_state.get('selected_notes', [])
    dynamic_notes = get_dynamic_notes(st.session_state.cart)
    final_notes_to_export = SACRED_NOTES + dynamic_notes + current_notes

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