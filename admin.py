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
# Thay đổi đường dẫn này thành đường dẫn file thực tế của bạn (ví dụ: "C:/path/to/logo.png" hoặc "logo.png" nếu cùng thư mục code)
# Hoặc sử dụng link online nếu bạn host ảnh ở đâu đó: "https://your-website.com/logo.png"
LOGO_IMAGE = "logo.png" 

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
# Khởi tạo client Supabase bên ngoài try-except để tránh lỗi phạm vi
try:
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")
    st.stop()

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM XUẤT PDF + QR CODE ---
def export_pdf(row):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_qr:
        qr_path = tmp_qr.name
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Thêm font hỗ trợ tiếng Việt (Arial)
        # Lưu ý: Cần file 'arial.ttf' trong cùng thư mục chạy code
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path, uni=True)
            pdf.set_font('ArialVN', size=16)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', 'B', size=16)
            font_name = 'Helvetica'

        # Tạo nội dung QR
        mst = str(row.get('mst', 'N/A'))
        ten_dv = str(row.get('ten_don_vi', ''))
        qr_content = f"MST: {mst}\nDon vi: {ten_dv}"
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_path)
        
        # Thêm QR Code vào góc trên bên phải PDF
        pdf.image(qr_path, x=165, y=10, w=30)

        # Tiêu đề phiếu
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
        
        # Xuất từng dòng thông tin
        for label, val in fields:
            pdf.multi_cell(0, 8, txt=f"{label}: {val if val else ''}")
            pdf.ln(1)
            
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return b""
    finally:
        if os.path.exists(qr_path): os.remove(qr_path)

# --- 3. KIỂM TRA ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        # TÍCH HỢP LOGO VÀO MÀN HÌNH ĐĂNG NHẬP (TÙY CHỌN)
        # if os.path.exists(LOGO_IMAGE):
        #     st.image(LOGO_IMAGE, width=100)
        st.subheader("🛡️ Hệ thống Quản trị HN11")
        u = st.text_input("Tài khoản Admin")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            # Thông tin đăng nhập cứng
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin đăng nhập!")
    st.stop()

