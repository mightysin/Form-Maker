import streamlit as st
import pandas as pd
import datetime
import re
from excel_export import generate_excel
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

# ✨ 這裡是最關鍵的修正：正確引入兩顆全新的 AI 引擎！
from llm_service import generate_notations_by_llm, generate_warnings_by_llm

# === 🛡️ 神主牌注意事項 (鎖死不可刪除) ===
SACRED_NOTES = [
    "本估價單30天內有效，如經同意施作，請簽名回傳。",
    "本工程施工時間為正常上班日 (星期一至五，上午九點至下午五點)，如需特殊時段施工，需另行報價。"
]

# === ✨ 終極防護罩：無敵安全轉換 ===
def safe_int(val, default=0):
    try:
        if val is None: return default
        val_str = str(val).strip()
        if val_str == "" or val_str.lower() in ["none", "nan", "<na>"]: return default
        return int(float(val))
    except Exception: 
        return default

# === ⚙️ 動態觸發條款引擎 (加入保固雷達) ===
def get_dynamic_notes(cart):
    dynamic_notes = []
    has_water_cooling = False
    fan_coil_qty = 0
    has_warranty_item = False

    for item in cart:
        name = str(item.get("品名", ""))
        qty = safe_int(item.get("數量"), 0)

        if "送風機" in name and "清洗" in name:
            fan_coil_qty += qty
            
        if "水冷" in name and ("清洗" in name or "保養" in name):
            has_water_cooling = True
            
        if name.strip() != "":
            maintenance_keywords = ["清洗", "保養", "清潔", "疏通", "拆除", "清運", "清理", "探漏", "檢測", "放水", "測試", "處理", "填充", "廢棄物"]
            installation_keywords = ["更新", "更換", "安裝", "全新", "定做", "配置", "佈設", "焊補", "包覆"]
            
            is_maintenance = any(k in name for k in maintenance_keywords)
            is_installation = any(k in name for k in installation_keywords)
            
            if is_installation or not is_maintenance:
                has_warranty_item = True

    if fan_coil_qty > 0:
        dynamic_notes.append(f"送風機初估{fan_coil_qty}台.實際數量以現場為準.進行清洗保養作業時.會順便進行送風機馬達檢測.如發現馬達軸承有老化現象.會建議業主更新.")
    if has_water_cooling:
        dynamic_notes.append("清洗散熱管路,可能因主機老舊,造成管路腐蝕穿孔,導致管路漏水,冷氣無法運轉,若發生上述狀況,恕非屬本公司之責,敬請見諒.")
        dynamic_notes.append("舊有之關水閘閥 可能因年久老化無法完全關水 如有此種現象發生 更換銅閘閥費用另計")
    if has_warranty_item:
        dynamic_notes.append("更換之零件及施工項目保固一年。")

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
    subtotal = int(price) * int(qty)
    new_item = {
        "品名": name,
        "數量": qty,
        "單位": unit,
        "單價": price,
        "金額": subtotal
    }
    
    # 檢查是否有指定插入位置 (從右邊表格選取的)
    insert_index = st.session_state.get('insert_index')
    
    if insert_index is not None and 0 <= insert_index < len(st.session_state.cart):
        # 插入到選取的「該項目的下方」(所以是 index + 1)
        st.session_state.cart.insert(insert_index + 1, new_item)
        # 更新指標：讓連續按「加入」時，品項會順序往下排
        st.session_state.insert_index += 1
    else:
        # 如果都沒選取，就加到最下面
        st.session_state.cart.append(new_item)

def add_category_to_cart(category_name, items_by_category):
    items = items_by_category[category_name]
    insert_index = st.session_state.get('insert_index')
    
    new_items = []
    for item_name, details in items.items():
        new_items.append({
            "品名": item_name,
            "數量": 1,
            "單位": details["unit"],
            "單價": details["price"],
            "金額": details["price"]
        })
        
    if insert_index is not None and 0 <= insert_index < len(st.session_state.cart):
        # 將整個分類的品項依序插入
        for i, item in enumerate(new_items):
            st.session_state.cart.insert(insert_index + 1 + i, item)
        # 更新指標，確保下次加入不會位置錯亂
        st.session_state.insert_index += len(new_items)
    else:
        st.session_state.cart.extend(new_items)

