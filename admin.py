import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
import qrcode
from PIL import Image
from fpdf import FPDF
import plotly.express as px
from datetime import datetime
import tempfile

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM XUẤT PDF + QR CODE ---
def export_pdf(row):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_qr:
        qr_path = tmp_qr.name
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path, uni=True)
            pdf.set_font('ArialVN', size=16)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', 'B', size=16)
            font_name = 'Helvetica'

        # Tạo mã QR
        mst = str(row.get('mst', 'N/A'))
        ten_dv = str(row.get('ten_don_vi', ''))
        qr_content = f"MST: {mst}\nDon vi: {ten_dv}"
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_path)
        
        pdf.image(qr_path, x=165, y=10, w=30)

        # Tiêu đề
        pdf.set_font(font_name, size=16)
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        
        # Các trường thông tin cần xuất
        fields = [
            ("Mã số thuế", row.get('mst')),
            ("Tên đơn vị", str(row.get('ten_don_vi', '')).upper()),
            ("Địa chỉ", row.get('dia_chi')),
            ("Khu vực (Huyện cũ)", row.get('huyen_cu')),
            ("Họ tên Thủ trưởng", row.get('chu_tai_khoan')),
            ("Chức vụ", row.get('chuc_vu')),
            ("Họ tên Kế toán", row.get('ke_toan')),
            ("Số điện thoại", row.get('sdt_ke_toan')),
            ("Số tài khoản", row.get('so_tkkb')),
            ("Mã QHNS", row.get('ma_qhns')),
            ("Mã máy (Serial)", row.get('san_pham'))
        ]
        
        for label, val in fields:
            pdf.multi_cell(0, 8, txt=f"{label}: {val if val else ''}")
            pdf.ln(1)
            
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return b""
    finally:
        if os.path.exists(qr_path): os.remove(qr_path)

# --- 3. GIAO DIỆN ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Hệ thống Quản trị HN11")
        u = st.text_input("Tài khoản Admin")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin đăng nhập!")
    st.stop()

# --- 4. TẢI DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    if not df_raw.empty:
        df_raw['ten_don_vi'] = df_raw['ten_don_vi'].str.upper()

    # SIDEBAR
    with st.sidebar:
        st.header("📊 DASHBOARD")
        st.metric("Tổng đơn vị", len(df_raw))
        st.divider()
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # MÀN HÌNH CHÍNH
    st.subheader("📋 DANH SÁCH ĐƠN VỊ")
    search_q = st.text_input("🔍 Tìm kiếm nhanh (Tên, MST, SĐT...)", placeholder="Nhập nội dung cần tìm...")
    
    df_f = df_raw
    if search_q:
        q = search_q.lower()
        df_f = df_f[df_f.apply(lambda x: q in str(x.values).lower(), axis=1)]

    st.dataframe(
        df_f[['mst', 'ten_don_vi', 'huyen_cu', 'chu_tai_khoan', 'ke_toan', 'sdt_ke_toan']],
        use_container_width=True, hide_index=True,
        selection_mode="single-row", key="table_select", on_select="rerun"
    )

    # XỬ LÝ KHI CHỌN DÒNG
    if st.session_state.table_select.selection.rows:
        idx = st.session_state.table_select.selection.rows[0]
        row = df_f.iloc[idx]
        
        st.divider()
        st.subheader(f"🛠️ CHI TIẾT & CẬP NHẬT: {row['ten_don_vi']}")
        
        # FORM SỬA VÀ LƯU
        with st.form("edit_update_form"):
            col1, col2 = st.columns(2)
            up = {}
            with col1:
                up['ten_don_vi'] = st.text_input("Tên đơn vị", value=row.get('ten_don_vi', ''))
                up['mst'] = st.text_input("Mã số thuế", value=row.get('mst', ''))
                up['dia_chi'] = st.text_input("Địa chỉ", value=row.get('dia_chi', ''))
                up['huyen_cu'] = st.text_input("Huyện cũ (Khu vực)", value=row.get('huyen_cu', ''))
                up['so_tkkb'] = st.text_input("Số tài khoản", value=row.get('so_tkkb', ''))
            with col2:
                up['chu_tai_khoan'] = st.text_input("Họ tên Thủ trưởng", value=row.get('chu_tai_khoan', ''))
                up['chuc_vu'] = st.text_input("Chức vụ", value=row.get('chuc_vu', ''))
                up['ke_toan'] = st.text_input("Họ tên Kế toán", value=row.get('ke_toan', ''))
                up['sdt_ke_toan'] = st.text_input("Số điện thoại", value=row.get('sdt_ke_toan', ''))
                up['san_pham'] = st.text_input("Mã máy (Serial)", value=row.get('san_pham', ''))

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.form_submit_button("💾 LƯU THAY ĐỔI", type="primary", use_container_width=True):
                    up['ten_don_vi'] = up['ten_don_vi'].upper()
                    supabase.table("don_vi").update(up).eq("mst", row['mst']).execute()
                    st.success("Đã cập nhật dữ liệu thành công!")
                    st.rerun()
            with c_btn2:
                # Nút xuất PDF nằm trong Form (hoặc ngoài tùy ý)
                pdf_bytes = export_pdf(row)
                if pdf_bytes:
                    st.download_button("📄 XUẤT FILE PDF", pdf_bytes, f"HN11_{row['mst']}.pdf", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
