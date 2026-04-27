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

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM HỖ TRỢ PDF & QR CODE ---
def export_pdf(row):
    try:
        # Khởi tạo PDF
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

        # TẠO MÃ QR (Chứa MST và Tên đơn vị)
        mst = str(row.get('mst', 'N/A'))
        ten_dv = str(row.get('ten_don_vi', ''))
        qr_content = f"MST: {mst}\nĐơn vị: {ten_dv}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        
        # Lưu QR vào bộ nhớ đệm
        qr_buffer = io.BytesIO()
        img_qr.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Chèn QR vào góc phải phía trên
        pdf.image(qr_buffer, x=165, y=10, w=30)

        # Tiêu đề phiếu
        pdf.set_font(font_name, size=16)
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        
        # Danh sách trường thông tin
        fields = {
            "Tên đơn vị": ten_dv.upper(), 
            "Mã số thuế": "mst", 
            "Địa chỉ": "dia_chi",
            "Khu vực": "huyen_cu", 
            "Mã QHNS": "ma_qhns", 
            "Số TK Kho bạc": "so_tkkb",
            "Mã Kho bạc": "ma_kbnn", 
            "Chủ tài khoản": "chu_tai_khoan", 
            "Chức vụ": "chuc_vu",
            "Kế toán trưởng": "ke_toan", 
            "Số điện thoại": "sdt_ke_toan", 
            "Mã máy": "san_pham"
        }
        
        for label, key in fields.items():
            val = str(row.get(key, key)) if isinstance(key, str) and key in row else str(key)
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
            
        # Xuất dữ liệu byte (Sửa lỗi encoding)
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Lỗi tạo PDF & QR: {e}")
        return b""

# --- 3. HÀM XUẤT EXCEL THEO BIỂU MẪU ---
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
            workbook = writer.book
            worksheet = writer.sheets['NHAPLIEU']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 20)
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
        c1, c2 = st.columns(2)
        c1.metric("Tổng đơn vị", len(df_raw))
        missing = int(df_raw['sdt_ke_toan'].isna().sum())
        c2.metric("Thiếu SĐT", missing, delta=f"-{missing}", delta_color="inverse")
        
        st.write("---")
        st.subheader("🔗 TIỆN ÍCH")
        st.link_button("🌐 Tra cứu MST Thuế", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        # Nút kiểm tra cập nhật
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        
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

    # Nút xuất file hàng loạt
    if not df_f.empty:
        ce1, ce2 = st.columns(2)
        with ce1:
            buf = io.BytesIO()
            df_f.to_excel(buf, index=False)
            st.download_button("📥 Tải danh sách gốc", buf.getvalue(), "HN11_Full.xlsx", use_container_width=True)
        with ce2:
            spec = export_special_excel(df_f)
            if spec: st.download_button("📝 MẪU CẤP LICENSE", spec, "HN11_License.xlsx", type="primary", use_container_width=True)

    # Hiệu chỉnh dòng được chọn
    if st.session_state.table_select.selection.rows:
        idx = st.session_state.table_select.selection.rows[0]
        row = df_f.iloc[idx]
        st.divider()
        st.subheader(f"🛠️ Hiệu chỉnh: {row['ten_don_vi']}")
        
        with st.form("edit_form"):
            f1, f2, f3 = st.columns(3)
            up = {}
            with f1:
                up['ten_don_vi'] = st.text_input("Tên đơn vị", value=row['ten_don_vi'])
                up['mst'] = st.text_input("MST", row['mst'])
            with f2:
                up['huyen_cu'] = st.text_input("Khu vực", row['huyen_cu'])
                up['ma_qhns'] = st.text_input("Mã QHNS", row['ma_qhns'])
            with f3:
                up['ke_toan'] = st.text_input("Kế toán", row['ke_toan'])
                up['sdt_ke_toan'] = st.text_input("SĐT", row['sdt_ke_toan'])
            
            if st.form_submit_button("💾 LƯU THAY ĐỔI", type="primary", use_container_width=True):
                supabase.table("don_vi").update(up).eq("mst", row['mst']).execute()
                st.success("Đã cập nhật!")
                st.rerun()

        b1, b2, b3 = st.columns(3)
        with b1:
            sdt = str(row['sdt_ke_toan']).strip()
            if sdt and sdt != "nan": st.link_button("💬 ZALO KẾ TOÁN", f"https://zalo.me/{sdt}", use_container_width=True)
        with b2:
            pdf_bytes = export_pdf(row)
            if pdf_bytes: st.download_button("📄 XUẤT PDF + QR", pdf_bytes, f"HN11_{row['mst']}.pdf", use_container_width=True, mime="application/pdf")
        with b3:
            row_ex = export_special_excel(pd.DataFrame([row]))
            if row_ex: st.download_button("📊 MẪU LICENSE DÒNG NÀY", row_ex, f"License_{row['mst']}.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