def reset_notes():
    st.session_state.selected_notes = []
    st.session_state.selected_warnings = []

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
    st.header("2. 預覽與調整項目")
    
    if 'cart' not in st.session_state or not st.session_state.cart:
        st.info("🛒 目前尚未加入任何項目，請從左側挑選。")
        return

    # --- 0. 準備與清理資料 ---
    df = pd.DataFrame(st.session_state.cart)

    # 🧹 終極殺蟲劑：徹底清除舊的「選取」欄位與系統隱藏亂碼
    cols_to_drop = [col for col in df.columns if col.startswith('_') or col == '選取' or col == '編號']
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # 🔢 重新插入乾淨的「編號」欄
    df.insert(0, '編號', range(1, len(df) + 1))

    # --- 1. 設定 AgGrid 的強大功能 ---
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # 🔒 全域設定：先全部設為「不可編輯」，避免點擊衝突
    gb.configure_default_column(editable=False, wrapText=True, autoHeight=True)
    
    # 🔓 針對需要的欄位開啟編輯功能 (✨ 這次把「單位」也加進來了！)
    editable_cols = ["品名", "數量", "單位", "單價"] 
    for col in editable_cols:
        if col in df.columns:
            gb.configure_column(col, editable=True)

    # ✨ 完美排版：把「選取框」跟「編號」結合在同一個欄位
    gb.configure_column(
        "編號",
        editable=False,
        width=100,
        checkboxSelection=True,       # 每一列的專屬打勾框
        headerCheckboxSelection=True, # 標題列的全選打勾框
        pinned="left"                 # 永遠固定在最左邊，往右滑也不會不見
    )
    
    # 設定多選模式
    gb.configure_selection(selection_mode="multiple", use_checkbox=False)
    
    gridOptions = gb.build()
    
    # 🛡️ 完美修復點擊衝突：禁止「點擊整列就選取」！
    # 這樣只有點擊最左邊的「勾選框」才會選取，點擊其他文字欄位就能專心「雙擊編輯」了！
    gridOptions['suppressRowClickSelection'] = True 

    st.markdown("💡 **操作提示**：點擊最左側勾選框可多選。**雙擊**品名、數量、單位或單價可直接修改。")
    
    # --- 2. 顯示表格 ---
    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True, 
        theme='streamlit', 
        height=400 
    )

    # --- 3. 同步資料回購物車 (保持資料庫乾淨) ---
    updated_df = grid_response['data']
    selected_rows = grid_response['selected_rows']

    # 存回購物車前，把「編號」跟「系統隱藏欄位」剃除掉
    cols_to_keep = [col for col in updated_df.columns if not col.startswith('_') and col != '編號']
    clean_df = updated_df[cols_to_keep]

    # 正式更新購物車
    st.session_state.cart = clean_df.to_dict('records')

    if selected_rows is not None and len(selected_rows) > 0:
        # 取出第一個被選取項目的「編號」，減 1 就是它在 list 中的真實 index
        if isinstance(selected_rows, pd.DataFrame):
            first_idx = int(selected_rows.iloc[0]['編號']) - 1
        else:
            first_idx = int(selected_rows[0]['編號']) - 1
        st.session_state.insert_index = first_idx
    else:
        # 如果取消選取，就清空插入點 (恢復加到最下方)
        st.session_state.insert_index = None

    col_del1, col_del2 = st.columns(2)
    
    with col_del1:
        if selected_rows is not None and len(selected_rows) > 0:
            st.warning(f"已選取 {len(selected_rows)} 個項目")
            if st.button("🗑️ 刪除選取的項目", type="primary", use_container_width=True):
                # 將勾選的項目轉換成乾淨的字典格式
                if isinstance(selected_rows, pd.DataFrame):
                    selected_dicts = selected_rows[cols_to_keep].to_dict('records')
                else:
                    selected_dicts = [{k: v for k, v in row.items() if not k.startswith('_') and k != '編號'} for row in selected_rows]
                
                # 從購物車移除選中的項目
                new_cart = [item for item in st.session_state.cart if item not in selected_dicts]
                st.session_state.cart = new_cart
                st.session_state.insert_index = None # 刪除後重置插入點
                st.rerun() # 重新整理畫面

    with col_del2:
        # 只要購物車有東西，就顯示清空按鈕
        if len(st.session_state.cart) > 0:
            st.markdown("<div style='margin-top:54px;'></div>", unsafe_allow_html=True) # 對齊左邊的按鈕高度
            if st.button("🚨 一鍵清空所有品項", type="secondary", use_container_width=True):
                st.session_state.cart = [] # 直接將購物車歸零
                st.session_state.insert_index = None # 重置插入點
                st.rerun()

