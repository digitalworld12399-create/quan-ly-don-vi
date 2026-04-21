import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import io
import re
from fpdf import FPDF

# --- 1. KẾT NỐI HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 - Admin Dashboard", layout="wide", page_icon="🛡️")

# --- 2. HÀM TẠO PDF TIẾNG VIỆT ---
def export_pdf(data_row):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Lưu ý: Bạn cần file font 'arial.ttf' trong cùng thư mục để hiển thị tiếng Việt
        # Nếu chưa có, PDF sẽ bị lỗi font hoặc bạn có thể dùng font mặc định (không dấu)
        try:
            pdf.add_font('Arial', '', 'arial.ttf', unicode=True)
            pdf.set_font('Arial', size=12)
        except:
            pdf.set_font('Arial', size=12)

        pdf.cell(200, 10, txt="PHIẾU THÔNG TIN ĐƠN VỊ HN11", ln=True, align='C')
        pdf.ln(10)

        labels = {
            "mst": "Mã số thuế", "ten_don_vi": "Tên đơn vị", "dia_chi": "Địa chỉ", 
            "huyen_cu": "Khu vực", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK Kho bạc",
            "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "chuc_vu": "Chức danh",
            "ke_toan": "Kế toán", "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã máy DTSoft"
        }

        for key, label in labels.items():
            val = str(data_row.get(key, ""))
            pdf.multi_cell(0, 10, txt=f"{label}: {val}")
        
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
            u = st.text_input("Tài khoản")
            p = st.text_input("Mật khẩu", type="password")
            if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
                if u == "kh" and p == "a11": st.session_state.auth = True; st.rerun()
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
        if st.button("🚪 Đăng xuất", use_container_width=True): st.session_state.auth = False; st.rerun()

    st.markdown("### 📊 QUẢN LÝ DỮ LIỆU HN11")
    search_q = st.text_input("🔎 Tìm kiếm thông tin", placeholder="Nhập MST hoặc Tên đơn vị...")
    
    if search_q:
        df_f = df_filtered[df_filtered['mst'].astype(str).str.contains(search_q, case=False) | 
                           df_filtered['ten_don_vi'].str.contains(search_q, case=False)]
    else:
        df_f = df_filtered

    # --- 5. BẢNG CHỌN DÒNG ---
    event = st.dataframe(df_f, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")
    selected_rows = event.selection.rows

    # --- 6. CHI TIẾT & KẾT XUẤT ---
    if len(selected_rows) > 0:
        row = df_f.iloc[selected_rows[0]]
        st.divider()
        st.markdown(f"#### 📋 CHI TIẾT: {row['ten_don_vi'].upper()}")
        
        with st.container(border=True):
            # Hiển thị thông tin
            c_info = st.columns(3)
            # (Phần hiển thị grid 3 cột tương tự các bản trước...)
            for i, (k, l) in enumerate({"mst":"MST", "ten_don_vi":"Tên", "dia_chi":"Địa chỉ", "huyen_cu":"Vùng", "ma_qhns":"QHNS", "ke_toan":"Kế toán"}.items()):
                with c_info[i % 3]: st.write(f"**{l}:** {row.get(k, '')}")

            st.divider()
            c1, c2 = st.columns(2)
            
            # 1. Kết xuất Excel
            with c1:
                output_ex = io.BytesIO()
                with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                    pd.DataFrame([row]).to_excel(writer, index=False)
                st.download_button(f"📊 TẢI EXCEL", output_ex.getvalue(), f"{row['mst']}.xlsx", use_container_width=True)
            
            # 2. Kết xuất PDF
            with c2:
                pdf_bytes = export_pdf(row)
                if pdf_bytes:
                    st.download_button(f"📄 TẢI PDF", pdf_bytes, f"{row['mst']}.pdf", "application/pdf", use_container_width=True, type="primary")

except Exception as e:
    st.error(f"🚨 Lỗi: {e}")
