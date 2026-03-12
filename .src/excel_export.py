import io
import openpyxl
from openpyxl.styles import Alignment
import streamlit as st

def generate_excel(client_name, export_date, subtotal, tax, grand_total, cart, selected_notes):
    """
    負責寫入資料、刪除空白列、解除隱藏合併、並匯出 Excel 二進位檔
    """
    wb = openpyxl.load_workbook("blank_form.xlsx")
    ws = wb.active
    
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
        # 🛡️ 防當機掃雷魔法：強制解除預計刪除區間內的合併儲存格
        ranges_to_unmerge = []
        for m_range in ws.merged_cells.ranges:
            if not (m_range.max_row < current_row or m_range.min_row >= subtotal_row):
                ranges_to_unmerge.append(m_range)
        for m_range in ranges_to_unmerge:
            ws.unmerge_cells(str(m_range))
            
        # 刪除多餘空白列
        rows_to_delete = subtotal_row - current_row
        ws.delete_rows(current_row, amount=rows_to_delete)
        
        new_subtotal_row = current_row
        
        # 靠右對齊小計區塊
        right_align = Alignment(horizontal='right')
        for i in range(3):
            ws.cell(row=new_subtotal_row + i, column=5).alignment = right_align
        
        # 寫入並合併注意事項
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