# 🔹 Section 3: 條款與免責警語 (全新雙引擎階層版)
def render_section_3_notes(notation_db, warning_db):
    st.header("3. 條款與免責警語")
    
    flat_notations = [text for cat in notation_db.values() for text in cat.values()] if isinstance(notation_db, dict) else []
    flat_warnings = [text for cat in warning_db.values() for text in cat.values()] if isinstance(warning_db, dict) else []

    if 'selected_notes' not in st.session_state: st.session_state.selected_notes = []
    if 'selected_warnings' not in st.session_state: st.session_state.selected_warnings = []

    # ==========================================
    # 📝 區塊 A：專屬注意事項
    # ==========================================
    st.subheader("📝 專屬注意事項")
    st.markdown("**(固定條款)**")
    for sacred_note in SACRED_NOTES: st.markdown(f"🔒 `{sacred_note}`")
            
    dynamic_notes = get_dynamic_notes(st.session_state.cart)
    if dynamic_notes:
        st.markdown("**(自動觸發條款)**")
        for d_note in dynamic_notes: st.markdown(f"⚙️ `{d_note}`")

    st.markdown("<br>", unsafe_allow_html=True) 

    if st.button("✨ 讓 AI 自動判斷【注意事項】", type="secondary", use_container_width=True):
        if len(st.session_state.cart) == 0:
            st.warning("⚠️ 請先加入估價品項！")
        else:
            with st.spinner('AI 正在挑選注意事項...'):
                try:
                    ai_notes = generate_notations_by_llm(st.session_state.cart, notation_db)
                    for note in ai_notes:
                        if note not in st.session_state.selected_notes and note not in SACRED_NOTES and note not in dynamic_notes:
                            st.session_state.selected_notes.append(note)
                    st.rerun()
                except Exception as e:
                    st.error(f"錯誤: {str(e)}")

    col_n1, col_n2, col_n3 = st.columns([2, 3, 1])
    with col_n1:
        cat_n = st.selectbox("1. 選擇分類", ["請選擇..."] + list(notation_db.keys()), key="cat_n")
    with col_n2:
        if cat_n != "請選擇...":
            title_n = st.selectbox("2. 選擇條文", ["請選擇..."] + list(notation_db[cat_n].keys()), key="title_n")
        else:
            title_n = "請選擇..."
            st.selectbox("2. 選擇條文", ["請先選擇分類"], key="title_n_dummy")
    with col_n3:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ 加入", key="btn_add_n", use_container_width=True):
            if cat_n != "請選擇..." and title_n != "請選擇...":
                text = notation_db[cat_n][title_n]
                if text not in st.session_state.selected_notes:
                    st.session_state.selected_notes.append(text)
                    st.rerun()

    st.session_state.selected_notes = st.multiselect(
        "📝 目前已選的注意事項 (可點擊 X 刪除)：",
        options=list(set(st.session_state.selected_notes + flat_notations)),
        default=st.session_state.selected_notes
    )
    
    # ==========================================
    # ⚠️ 區塊 B：施工免責與警語
    # ==========================================
    st.subheader("⚠️ 施工免責與警語")

    if st.button("✨ 讓 AI 自動判斷【免責警語】", type="secondary", use_container_width=True):
        if len(st.session_state.cart) == 0:
            st.warning("⚠️ 請先加入估價品項！")
        else:
            with st.spinner('AI 正在挑選免責警語...'):
                try:
                    ai_warns = generate_warnings_by_llm(st.session_state.cart, warning_db)
                    for warn in ai_warns:
                        if warn not in st.session_state.selected_warnings and warn not in dynamic_notes:
                            st.session_state.selected_warnings.append(warn)
                    st.rerun()
                except Exception as e:
                    st.error(f"錯誤: {str(e)}")

    col_w1, col_w2, col_w3 = st.columns([2, 3, 1])
    with col_w1:
        cat_w = st.selectbox("1. 選擇分類", ["請選擇..."] + list(warning_db.keys()), key="cat_w")
    with col_w2:
        if cat_w != "請選擇...":
            title_w = st.selectbox("2. 選擇警語", ["請選擇..."] + list(warning_db[cat_w].keys()), key="title_w")
        else:
            title_w = "請選擇..."
            st.selectbox("2. 選擇警語", ["請先選擇分類"], key="title_w_dummy")
    with col_w3:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ 加入", key="btn_add_w", use_container_width=True):
            if cat_w != "請選擇..." and title_w != "請選擇...":
                text = warning_db[cat_w][title_w]
                if text not in st.session_state.selected_warnings:
                    st.session_state.selected_warnings.append(text)
                    st.rerun()

    st.session_state.selected_warnings = st.multiselect(
        "⚠️ 目前已選的免責警語 (可點擊 X 刪除)：",
        options=list(set(st.session_state.selected_warnings + flat_warnings)),
        default=st.session_state.selected_warnings
    )

    st.divider()
    st.button("🧹 點此清空所有手動加入的條款與警語", type="secondary", use_container_width=True, on_click=reset_notes)


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
    
    if uploaded_file: st.success(f"✅ 已載入歷史檔案：{uploaded_file.name}")

    current_notes = st.session_state.get('selected_notes', [])
    current_warnings = st.session_state.get('selected_warnings', [])
    dynamic_notes = get_dynamic_notes(st.session_state.cart)
    
    final_notes_to_export = SACRED_NOTES + dynamic_notes + current_notes + current_warnings

    if len(st.session_state.cart) > 0:
        excel_data = generate_excel(
            client_name, export_date, subtotal, tax, grand_total, 
            st.session_state.cart, final_notes_to_export, uploaded_file
        )
        file_name = f"{uploaded_file.name.replace('.xlsx', '')}_更新版.xlsx" if uploaded_file else f"{client_name if client_name else '未命名'}_估價單.xlsx"
        st.download_button(
            label="📥 匯出並下載 Excel", data=excel_data, file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary", use_container_width=True
        )
    else:
        st.warning("⚠️ 請先新增項目，方可匯出估價單。")