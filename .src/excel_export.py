import io
import openpyxl
from openpyxl.styles import Alignment
from copy import copy
import streamlit as st

def copy_worksheet_format_and_data(source_ws, target_ws):
    """將範本的儲存格內容、寬高、合併格式、顏色與字體完美複製到新的工作表中"""
    # 1. 複製合併儲存格
    for mcr in source_ws.merged_cells.ranges:
        target_ws.merge_cells(str(mcr))
        
    # 2. 複製欄寬
    for col_letter, col_dim in source_ws.column_dimensions.items():
        target_ws.column_dimensions[col_letter].width = col_dim.width
        
    # 3. 複製列高
    for row_idx, row_dim in source_ws.row_dimensions.items():
        target_ws.row_dimensions[row_idx].height = row_dim.height
            
    # 4. 複製儲存格資料與格式
    for row in source_ws.iter_rows():
        for cell in row:
            new_cell = target_ws.cell(row=cell.row, column=cell.column, value=cell.value)
            if cell.has_style:
                new_cell.font = copy(cell.font)
                new_cell.border = copy(cell.border)
                new_cell.fill = copy(cell.fill)
                new_cell.number_format = copy(cell.number_format)
                new_cell.protection = copy(cell.protection)
                new_cell.alignment = copy(cell.alignment)
                
    # 🌟 5. 新增：複製圖片 (如公司大小章)
    # 檢查範本是否有放圖片，有的話就複製過來，並放在同一個位置
    for img in source_ws._images:
        new_img = copy(img)
        target_ws.add_image(new_img, img.anchor)

def generate_excel(client_name, export_date, subtotal, tax, grand_total, cart, selected_notes, uploaded_file=None):
    # 先載入我們的標準空白範本
    template_wb = openpyxl.load_workbook("blank_form.xlsx")
    source_ws = template_wb.active
    
    # 判斷使用者是否有上傳客戶的歷史檔案
    if uploaded_file is not None:
        wb = openpyxl.load_workbook(uploaded_file)
        
        # 設定新工作表的名稱 (例如：0314_報價)
        sheet_title = f"{export_date.month:02d}{export_date.day:02d}_報價"
        # 確保工作表名稱不重複
        base_title = sheet_title
        counter = 1
        while sheet_title in wb.sheetnames:
            sheet_title = f"{base_title}_{counter}"
            counter += 1
            
        # 在客戶檔案中建立新工作表，並複製範本過去
        ws = wb.create_sheet(title=sheet_title)
        copy_worksheet_format_and_data(source_ws, ws)
        wb.active = ws  # 切換到新建立的這張表準備寫入
    else:
        # 沒有上傳檔案，直接使用空白範本
        wb = template_wb
        ws = wb.active
        if client_name:
            ws.title = str(client_name)[:31] # Excel 工作表名稱限制 31 字元

    # ================= 以下寫入邏輯不變 =================
    # 1. 填寫 TO 與日期 (固定在第 6 列)
    ws.cell(row=6, column=2).value = client_name
    
    minguo_year = export_date.year - 1911
    date_str = f"{minguo_year}/{export_date.month}/{export_date.day}"
    ws.cell(row=6, column=6).value = date_str
    
    # 2. 填寫購物車內的項目
    current_row = 8
    for idx, item in enumerate(cart):
        if "小計" in str(ws.cell(row=current_row, column=5).value).strip():
            st.warning("項目數量超過表單預留空間，部分項目可能未匯出。")
            break
            
        ws.cell(row=current_row, column=1).value = idx + 1               
        ws.cell(row=current_row, column=2).value = item.get("品名", "")  
        ws.cell(row=current_row, column=3).value = item.get("數量", 0)   
        ws.cell(row=current_row, column=4).value = item.get("單位", "")  
        ws.cell(row=current_row, column=5).value = item.get("單價", 0)   
        ws.cell(row=current_row, column=6).value = item.get("金額", 0)   
        current_row += 1

    # 3. 尋找底部的「小計」
    subtotal_row = -1
    for r in range(current_row, current_row + 100):
        cell_val = str(ws.cell(row=r, column=5).value).strip()
        
        if "小計" in cell_val:
            subtotal_row = r
            ws.cell(row=r, column=6).value = subtotal       
            ws.cell(row=r+1, column=6).value = tax          
            ws.cell(row=r+2, column=6).value = grand_total  
            break

    # 4. 完美接合與動態對齊格式
    if subtotal_row != -1 and subtotal_row > current_row:
        # 防當機掃雷魔法
        ranges_to_unmerge = []
        for m_range in ws.merged_cells.ranges:
            if not (m_range.max_row < current_row or m_range.min_row >= subtotal_row):
                ranges_to_unmerge.append(m_range)
        for m_range in ranges_to_unmerge:
            ws.unmerge_cells(str(m_range))
            
        rows_to_delete = subtotal_row - current_row
        ws.delete_rows(current_row, amount=rows_to_delete)
        
        new_subtotal_row = current_row
        
        right_align = Alignment(horizontal='right')
        for i in range(3):
            ws.cell(row=new_subtotal_row + i, column=5).alignment = right_align
        
        notes_row = -1
        for r in range(new_subtotal_row + 3, new_subtotal_row + 15):
            if str(ws.cell(row=r, column=1).value).strip() != "":
                notes_row = r
                break
        
        if notes_row != -1:
            notes_text = ""
            for i, note in enumerate(selected_notes):
                notes_text += f"{i+1}. {note}\n"
            
            ws.cell(row=notes_row, column=1).value = notes_text.strip()
            ws.cell(row=notes_row, column=1).alignment = Alignment(wrap_text=True, vertical='top')
            
            lines_needed = max(5, len(notes_text) // 40 + len(selected_notes))
            ws.merge_cells(start_row=notes_row, start_column=1, end_row=notes_row + lines_needed, end_column=7)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output