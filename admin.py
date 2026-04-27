import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
import qrcode
from fpdf import FPDF
import plotly.express as px
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Pro", layout="wide")

# --- 2. HÀM TẠO MÃ QR ---
def generate_qr(data):
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf
    except:
        return None

# --- 3. HÀM XUẤT PDF (SỬA LỖI CODEC & UNICODE) ---
def export_pdf(row):
    try:
        # Sử dụng fpdf2
        pdf = FPDF()
        pdf.add_page()
        
        # Cấu hình Font (Cần file arial.ttf trong thư mục gốc)
        font_path = "arial.ttf"
        font_name = 'Helvetica'
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', size=16)

        # Chèn QR Code (Lấy dữ liệu MST và Tên đơn vị)
        qr_content = f"MST: {row.get('mst')}\nDV: {row.get('ten_don_vi')}\nSDT: {row.get('sdt_ke_toan')}"
        qr_buf = generate_qr(qr_content)
        if qr_buf:
            temp_qr = f"qr_{row.get('mst')}.png"
            with open(temp_qr, "wb") as f:
                f.write(qr_buf.getvalue())
            pdf.image(temp_qr, x=165, y=10, w=30)
            if os.path.exists(temp_qr): os.remove(temp_qr)

        # Tiêu đề & Nội dung
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        
        fields = {
            "Tên đơn vị": str(row.get('ten_don_vi', '')).upper(),
            "Mã số thuế": "mst", "Địa chỉ": "dia_chi", "Khu vực": "huyen_cu",
            "Mã QHNS": "ma_qhns", "Chủ tài khoản": "chu_tai_khoan", 
            "Kế toán": "ke_toan", "SĐT": "sdt_ke_toan", "Mã máy": "san_pham"
        }
        for label, key in fields.items():
            val = str(row.get(key, key)) if key in row else str(key)
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)

        # --- ĐIỂM SỬA LỖI QUAN TRỌNG ---
        # Trả về bytes() nguyên bản, fpdf2 sẽ xử lý dữ liệu nhị phân sạch
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return b""

# --- 4. ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Hệ thống Quản trị")
        u = st.text_input("Tài khoản")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 5. TẢI DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    
    # Sửa lỗi so sánh str/float (NaN xử lý thành chuỗi)
    df_raw['huyen_cu'] = df_raw['huyen_cu'].fillna("Chưa rõ").astype(str)
    list_huyen = sorted([h for h in df_raw['huyen_cu'].unique() if h.strip() != ""])

    # SIDEBAR
    with st.sidebar:
        st.header("📊 DASHBOARD")
        st.metric("Tổng đơn vị", len(df_raw))
        st.write("---")
        st.subheader("🔗 TIỆN ÍCH")
        st.link_button("🌐 Tra cứu MST", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://github.com/", use_container_width=True)
        
        # PHÂN TÍCH CHUYÊN SÂU NẰM CUỐI
        st.write("---")
        with st.expander("📈 PHÂN TÍCH CHUYÊN SÂU", expanded=False):
            valid_stats = df_raw.notna().sum().drop(['id'], errors='ignore')
            fig = px.bar(x=valid_stats.values, y=valid_stats.index, orientation='h', color_discrete_sequence=['#1f77b4'])
            fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # MÀN HÌNH CHÍNH
    st.subheader("📋 QUẢN LÝ ĐƠN VỊ")
    c1, c2 = st.columns([1, 2])
    with c1:
        sel_h = st.selectbox("Lọc khu vực:", ["Tất cả"] + list_huyen)
    with c2:
        search = st.text_input("🔍 Tìm nhanh (MST, Tên...):")

    df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]
    if search:
        df_f = df_f[df_f.apply(lambda x: search.lower() in str(x.values).lower(), axis=1)]

    st.dataframe(df_f[['mst', 'ten_don_vi', 'huyen_cu', 'sdt_ke_toan']], 
                 use_container_width=True, hide_index=True, 
                 selection_mode="single-row", key="table_select", on_select="rerun")

    # XỬ LÝ DÒNG CHỌN
    if st.session_state.table_select.selection.rows:
        row = df_f.iloc[st.session_state.table_select.selection.rows[0]]
        st.divider()
        
        col_pdf, col_zalo = st.columns(2)
        with col_pdf:
            pdf_bytes = export_pdf(row)
            if pdf_bytes:
                st.download_button("📄 TẢI PDF (CÓ QR)", pdf_bytes, f"{row['mst']}.pdf", type="primary", use_container_width=True)
        with col_zalo:
            sdt = str(row['sdt_ke_toan']).strip()
            if sdt != "nan" and sdt != "":
                st.link_button("💬 LIÊN HỆ ZALO", f"https://zalo.me/{sdt}", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
