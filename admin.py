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

st.set_page_config(page_title="HN11 Admin - Multi-License", layout="wide")

# --- 2. HÀM XUẤT EXCEL CHUẨN BIỂU MẪU (SỬA LỖI TRỐNG DỮ LIỆU) ---
def export_to_excel(selected_df):
    try:
        if selected_df.empty:
            return None
        
        # Tạo cấu trúc DataFrame mới đúng theo biểu mẫu yêu cầu
        export_df = pd.DataFrame()
        export_df['STT'] = range(1, len(selected_df) + 1)
        
        # Ánh xạ dữ liệu từ cột Database vào cột Excel (Sửa lỗi cột B, C, D, E)
        # B: ĐỊA DANH
        export_df['ĐỊA DANH'] = selected_df['huyen_cu'].fillna('')
        # C: TÊN KHÁCH HÀNG (Viết hoa toàn bộ)
        export_df['TÊN KHÁCH HÀNG'] = selected_df['ten_don_vi'].fillna('').apply(lambda x: str(x).upper())
        # D: MÃ QUAN HỆ NGÂN SÁCH
        export_df['MÃ QUAN HỆ NGÂN SÁCH'] = selected_df['ma_qhns'].fillna('')
        # E: MÃ KHÁCH HÀNG (SỐ SERIAL)
        export_df['MÃ KHÁCH HÀNG (SỐ SERIAL)'] = selected_df['san_pham'].fillna('')
        
        # F, G, H, I: Các giá trị mặc định
        export_df['PHẦN MỀM'] = "KTHC"
        export_df['LOẠI CÀI ĐẶT'] = "Chuyển giao"
        export_df['NGÀY KÝ HỢP ĐỒNG'] = datetime.now().strftime("%d/%m/%Y")
        export_df['LÝ DO'] = "Cài mới"
        
        # Ghi vào file Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='NHAPLIEU')
            workbook = writer.book
            worksheet = writer.sheets['NHAPLIEU']
            
            # Định dạng Header chuẩn
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25) # Độ rộng cột
                
        return output.getvalue()
    except Exception as e:
        st.error(f"Lỗi logic xuất Excel: {e}")
        return None

# --- 3. ĐĂNG NHẬP ---
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

# --- 4. TẢI VÀ XỬ LÝ DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    with st.sidebar:
        st.header("📊 DASHBOARD")
        st.metric("Tổng đơn vị", len(df_raw))
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    st.title("📋 Quản lý & Kết xuất License")
    
    # Bộ lọc tìm kiếm
    c1, c2 = st.columns([1, 2])
    vung = c1.selectbox("Vùng:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
    search = c2.text_input("🔍 Tìm nhanh (Tên, MST, SĐT...):")

    df_f = df_raw.copy()
    if vung != "Tất cả": df_f = df_f[df_f['huyen_cu'] == vung]
    if search:
        df_f = df_f[df_f.apply(lambda x: search.lower() in str(x.values).lower(), axis=1)]

    # --- BẢNG HIỂN THỊ CHỌN NHIỀU ---
    st.write("### Danh sách đơn vị (Tích chọn để kết xuất)")
    selection = st.dataframe(
        df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ma_qhns', 'san_pham']],
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row", # CHO PHÉP CHỌN NHIỀU
        key="data_table",
        on_select="rerun"
    )

    # --- XỬ LÝ KẾT XUẤT ---
    selected_indices = st.session_state.data_table.selection.rows
    
    if selected_indices:
        selected_df = df_f.iloc[selected_indices]
        st.success(f"Đã chọn **{len(selected_df)}** đơn vị.")
        
        # Nút xuất Excel cho các đơn vị đã chọn
        excel_file = export_to_excel(selected_df)
        if excel_file:
            st.download_button(
                label=f"📥 TẢI FILE EXCEL ({len(selected_df)} ĐƠN VỊ)",
                data=excel_file,
                file_name=f"License_HN11_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
    else:
        st.info("💡 Mẹo: Bạn hãy tích vào ô đầu dòng trong bảng để chọn một hoặc nhiều đơn vị cần xuất file.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
