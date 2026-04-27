import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin - Multi-Export", layout="wide")

# --- 2. HÀM XUẤT EXCEL TỐI ƯU (DÀNH CHO CHỌN NHIỀU DÒNG) ---
def export_selected_to_excel(selected_df):
    try:
        if selected_df.empty:
            return None
        
        # Chuẩn bị dữ liệu kết xuất
        export_df = pd.DataFrame()
        export_df['STT'] = range(1, len(selected_df) + 1)
        
        # Ánh xạ dữ liệu từ database vào biểu mẫu
        export_df['ĐỊA DANH'] = selected_df['huyen_cu'].fillna('')
        export_df['TÊN KHÁCH HÀNG'] = selected_df['ten_don_vi'].fillna('').astype(str).str.upper()
        export_df['MÃ QUAN HỆ NGÂN SÁCH'] = selected_df['ma_qhns'].fillna('')
        export_df['MÃ KHÁCH HÀNG (SỐ SERIAL)'] = selected_df['san_pham'].fillna('')
        
        # Thông tin mặc định
        export_df['PHẦN MỀM'] = "KTHC"
        export_df['LOẠI CÀI ĐẶT'] = "Chuyển giao"
        export_df['NGÀY KÝ HỢP ĐỒNG'] = datetime.now().strftime("%d/%m/%Y")
        export_df['LÝ DO'] = "Cài mới"
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='NHAPLIEU')
            
            workbook = writer.book
            worksheet = writer.sheets['NHAPLIEU']
            
            # Định dạng Header
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25)
                
        return output.getvalue()
    except Exception as e:
        st.error(f"Lỗi kết xuất: {e}")
        return None

# --- 3. ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Quản trị HN11")
        u = st.text_input("Tài khoản")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- 4. TẢI DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # Sidebar
    with st.sidebar:
        st.header("📊 HỆ THỐNG")
        st.metric("Tổng đơn vị", len(df_raw))
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    st.title("📋 Quản lý & Kết xuất License")
    
    # Bộ lọc
    col_f1, col_f2 = st.columns([1, 3])
    with col_f1:
        vung = st.selectbox("Khu vực:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
    with col_f2:
        search = st.text_input("🔍 Tìm kiếm nhanh (Tên, MST...):")

    df_f = df_raw.copy()
    if vung != "Tất cả":
        df_f = df_f[df_f['huyen_cu'] == vung]
    if search:
        df_f = df_f[df_f.apply(lambda x: search.lower() in str(x.values).lower(), axis=1)]

    # --- BẢNG CHỌN NHIỀU (MULTI-ROW SELECTION) ---
    st.write("### Danh sách đơn vị (Tích chọn để kết xuất)")
    selection_events = st.dataframe(
        df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ma_qhns', 'san_pham']],
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row", # Cho phép chọn nhiều dòng
        key="data_table",
        on_select="rerun"
    )

    # Xử lý các dòng được chọn
    selected_indices = st.session_state.data_table.selection.rows
    if selected_indices:
        selected_df = df_f.iloc[selected_indices]
        num_selected = len(selected_df)
        
        st.success(f"Đang chọn **{num_selected}** đơn vị.")
        
        # Nút kết xuất cho danh sách đã chọn
        excel_data = export_selected_to_excel(selected_df)
        if excel_data:
            st.download_button(
                label=f"📥 TẢI TỆP EXCEL CHO {num_selected} ĐƠN VỊ ĐÃ CHỌN",
                data=excel_data,
                file_name=f"HN11_License_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
    else:
        st.info("💡 Vui lòng tích chọn các đơn vị trong bảng trên để bắt đầu kết xuất.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
