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

# --- 0. CẤU HÌNH ĐƯỜNG DẪN LOGO ---
LOGO_IMAGE = "logo.png" 

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"

try:
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")
    st.stop()

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM XUẤT PDF + QR CODE ---
def export_pdf(row):
    qr_path = None
    try:
        # Tạo file tạm cho QR Code để tránh lỗi quyền truy cập
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_qr:
            qr_path = tmp_qr.name

        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Cấu hình Font tiếng Việt
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path, uni=True)
            pdf.set_font('ArialVN', size=14)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', 'B', size=14)
            font_name = 'Helvetica'

        # Tạo QR Code
        mst = str(row.get('mst', 'N/A'))
        ten_dv_raw = str(row.get('ten_don_vi', ''))
        qr_content = f"MST: {mst} - DV: {ten_dv_raw}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_path)
        
        # Chèn QR Code vào PDF
        pdf.image(qr_path, x=165, y=10, w=30)

        # Nội dung văn bản
        pdf.set_font(font_name, size=18)
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.ln(5)
        pdf.set_font(font_name, size=11)
        
        fields = [
            ("Mã số thuế", row.get('mst')),
            ("Tên đơn vị", str(row.get('ten_don_vi', '')).upper()),
            ("Địa chỉ", row.get('dia_chi')),
            ("Khu vực", row.get('huyen_cu')),
            ("Thủ trưởng", row.get('chu_tai_khoan')),
            ("Chức vụ", row.get('chuc_vu')),
            ("Kế toán", row.get('ke_toan')),
            ("Số điện thoại", row.get('sdt_ke_toan')),
            ("Số tài khoản", row.get('so_tkkb')),
            ("Mã QHNS", row.get('ma_qhns')),
            ("Mã máy (Serial)", row.get('san_pham'))
        ]
        
        for label, val in fields:
            pdf.multi_cell(0, 8, txt=f"{label}: {val if val else ''}")
            pdf.ln(1)
            
        # KHẮC PHỤC LỖI: Chuyển đổi bytearray sang bytes chuẩn
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, (bytearray, bytes)):
            return bytes(pdf_output)
        return pdf_output.encode('latin-1') if isinstance(pdf_output, str) else pdf_output
        
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None
    finally:
        if qr_path and os.path.exists(qr_path):
            try: os.remove(qr_path)
            except: pass

# --- 3. KIỂM TRA ĐĂNG NHẬP ---
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

    # --- 5. SIDEBAR ---
    with st.sidebar:
        if os.path.exists(LOGO_IMAGE):
            st.image(LOGO_IMAGE, use_container_width=True) 
        
        st.title("📊 THỐNG KÊ")
        if not df_raw.empty:
            st.metric("Tổng đơn vị", len(df_raw))
            if 'huyen_cu' in df_raw.columns:
                df_huyen = df_raw['huyen_cu'].value_counts().reset_index()
                fig_pie = px.pie(df_huyen, values='count', names='huyen_cu', hole=0.4)
                fig_pie.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250, showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 6. MÀN HÌNH CHÍNH ---
    st.subheader("📋 QUẢN LÝ DANH SÁCH")
    search_q = st.text_input("🔍 Tìm kiếm...", placeholder="Nhập tên, MST hoặc SĐT...")
    
    df_f = df_raw
    if search_q and not df_raw.empty:
        q = search_q.lower()
        df_f = df_f[df_f.apply(lambda x: q in str(x.values).lower(), axis=1)]

    columns_to_show = ['mst', 'ten_don_vi', 'huyen_cu', 'ke_toan', 'sdt_ke_toan']
    st.dataframe(
        df_f[columns_to_show] if not df_f.empty else df_f,
        use_container_width=True, hide_index=True,
        selection_mode="single-row", key="table_select", on_select="rerun"
    )

    # --- 7. FORM CHI TIẾT ---
    if not df_f.empty and st.session_state.table_select.selection.rows:
        idx = st.session_state.table_select.selection.rows[0]
        row = df_f.iloc[idx]
        
        st.divider()
        with st.form("edit_form"):
            st.subheader(f"🛠️ CHỈNH SỬA: {row['ten_don_vi']}")
            c1, c2 = st.columns(2)
            up = {} 
            with c1:
                up['ten_don_vi'] = st.text_input("Tên đơn vị", value=row.get('ten_don_vi', ''))
                up['mst'] = st.text_input("Mã số thuế", value=row.get('mst', ''))
                up['dia_chi'] = st.text_input("Địa chỉ", value=row.get('dia_chi', ''))
            with c2:
                up['ke_toan'] = st.text_input("Kế toán", value=row.get('ke_toan', ''))
                up['sdt_ke_toan'] = st.text_input("Số điện thoại", value=row.get('sdt_ke_toan', ''))
                up['san_pham'] = st.text_input("Mã máy (Serial)", value=row.get('san_pham', ''))

            if st.form_submit_button("💾 LƯU THAY ĐỔI", type="primary", use_container_width=True):
                supabase.table("don_vi").update(up).eq("mst", row['mst']).execute()
                st.success("Đã cập nhật!")
                st.rerun()

        # NÚT THAO TÁC NHANH
        col_pdf, col_zalo, col_excel = st.columns(3)
        with col_pdf:
            pdf_data = export_pdf(row)
            if pdf_data:
                st.download_button("📄 TẢI PDF", pdf_data, f"{row['mst']}.pdf", "application/pdf", use_container_width=True)
        with col_zalo:
            sdt = str(row.get('sdt_ke_toan', '')).strip()
            if sdt and sdt not in ["None", ""]:
                st.link_button("💬 ZALO", f"https://zalo.me/{sdt}", use_container_width=True)
        with col_excel:
            buf = io.BytesIO()
            pd.DataFrame([row]).to_excel(buf, index=False)
            st.download_button("📊 EXCEL", buf.getvalue(), f"{row['mst']}.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi ứng dụng: {e}")
