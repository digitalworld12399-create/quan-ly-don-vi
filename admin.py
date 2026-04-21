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

# --- 2. HÀM TẠO PDF TIẾNG VIỆT (Dùng fpdf2) ---
def export_pdf(data_row):
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = "arial.ttf"
        
        if os.path.exists(font_path):
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
        st.error(f"Lỗi PDF: {e}")
        return None

# --- 3. ĐĂNG NHẬP ---
if "auth" not in st.session_state: 
    st.session_state.auth = False

if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🔐 Quản trị HN11")
        u = st.text_input("Tài khoản", key="login_u")
        p = st.text_input("Mật khẩu", type="password", key="login_p")
        if st.button("Đăng nhập", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: 
                st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

# --- 4. TẢI DỮ LIỆU & TÌM KIẾM ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    with st.sidebar:
        st.title("🛡️ HN11 ADMIN")
        huyen_list = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
        sel_huyen = st.selectbox("Lọc theo vùng:", huyen_list)
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    df_filtered = df_raw if sel_huyen == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_huyen]

    # Thanh tìm kiếm nhanh
    search_q = st.text_input("🔎 Tìm kiếm nhanh", placeholder="Nhập Tên đơn vị hoặc Mã số thuế...")
    
    if search_q:
        df_f = df_filtered[
            df_filtered['mst'].astype(str).str.contains(search_q, case=False) | 
            df_filtered['ten_don_vi'].str.contains(search_q, case=False)
        ]
    else:
        df_f = df_filtered

    # --- 5. BẢNG HIỂN THỊ ---
    st.info("💡 Click chọn một dòng bên dưới để xem chi tiết.")
    event = st.dataframe(
        df_f, 
        use_container_width=True, 
        hide_index=True, 
        selection_mode="single-row", 
        on_select="rerun"
    )

    # --- 6. CHI TIẾT ---
    if event.selection.rows:
        row = df_f.iloc[event.selection.rows[0]]
        st.divider()
        st.subheader(f"🏢 {row['ten_don_vi']}")
        
        with st.container(border=True):
            cols = st.columns(3)
            cols[0].write(f"**MST:** {row['mst']}")
            cols[1].write(f"**Vùng:** {row['huyen_cu']}")
            cols[2].write(f"**Mã máy:** {row.get('san_pham', '...')}")
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                output_ex = io.BytesIO()
                with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                    pd.DataFrame([row]).to_excel(writer, index=False)
                st.download_button("📊 XUẤT EXCEL", output_ex.getvalue(), f"{row['mst']}.xlsx", use_container_width=True)
            with c2:
                pdf_data = export_pdf(row)
                if pdf_data:
                    st.download_button("📄 XUẤT PDF", pdf_data, f"{row['mst']}.pdf", "application/pdf", use_container_width=True, type="primary")

except Exception as e:
    st.error(f"Lỗi: {e}")
