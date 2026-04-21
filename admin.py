import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from fpdf import FPDF

# --- 1. KẾT NỐI HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin - Full Info", layout="wide")

# --- 2. HÀM TẠO PDF (Sửa lỗi Undefined font B) ---
def export_pdf(row):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
            pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ CHI TIẾT", ln=True, align='C')
            pdf.set_font('ArialVN', size=11)
        else:
            pdf.set_font('Helvetica', size=12)
            pdf.cell(0, 10, txt="PHIEU THONG TIN (Thieu font arial.ttf)", ln=True, align='C')

        pdf.ln(10)
        
        # 12 trường thông tin đầy đủ
        labels = {
            "ten_don_vi": "1. Tên đơn vị",
            "mst": "2. Mã số thuế",
            "dia_chi": "3. Địa chỉ",
            "huyen_cu": "4. Khu vực (Huyện cũ)",
            "ma_qhns": "5. Mã QHNS",
            "so_tkkb": "6. Số tài khoản Kho bạc",
            "ma_kbnn": "7. Mã Kho bạc (KBNN)",
            "chu_tai_khoan": "8. Chủ tài khoản (Đại diện)",
            "chuc_vu": "9. Chức vụ",
            "ke_toan": "10. Kế toán trưởng/Phụ trách",
            "sdt_ke_toan": "11. Số điện thoại liên hệ",
            "san_pham": "12. Mã số máy (Phần mềm)"
        }

        for key, label in labels.items():
            val = str(row.get(key, "Trống"))
            # CHÚ Ý: Không dùng style='B' để tránh lỗi Undefined font
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
        
        pdf_output = pdf.output()
        return bytes(pdf_output) if isinstance(pdf_output, bytearray) else pdf_output
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Quản trị HN11")
        u = st.text_input("Tài khoản", key="login_u")
        p = st.text_input("Mật khẩu", type="password", key="login_p")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- 4. TÌM KIẾM & LỌC ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    with st.sidebar:
        st.title("🛡️ HN11 ADMIN")
        h_list = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
        sel_h = st.selectbox("Lọc theo vùng:", h_list)
        if st.button("🚪 Đăng xuất"): st.session_state.auth = False; st.rerun()

    df_filtered = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]
    
    # Tìm kiếm nhanh (đã bổ sung lại)
    search_q = st.text_input("🔎 Tìm kiếm nhanh (MST hoặc Tên)", placeholder="Nhập từ khóa...")
    df_f = df_filtered
    if search_q:
        df_f = df_filtered[df_filtered['mst'].astype(str).str.contains(search_q, case=False) | 
                           df_filtered['ten_don_vi'].str.contains(search_q, case=False)]

    # --- 5. BẢNG CHỌN ---
    st.info("💡 Click chọn một dòng để xem chi tiết & kết xuất.")
    event = st.dataframe(
        df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ke_toan']], 
        use_container_width=True, hide_index=True, 
        selection_mode="single-row", on_select="rerun"
    )

    # --- 6. HIỂN THỊ CHI TIẾT 12 TRƯỜNG ---
    if event.selection.rows:
        row = df_f.iloc[event.selection.rows[0]]
        st.divider()
        st.markdown(f"### 📋 CHI TIẾT: {row['ten_don_vi'].upper()}")
        
        full_labels = {
            "mst": "Mã số thuế", "ten_don_vi": "Tên đơn vị", "dia_chi": "Địa chỉ",
            "huyen_cu": "Khu vực", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK Kho bạc",
            "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "chuc_vu": "Chức vụ",
            "ke_toan": "Kế toán", "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã máy"
        }
        
        with st.container(border=True):
            keys = list(full_labels.keys())
            for i in range(0, len(keys), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(keys):
                        k = keys[i + j]
                        with cols[j]:
                            st.markdown(f"**📌 {full_labels[k]}**")
                            st.info(row.get(k, "Trống"))

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
                    pd.DataFrame([row]).to_excel(w, index=False)
                st.download_button("📊 TẢI EXCEL", buf.getvalue(), f"HN11_{row['mst']}.xlsx", use_container_width=True)
            with c2:
                pdf_bytes = export_pdf(row)
                if pdf_bytes:
                    st.download_button("📄 TẢI PDF", pdf_bytes, f"HN11_{row['mst']}.pdf", "application/pdf", use_container_width=True, type="primary")

except Exception as e:
    st.error(f"Lỗi: {e}")