# --- 4. TẢI DỮ LIỆU ---
try:
    # Truy vấn toàn bộ bảng 'don_vi'
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    
    # Xử lý chuẩn hóa tên đơn vị
    if not df_raw.empty:
        df_raw['ten_don_vi'] = df_raw['ten_don_vi'].str.upper()

    # --- 5. SIDEBAR: TÍCH HỢP LOGO VÀ THỐNG KÊ ---
    with st.sidebar:
        # === PHẦN LOGO MỚI ĐƯỢC TÍCH HỢP ===
        if os.path.exists(LOGO_IMAGE):
            # Hiển thị logo, căn giữa
            st.image(LOGO_IMAGE, use_container_width=True) 
        else:
            # Nếu không tìm thấy file logo, hiển thị thông báo thay thế
            st.warning(f"Không tìm thấy logo tại: {LOGO_IMAGE}")
        
        st.title("📊 THỐNG KÊ HỆ THỐNG")
        
        if not df_raw.empty:
            # Thống kê con số nhanh (KPIs)
            total_dv = len(df_raw)
            # Giả sử 'sdt_ke_toan' và 'mst' có thể bị NULL
            missing_sdt = df_raw['sdt_ke_toan'].isna().sum() if 'sdt_ke_toan' in df_raw.columns else 0
            missing_mst = df_raw['mst'].isna().sum() if 'mst' in df_raw.columns else 0
            
            col_kpi1, col_kpi2 = st.columns(2)
            col_kpi1.metric("Tổng đơn vị", total_dv)
            if 'sdt_ke_toan' in df_raw.columns:
                col_kpi2.metric("Thiếu SĐT", missing_sdt, delta=f"-{missing_sdt}", delta_color="inverse")
            
            st.divider()

            # 1. Biểu đồ tròn: Tỷ lệ theo Khu vực (Huyện cũ)
            if 'huyen_cu' in df_raw.columns:
                st.subheader("📍 Theo Khu vực")
                df_huyen = df_raw['huyen_cu'].value_counts().reset_index()
                fig_pie = px.pie(df_huyen, values='count', names='huyen_cu', hole=0.4)
                fig_pie.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

            # 2. Biểu đồ cột: Theo loại sản phẩm (Mã máy)
            if 'san_pham' in df_raw.columns:
                st.subheader("💻 Theo Mã máy")
                df_sp = df_raw['san_pham'].value_counts().reset_index().head(5)
                fig_bar = px.bar(df_sp, x='san_pham', y='count', color='san_pham')
                fig_bar.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu thống kê.")

        st.divider()
        st.subheader("🔗 TIỆN ÍCH")
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 6. MÀN HÌNH CHÍNH ---
    st.subheader("📋 QUẢN LÝ DANH SÁCH")
    
    # Ô tìm kiếm dữ liệu
    search_q = st.text_input("🔍 Tìm kiếm đơn vị...", placeholder="Nhập tên, MST hoặc SĐT...")
    
    # Xử lý lọc dữ liệu dựa trên ô tìm kiếm
    df_f = df_raw
    if search_q and not df_raw.empty:
        q = search_q.lower()
        # Lọc trên tất cả các cột
        df_f = df_f[df_f.apply(lambda x: q in str(x.values).lower(), axis=1)]

    # Hiển thị bảng dữ liệu chính
    # Lưu ý: 'sdt_ke_toan' được thêm vào danh sách hiển thị để người dùng thấy SĐT
    columns_to_show = ['mst', 'ten_don_vi', 'huyen_cu', 'chu_tai_khoan', 'ke_toan']
    if 'sdt_ke_toan' in df_f.columns:
        columns_to_show.append('sdt_ke_toan')

    st.dataframe(
        df_f[columns_to_show] if not df_f.empty else df_f,
        use_container_width=True, hide_index=True,
        selection_mode="single-row", key="table_select", on_select="rerun"
    )

    # Xử lý khi người dùng chọn một dòng trong bảng
    if not df_f.empty and st.session_state.table_select.selection.rows:
        idx = st.session_state.table_select.selection.rows[0]
        # Lấy dữ liệu của dòng được chọn
        row = df_f.iloc[idx]
        
        st.divider()
        st.subheader(f"🛠️ CHI TIẾT ĐƠN VỊ: {row['ten_don_vi']}")
        
        # FORM SỬA VÀ LƯU DỮ LIỆU
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            up = {} # Dictionary chứa dữ liệu cập nhật
            with c1:
                up['ten_don_vi'] = st.text_input("Tên đơn vị", value=row.get('ten_don_vi', ''))
                up['mst'] = st.text_input("Mã số thuế", value=row.get('mst', ''))
                up['dia_chi'] = st.text_input("Địa chỉ", value=row.get('dia_chi', ''))
                up['huyen_cu'] = st.text_input("Huyện cũ", value=row.get('huyen_cu', ''))
                up['so_tkkb'] = st.text_input("Số tài khoản", value=row.get('so_tkkb', ''))
            with c2:
                up['chu_tai_khoan'] = st.text_input("Thủ trưởng", value=row.get('chu_tai_khoan', ''))
                up['chuc_vu'] = st.text_input("Chức vụ", value=row.get('chuc_vu', ''))
                up['ke_toan'] = st.text_input("Kế toán", value=row.get('ke_toan', ''))
                up['sdt_ke_toan'] = st.text_input("Số điện thoại", value=row.get('sdt_ke_toan', ''))
                up['san_pham'] = st.text_input("Mã máy (Serial)", value=row.get('san_pham', ''))

            # Nút lưu dữ liệu trong form
            if st.form_submit_button("💾 LƯU THAY ĐỔI DỮ LIỆU", type="primary", use_container_width=True):
                try:
                    # Chuẩn hóa tên đơn vị thành chữ hoa trước khi lưu
                    up['ten_don_vi'] = up['ten_don_vi'].upper()
                    # Cập nhật dữ liệu vào Supabase dựa trên MST (Mã số thuế là khóa chính/duy nhất)
                    supabase.table("don_vi").update(up).eq("mst", row['mst']).execute()
                    st.success("Đã cập nhật dữ liệu thành công!")
                    # Reload lại trang để cập nhật bảng
                    st.rerun()
                except Exception as save_e:
                    st.error(f"Lỗi khi lưu dữ liệu: {save_e}")

        # NÚT XUẤT FILE (NGOÀI FORM)
        st.write("### 📂 Thao tác nhanh")
        b_col1, b_col2, b_col3 = st.columns(3)
        with b_col1:
            # Xuất PDF có QR Code
            pdf_data = export_pdf(row)
            if pdf_data:
                st.download_button("📄 TẢI PDF (+QR CODE)", pdf_data, f"HN11_{row['mst']}.pdf", "application/pdf", use_container_width=True)
        with b_col2:
            # Liên hệ Zalo qua số điện thoại kế toán
            sdt = str(row.get('sdt_ke_toan', '')).strip()
            if sdt and sdt != "None" and sdt != "":
                st.link_button("💬 LIÊN HỆ ZALO", f"https://zalo.me/{sdt}", use_container_width=True)
            else:
                st.button("💬 LIÊN HỆ ZALO (Thiếu SĐT)", use_container_width=True, disabled=True)
        with b_col3:
            # Xuất file Excel chi tiết của dòng được chọn
            buf = io.BytesIO()
            pd.DataFrame([row]).to_excel(buf, index=False)
            st.download_button("📊 XUẤT EXCEL CHI TIẾT", buf.getvalue(), f"Detail_{row['mst']}.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi ứng dụng: {e}")
