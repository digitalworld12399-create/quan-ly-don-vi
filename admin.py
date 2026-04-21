import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import io
import os
from fpdf import FPDF

# --- 1. KẾT NỐI HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 - Admin Dashboard", layout="wide", page_icon="🛡️")

# --- 2. HÀM TẠO PDF TIẾNG VIỆT (Sửa lỗi Unicode) ---
def export_pdf(data_row):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Đường dẫn tới file font arial.ttf (phải nằm cùng thư mục code)
        font_path = "arial.ttf"
        
        if os.path.exists(font_path):
            pdf.add_font('ArialCustom', '', font_path, unicode=True)
            pdf.set_font('ArialCustom', size=14)
            pdf.cell(200, 10, txt="PHIẾU THÔNG TIN ĐƠN VỊ HN11", ln=True, align='C')
            pdf.set_font('ArialCustom', size=11)
        else:
            # Nếu không thấy file font, dùng font mặc định (nhưng sẽ lỗi tiếng Việt)
            pdf.set_font('Helvetica', size=12)
            pdf.cell(200, 10, txt="PHIEU THONG TIN (LOI FONT)", ln=True, align='C')
            st.error("Thiếu file arial.ttf để hiển thị tiếng Việt PDF!")

        pdf.ln(10)
        labels = {
            "mst": "Mã số thuế", "ten_don_vi": "Tên đơn vị", "dia_chi": "Địa chỉ", 
            "huyen_cu": "Khu vực", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK Kho bạc",
            "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "chuc_vu": "Chức danh",
            "ke_toan": "Kế toán", "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã máy DTSoft"
        }

        for key, label in labels.items():
            val = str(data_row.get(key, "")) if data_row.get(key) else "..."
            # Sử dụng multi_cell để tự động xuống dòng nếu text quá dài
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(2)
        
        return pdf.output(dest='S')
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. KIỂM TRA ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    _, col_login, _ = st.columns([1.5, 1, 1.5])
    with col_login:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🔐 HN11 LOGIN</h3>", unsafe_allow_html=True)
            u = st.text_input("Tài khoản", key="user_login")
            p = st.text_input("Mật khẩu", type="password", key="pass_login")
            if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
                if u == "kh" and p == "a11": 
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Sai thông tin!")
    st.stop()

# --- 4. TẢI VÀ LỌC DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    with st.sidebar:
        st.header("🛡️ HN11 ADMIN")
        list_huyen = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
        sel_huyen = st.selectbox("Lọc theo Huyện cũ:", list_huyen)
        df_filtered = df_raw if sel_huyen == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_huyen]
        
        st.divider()
        st.link_button("🔄 KIỂM TRA CẬP NHẬT", "https://your-storage-link.com", use_container_width=True)
        if st.button("🚪 Đăng xuất", use_container_width=True): 
            st.session_state.auth = False
            st.rerun()

    st.markdown("### 📊 QUẢN LÝ DỮ LIỆU HN11")
    
    # Chức năng tìm kiếm thông tin trước đó
    search_q = st.text_input("🔎 Tìm kiếm thông tin", placeholder="Nhập Mã số thuế hoặc Tên đơn vị để tìm...")
    
    if search_q:
        df_f = df_filtered[
            df_filtered['mst'].astype(str).str.contains(search_q, case=False) | 
            df_filtered['ten_don_vi'].str.contains(search_q, case=False)
        ]
    else:
        df_f = df_filtered

    # --- 5. BẢNG HIỂN THỊ CHỌN DÒNG ---
    st.caption("💡 Mẹo: Click chọn (chếch) vào một dòng để xem chi tiết & kết xuất.")
    event = st.dataframe(
        df_f, 
        use_container_width=True, 
        hide_index=True, 
        selection_mode="single-row", 
        on_select="rerun"
    )

    selected_rows = event.selection.rows

    # --- 6. CHI TIẾT & KẾT XUẤT ---
    if len(selected_rows) > 0:
        row = df_f.iloc[selected_rows[0]]
        st.divider()
        st.markdown(f"#### 📋 CHI TIẾT: {row['ten_don_vi'].upper()}")
        
        # Grid hiển thị thông tin
        with st.container(border=True):
            display_labels = {
                "mst": "Mã số thuế", "ten_don_vi": "Tên đơn vị", "dia_chi": "Địa chỉ", 
                "huyen_cu": "Khu vực", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK Kho bạc",
                "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "chuc_vu": "Chức danh",
                "ke_toan": "Kế toán", "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã máy DTSoft"
            }
            c_info = st.columns(3)
            for i, (k, l) in enumerate(display_labels.items()):
                with c_info[i % 3]:
                    st.markdown(f"**{l}**")
                    st.info(row.get(k, "Trống"))

            st.divider()
            c1, c2 = st.columns(2)
            
            # Kết xuất Excel
            with c1:
                output_ex = io.BytesIO()
                with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                    pd.DataFrame([row]).to_excel(writer, index=False)
                st.download_button(f"📊 TẢI EXCEL", output_ex.getvalue(), f"{row['mst']}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            # Kết xuất PDF (Đã sửa Unicode)
            with c2:
                pdf_bytes = export_pdf(row)
                if pdf_bytes:
                    st.download_button(f"📄 TẢI PDF (TIẾNG VIỆT)", pdf_bytes, f"{row['mst']}.pdf", "application/pdf", use_container_width=True, type="primary")
    else:
        st.info("👆 Vui lòng chọn một đơn vị trong danh sách trên.")

except Exception as e:
    st.error(f"🚨 Lỗi hệ thống: {e}")
