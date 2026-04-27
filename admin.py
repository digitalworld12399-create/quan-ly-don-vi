import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin - License Export", layout="wide")

# --- 2. HÀM XUẤT EXCEL CHUẨN (SỬA LỖI TIÊU ĐỀ VÀ THIẾU DỮ LIỆU) ---
def export_to_excel(selected_df):
    try:
        if selected_df.empty:
            return None
        
        # Tạo bảng dữ liệu mới để khớp chính xác với mẫu đính kèm
        export_data = []
        for i, (_, row) in enumerate(selected_df.iterrows(), 1):
            export_data.append({
                "STT": i,
                "ĐỊA DANH": row.get('huyen_cu', ''),
                "TÊN KHÁCH HÀNG": str(row.get('ten_don_vi', '')).upper(),
                "MÃ QUAN HỆ NGÂN SÁCH": row.get('ma_qhns', ''),
                "MÃ KHÁCH HÀNG (SỐ SERIAL)": row.get('san_pham', ''),
                "PHẦN MỀM": "KTHC",
                "LOẠI CÀI ĐẶT": "Chuyển giao",
                "NGÀY KÝ HỢP ĐỒNG": datetime.now().strftime("%d/%m/%Y"),
                "LÝ DO": "Cài mới"
            })
        
        final_df = pd.DataFrame(export_data)
        
        # Ghi file Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name='NHAPLIEU')
            
            workbook = writer.book
            worksheet = writer.sheets['NHAPLIEU']
            
            # Định dạng tiêu đề giống mẫu (màu xanh lá nhạt, chữ đậm)
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'
            })
            
            for col_num, value in enumerate(final_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25) # Chỉnh độ rộng cột cho dễ nhìn
                
        return output.getvalue()
    except Exception as e:
        st.error(f"Lỗi kết xuất Excel: {e}")
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

# --- 4. TẢI VÀ HIỂN THỊ DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    st.title("📋 Danh sách đơn vị & Kết xuất License")
    
    # Bộ lọc vùng
    vung = st.selectbox("Lọc theo khu vực:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
    df_f = df_raw if vung == "Tất cả" else df_raw[df_raw['huyen_cu'] == vung]

    # Bảng cho phép chọn nhiều dòng
    st.write("### Tích chọn các đơn vị cần cấp License:")
    event = st.dataframe(
        df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ma_qhns', 'san_pham']],
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row", # Cho phép chọn nhiều dòng
        key="data_table",
        on_select="rerun"
    )

    # Xử lý nút xuất file
    selected_rows = st.session_state.data_table.selection.rows
    if selected_rows:
        selected_df = df_f.iloc[selected_rows]
        st.success(f"Đã chọn **{len(selected_df)}** đơn vị.")
        
        excel_file = export_to_excel(selected_df)
        if excel_file:
            st.download_button(
                label=f"📥 TẢI TỆP EXCEL CHO {len(selected_df)} ĐƠN VỊ",
                data=excel_file,
                file_name=f"License_HN11_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
    else:
        st.info("💡 Hãy tích vào ô ở đầu dòng trong bảng trên để chọn các đơn vị muốn xuất tệp Excel.")

except Exception as e:
    st.error(f"Lỗi tải dữ liệu: {e}")
