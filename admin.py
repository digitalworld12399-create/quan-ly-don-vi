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
import tempfile # Thêm thư viện này để xử lý tệp tạm

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM HỖ TRỢ PDF & QR CODE (ĐÃ SỬA LỖI RFIND) ---
def export_pdf(row):
    # Khởi tạo tệp tạm để chứa QR tránh lỗi rfind
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_qr:
        qr_path = tmp_qr.name
        
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Nhúng font tiếng Việt
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path, uni=True)
            pdf.set_font('ArialVN', size=16)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', 'B', size=16)
            font_name = 'Helvetica'

        # TẠO MÃ QR
        mst = str(row.get('mst', 'N/A'))
        ten_dv = str(row.get('ten_don_vi', ''))
        qr_content = f"MST: {mst}\nDon vi: {ten_dv}" # Không để dấu trong QR content nếu QR reader cũ
        
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        
        # Lưu QR vào tệp tạm thay vì BytesIO để FPDF đọc dễ dàng
        img_qr.save(qr_path)
        
        # Chèn QR từ đường dẫn tệp tạm
        pdf.image(qr_path, x=165, y=10, w=30)

        # Nội dung PDF
        pdf.set_font(font_name, size=16)
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        
        fields = {
            "Tên đơn vị": ten_dv.upper(), 
            "Mã số thuế": "mst", 
            "Địa chỉ": "dia_chi",
            "Khu vực": "huyen_cu", 
            "Mã QHNS": "ma_qhns", 
            "Số TK Kho bạc": "so_tkkb",
            "Mã máy": "san_pham"
        }
        
        for label, key in fields.items():
            val = str(row.get(key, key)) if isinstance(key, str) and key in row else str(key)
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
            
        # Xuất dữ liệu byte
        pdf_output = pdf.output(dest='S').encode('latin-1')
        return pdf_output
    except Exception as e:
        st.error(f"Lỗi tạo PDF & QR: {e}")
        return b""
    finally:
        # Xóa tệp tạm sau khi dùng xong
        if os.path.exists(qr_path):
            os.remove(qr_path)

# --- 3. HÀM XUẤT EXCEL ---
def export_special_excel(df):
    try:
        if df.empty: return None
        export_df = pd.DataFrame()
        export_df['STT'] = range(1, len(df) + 1)
        export_df['ĐỊA DANH'] = df['huyen_cu']
        export_df['TÊN KHÁCH HÀNG'] = df['ten_don_vi'].str.upper()
        export_df['MÃ QUAN HỆ NGÂN SÁCH'] = df['ma_qhns']
        export_df['MÃ KHÁCH HÀNG (SỐ SERIAL)'] = df['san_pham']
        export_df['PHẦN MỀM'] = "KTHC"
        export_df['LOẠI CÀI ĐẶT'] = "Chuyển giao"
        export_df['NGÀY KÝ HỢP ĐỒNG'] = datetime.now().strftime("%d/%m/%Y")
        export_df['LÝ DO'] = "Cài mới"
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='NHAPLIEU')
        return output.getvalue()
    except Exception as e:
        st.error(f"Lỗi xuất Excel: {e}")
        return None

# --- 4. GIAO DIỆN ĐĂNG NHẬP ---
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

# --- 5. TẢI DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    if not df_raw.empty and 'ten_don_vi' in df_raw.columns:
        df_raw['ten_don_vi'] = df_raw['ten_don_vi'].str.upper()

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.header("📊 DASHBOARD")
        st.metric("Tổng đơn vị", len(df_raw))
        st.write("---")
        st.subheader("🔗 TIỆN ÍCH")
        st.link_button("🌐 Tra cứu MST Thuế", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True) # Thông tin cập nhật
        
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 7. MÀN HÌNH CHÍNH ---
    st.subheader("📋 QUẢN LÝ NGHIỆP VỤ")
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        sel_h = st.selectbox("Vùng:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
    with col_s2:
        search_q = st.text_input("🔍 Tìm kiếm thông minh", placeholder="Tên đơn vị, MST...")

    df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]
    if search_q:
        q = search_q.lower()
        df_f = df_f[df_f.apply(lambda x: q in str(x.values).lower(), axis=1)]

    st.dataframe(
        df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ke_toan', 'sdt_ke_toan', 'san_pham']],
        use_container_width=True, hide_index=True,
        selection_mode="single-row", key="table_select", on_select="rerun"
    )

    if st.session_state.table_select.selection.rows:
        idx = st.session_state.table_select.selection.rows[0]
        row = df_f.iloc[idx]
        st.divider()
        st.subheader(f"🛠️ Nghiệp vụ: {row['ten_don_vi']}")
        
        b1, b2, b3 = st.columns(3)
        with b1:
            sdt = str(row['sdt_ke_toan']).strip()
            if sdt and sdt != "nan": st.link_button("💬 ZALO KẾ TOÁN", f"https://zalo.me/{sdt}", use_container_width=True)
        with b2:
            pdf_bytes = export_pdf(row)
            if pdf_bytes: st.download_button("📄 XUẤT PDF + QR", pdf_bytes, f"HN11_{row['mst']}.pdf", use_container_width=True, mime="application/pdf")
        with b3:
            row_ex = export_special_excel(pd.DataFrame([row]))
            if row_ex: st.download_button("📊 MẪU LICENSE", row_ex, f"License_{row['mst']}.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
