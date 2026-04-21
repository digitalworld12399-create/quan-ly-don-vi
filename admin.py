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
        
        # Bắt buộc phải có file arial.ttf trong cùng thư mục
        font_path = "arial.ttf"
        
        if os.path.exists(font_path):
            # FPDF2: Không dùng tham số 'unicode', tự động nhận diện .ttf là unicode
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
            pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ HN11", ln=True, align='C')
            pdf.set_font('ArialVN', size=11)
        else:
            pdf.set_font('Helvetica', size=12)
            pdf.cell(0, 10, txt="PHIEU THONG TIN (Thieu font arial.ttf)", ln=True, align='C')

        pdf.ln(10)
        labels = {
            "mst": "Mã số thuế", "ten_don_vi": "Tên đơn vị", "dia_chi": "Địa chỉ", 
            "huyen_cu": "Khu vực", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK Kho bạc",
            "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "chuc_vu": "Chức danh",
            "ke_toan": "Kế toán", "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã máy DTSoft"
        }

        for key, label in labels.items():
            val = str(data_row.get(key, "")) if data_row.get(key) else "..."
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
        
        return pdf.output()
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. KIỂM TRA ĐĂNG NHẬP ---
if \"auth\" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🔐 Đăng nhập Quản trị")
        u = st.text_input("Tài khoản", key="admin_u")
        p = st.text_input("Mật khẩu", type="password", key="admin_p")
        if st.button("Xác nhận", use_container_width=True):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

# --- 4. TẢI DỮ LIỆU & TÌM KIẾM ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    with st.sidebar:
        st.title("🛡️ HN11 ADMIN")
        huyen_list = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
        sel_huyen = st.selectbox("Lọc theo vùng (Huyện cũ):", huyen_list)
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # Lọc theo vùng trước
    df_filtered = df_raw if sel_huyen == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_huyen]

    # CHỨC NĂNG TÌM KIẾM (Bổ sung lại)
    search_q = st.text_input("🔎 Tìm kiếm nhanh đơn vị", placeholder="Gõ Tên đơn vị hoặc Mã số thuế...")
    
    if search_q:
        df_f = df_filtered[
            df_filtered['mst'].astype(str).str.contains(search_q, case=False) | 
            df_filtered['ten_don_vi'].str.contains(search_q, case=False)
        ]
    else:
        df_f = df_filtered

    # --- 5. BẢNG HIỂN THỊ CHỌN DÒNG ---
    st.info("💡 **Hướng dẫn:** Click trực tiếp vào một dòng trong bảng để xem chi tiết & kết xuất.")
    
    event = st.dataframe(
        df_f, 
        use_container_width=True, 
        hide_index=True, 
        selection_mode="single-row", 
        on_select="rerun"
    )

    # --- 6. CHI TIẾT & KẾT XUẤT ---
    if event.selection.rows:
        row = df_f.iloc[event.selection.rows[0]]
        st.divider()
        st.subheader(f"🏢 ĐƠN VỊ: {row['ten_don_vi']}")
        
        with st.container(border=True):
            cols = st.columns(3)
            cols[0].write(f"**Mã số thuế:** {row['mst']}")
            cols[1].write(f"**Khu vực:** {row['huyen_cu']}")
            cols[2].write(f"**Kế toán:** {row.get('ke_toan', '...')}")
            
            st.divider()
            c1, c2 = st.columns(2)
            
            # Kết xuất Excel
            with c1:
                output_ex = io.BytesIO()
                with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                    pd.DataFrame([row]).to_excel(writer, index=False)
                st.download_button("📊 XUẤT EXCEL", output_ex.getvalue(), f"{row['mst']}.xlsx", use_container_width=True)
            
            # Kết xuất PDF (Đã sửa lỗi Unicode)
            with c2:
                pdf_bytes = export_pdf(row)
                if pdf_bytes:
                    st.download_button("📄 XUẤT PDF", pdf_bytes, f"{row['mst']}.pdf", "application/pdf", use_container_width=True, type="primary")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
