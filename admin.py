import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from fpdf import FPDF
import plotly.express as px
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM XUẤT EXCEL (SỬA LỖI LẤY SỐ LIỆU CỘT B, C, D, E) ---
def export_special_excel(df):
    try:
        if df.empty:
            return None
        
        # Tạo DataFrame mới theo cấu trúc biểu mẫu yêu cầu
        export_df = pd.DataFrame()
        
        # Cột A: STT
        export_df['STT'] = range(1, len(df) + 1)
        
        # Cột B: ĐỊA DANH (Lấy từ huyen_cu)
        export_df['ĐỊA DANH'] = df['huyen_cu'].fillna('')
        
        # Cột C: TÊN KHÁCH HÀNG (Lấy từ ten_don_vi và viết hoa)
        export_df['TÊN KHÁCH HÀNG'] = df['ten_don_vi'].fillna('').astype(str).str.upper()
        
        # Cột D: MÃ QUAN HỆ NGÂN SÁCH (Lấy từ ma_qhns)
        export_df['MÃ QUAN HỆ NGÂN SÁCH'] = df['ma_qhns'].fillna('')
        
        # Cột E: MÃ KHÁCH HÀNG (SỐ SERIAL) (Lấy từ san_pham)
        export_df['MÃ KHÁCH HÀNG (SỐ SERIAL)'] = df['san_pham'].fillna('')
        
        # Cột F, G, H, I: Các giá trị mặc định
        export_df['PHẦN MỀM'] = "KTHC"
        export_df['LOẠI CÀI ĐẶT'] = "Chuyển giao"
        export_df['NGÀY KÝ HỢP ĐỒNG'] = datetime.now().strftime("%d/%m/%Y")
        export_df['LÝ DO'] = "Cài mới"
        
        # Xuất ra file Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='NHAPLIEU')
            
            workbook = writer.book
            worksheet = writer.sheets['NHAPLIEU']
            
            # Định dạng Header cho đẹp
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'
            })
            
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25) # Chỉnh độ rộng cột
                
        return output.getvalue()
    except Exception as e:
        st.error(f"Lỗi xuất Excel: {e}")
        return None

# --- 3. GIAO DIỆN ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Hệ thống Quản trị HN11")
        u = st.text_input("Tài khoản")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- 4. TẢI DỮ LIỆU VÀ HIỂN THỊ ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # Sidebar: Thống kê nhanh
    with st.sidebar:
        st.header("📊 DASHBOARD")
        st.metric("Tổng đơn vị", len(df_raw))
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # Màn hình chính
    tab_list, tab_analysis = st.tabs(["📋 QUẢN LÝ", "📈 PHÂN TÍCH"])
    
    with tab_list:
        search = st.text_input("🔍 Tìm kiếm đơn vị (MST, Tên...):")
        df_f = df_raw.copy()
        if search:
            df_f = df_f[df_f.apply(lambda x: search.lower() in str(x.values).lower(), axis=1)]
        
        st.dataframe(df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ma_qhns', 'san_pham']], 
                     use_container_width=True, hide_index=True, selection_mode="single-row", key="tbl", on_select="rerun")
        
        # NÚT XUẤT TỔNG HỢP (XUẤT TOÀN BỘ DANH SÁCH ĐANG LỌC)
        if not df_f.empty:
            st.download_button("📝 XUẤT MẪU CẤP LICENSE (TỔNG HỢP)", 
                             export_special_excel(df_f), "Mau_License_Tong_Hop.xlsx", 
                             type="primary", use_container_width=True)

        # CHI TIẾT DÒNG ĐANG CHỌN
        if st.session_state.tbl.selection.rows:
            idx = st.session_state.tbl.selection.rows[0]
            row = df_f.iloc[idx]
            st.divider()
            
            st.subheader(f"🛠️ Đang chọn: {row['ten_don_vi']}")
            
            col_a, col_b = st.columns(2)
            with col_a:
                # Nút xuất lẻ cho 1 đơn vị
                single_excel = export_special_excel(pd.DataFrame([row]))
                st.download_button(f"📊 XUẤT MẪU LICENSE: {row['mst']}", 
                                 single_excel, f"License_{row['mst']}.xlsx", use_container_width=True)
            with col_b:
                st.info("💡 Lưu ý: Hệ thống đã lấy thông tin từ 'huyen_cu', 'ten_don_vi', 'ma_qhns' và 'san_pham' để điền vào tệp Excel.")

except Exception as e:
    st.error(f"Lỗi: {e}")
