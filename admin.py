import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
import qrcode
from fpdf import FPDF
import plotly.express as px
import tempfile

# --- 0. CẤU HÌNH ---
LOGO_IMAGE = "logo.png" 
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"

try:
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")
    st.stop()

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 1. HÀM XUẤT PDF ---
def export_pdf(row):
    qr_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_qr:
            qr_path = tmp_qr.name

        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Cấu hình font Tiếng Việt
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path, uni=True)
            pdf.set_font('ArialVN', size=12)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', '', size=12)
            font_name = 'Helvetica'

        # Tạo QR Code
        qr_content = f"MST: {row.get('mst')}\nDV: {row.get('ten_don_vi')}"
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        qr.make_image().save(qr_path)
        
        # Chèn logo QR
        pdf.image(qr_path, x=170, y=10, w=25)
        
        # Tiêu đề
        pdf.set_font(font_name, size=16)
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.ln(5)
        
        # Danh sách các trường hiển thị trong PDF (Đã bổ sung Mã đơn vị BCTCNN)
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
            ("Mã máy (Serial)", row.get('san_pham')),
            ("Mã đơn vị BCTCNN", row.get('ma_bctcnn')) 
        ]
        
        pdf.set_font(font_name, size=11)
        for label, val in fields:
            pdf.multi_cell(0, 8, txt=f"{label}: {val if val else ''}")
            pdf.ln(1)
            
        return bytes(pdf.output(dest='S'))
        
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None
    finally:
        if qr_path and os.path.exists(qr_path):
            try: os.remove(qr_path)
            except: pass

# --- 2. ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Đăng nhập Hệ thống")
        u = st.text_input("User")
        p = st.text_input("Password", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai tài khoản!")
    st.stop()

# --- 3. DỮ LIỆU & THỐNG KÊ ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    if not df_raw.empty:
        df_raw['ten_don_vi'] = df_raw['ten_don_vi'].str.upper()

    with st.sidebar:
        if os.path.exists(LOGO_IMAGE):
            st.image(LOGO_IMAGE, use_container_width=True) 
        
        st.title("📊 THỐNG KÊ")
        if not df_raw.empty:
            st.metric("Tổng đơn vị", len(df_raw))
            color_theme = ["#FFD700", "#DAA520", "#B8860B", "#8B4513", "#5C4033"]

            if 'huyen_cu' in df_raw.columns:
                st.write("**📍 Tỷ lệ theo Khu vực**")
                df_huyen = df_raw['huyen_cu'].value_counts().reset_index()
                fig_pie = px.pie(df_huyen, values='count', names='huyen_cu', hole=0.5,
                                 color_discrete_sequence=color_theme)
                fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=200, showlegend=False)
                fig_pie.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()
        st.write("📂 **KHO LƯU TRỮ**")
        st.link_button("🌐 Mở Google Drive", 
                       "https://drive.google.com/drive/folders/1F5BCYCKIdPK2FAhQmog-8rWVAYagpGAW?usp=sharing", 
                       use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-link.com", use_container_width=True)
        
        if st.button("🚪 Thoát", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 4. GIAO DIỆN CHÍNH ---
    st.subheader("📋 DANH SÁCH ĐƠN VỊ")
    search = st.text_input("🔍 Tìm kiếm nhanh...", placeholder="Nhập tên, MST hoặc SĐT...")
    
    df_f = df_raw
    if search and not df_raw.empty:
        df_f = df_f[df_f.apply(lambda x: search.lower() in str(x.values).lower(), axis=1)]

    st.dataframe(
        df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ke_toan', 'sdt_ke_toan']] if not df_f.empty else df_f,
        use_container_width=True, hide_index=True,
        selection_mode="single-row", key="table_select", on_select="rerun"
    )

    # --- 5. FORM CHI TIẾT & CHỈNH SỬA ---
    if not df_f.empty and st.session_state.table_select.selection.rows:
        idx = st.session_state.table_select.selection.rows[0]
        row = df_f.iloc[idx]
        
        st.divider()
        with st.form("edit_form"):
            st.write(f"### 🛠️ Chỉnh sửa: {row['ten_don_vi']}")
            c1, c2 = st.columns(2)
            up = {}
            with c1:
                up['ten_don_vi'] = st.text_input("Tên đơn vị", value=row.get('ten_don_vi'))
                up['mst'] = st.text_input("MST", value=row.get('mst'))
                up['dia_chi'] = st.text_input("Địa chỉ", value=row.get('dia_chi'))
                up['huyen_cu'] = st.text_input("Huyện cũ", value=row.get('huyen_cu'))
            with c2:
                up['chu_tai_khoan'] = st.text_input("Thủ trưởng", value=row.get('chu_tai_khoan'))
                up['chuc_vu'] = st.text_input("Chức vụ", value=row.get('chuc_vu'))
                up['ke_toan'] = st.text_input("Kế toán", value=row.get('ke_toan'))
                up['sdt_ke_toan'] = st.text_input("SĐT", value=row.get('sdt_ke_toan'))
                
            # Hàng cuối: Hiển thị đối xứng Mã máy và Mã BCTCNN[cite: 1]
            col_left, col_right = st.columns(2)
            with col_left:
                up['san_pham'] = st.text_input("💻 Mã máy (Serial)", value=row.get('san_pham'))
            with col_right:
                up['ma_bctcnn'] = st.text_input("🆔 Mã đơn vị BCTCNN", value=row.get('ma_bctcnn'))

            if st.form_submit_button("💾 LƯU THAY ĐỔI", type="primary", use_container_width=True):
                up['ten_don_vi'] = up['ten_don_vi'].upper()
                supabase.table("don_vi").update(up).eq("mst", row['mst']).execute()
                st.success("Đã cập nhật dữ liệu thành công!")
                st.rerun()

        # NÚT THAO TÁC
        st.write("### 📂 Thao tác")
        col1, col2, col3 = st.columns(3)
        with col1:
            pdf_data = export_pdf(row)
            if pdf_data:
                st.download_button("📄 Tải PDF (+QR)", pdf_data, f"HN11_{row['mst']}.pdf", "application/pdf", use_container_width=True)
        with col2:
            sdt = str(row.get('sdt_ke_toan', '')).strip()
            if sdt and sdt != "None":
                st.link_button("💬 Zalo Kế toán", f"https://zalo.me/{sdt}", use_container_width=True)
        with col3:
            buf = io.BytesIO()
            pd.DataFrame([row]).to_excel(buf, index=False)
            st.download_button("📊 Xuất Excel", buf.getvalue(), f"Detail_{row['mst']}.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
