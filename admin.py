import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from fpdf import FPDF

# --- 1. KẾT NỐI ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin", layout="wide")

# --- 2. HÀM TẠO PDF (SỬA LỖI BINARY) ---
def export_pdf(data_row):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Nạp font tiếng Việt
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
            "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "ke_toan": "Kế toán",
            "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã máy DTSoft"
        }

        for key, label in labels.items():
            val = str(data_row.get(key, "")) if data_row.get(key) else "..."
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
        
        # QUAN TRỌNG: Ép kiểu dữ liệu về 'bytes' để Streamlit không bị lỗi
        pdf_output = pdf.output()
        if isinstance(pdf_output, bytearray):
            return bytes(pdf_output)
        return pdf_output
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        u = st.text_input("Tài khoản", key="u_ad")
        p = st.text_input("Mật khẩu", type="password", key="p_ad")
        if st.button("Đăng nhập", use_container_width=True):
            if u == "kh" and p == "a11": st.session_state.auth = True; st.rerun()
            else: st.error("Sai!")
    st.stop()

# --- 4. TẢI DỮ LIỆU & TÌM KIẾM ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    with st.sidebar:
        st.header("🛡️ HN11 ADMIN")
        h_list = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
        sel_h = st.selectbox("Lọc vùng:", h_list)
        if st.button("🚪 Đăng xuất"): st.session_state.auth = False; st.rerun()

    df_filtered = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]

    # Bổ sung thanh tìm kiếm
    search = st.text_input("🔎 Tìm kiếm theo MST hoặc Tên đơn vị")
    df_f = df_filtered
    if search:
        df_f = df_filtered[df_filtered['mst'].astype(str).str.contains(search, case=False) | 
                           df_filtered['ten_don_vi'].str.contains(search, case=False)]

    # --- 5. BẢNG CHỌN DÒNG ---
    st.info("💡 Click chọn một dòng để xem chi tiết & kết xuất.")
    event = st.dataframe(df_f, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")

    if event.selection.rows:
        row = df_f.iloc[event.selection.rows[0]]
        st.divider()
        st.subheader(f"🏢 {row['ten_don_vi']}")
        
        with st.container(border=True):
            c1, c2 = st.columns(2)
            
            # Xuất Excel
            with c1:
                buffer_ex = io.BytesIO()
                with pd.ExcelWriter(buffer_ex, engine='xlsxwriter') as writer:
                    pd.DataFrame([row]).to_excel(writer, index=False)
                st.download_button("📊 TẢI EXCEL", buffer_ex.getvalue(), f"{row['mst']}.xlsx", use_container_width=True)
            
            # Xuất PDF (Đã fix lỗi bytearray)
            with c2:
                pdf_bytes = export_pdf(row)
                if pdf_bytes:
                    st.download_button("📄 TẢI PDF", pdf_bytes, f"{row['mst']}.pdf", "application/pdf", use_container_width=True, type="primary")

except Exception as e:
    st.error(f"Lỗi: {e}")
