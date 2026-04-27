import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
import qrcode
from fpdf import FPDF # Lưu ý: Đây là FPDF từ thư viện fpdf2
import plotly.express as px
from datetime import datetime

# --- 1. CẤU HÌNH ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Pro", layout="wide")

# --- 2. HÀM TẠO QR ---
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

# --- 3. HÀM XUẤT PDF (SỬA LỖI CODEC 'UTF-8') ---
def export_pdf(row):
    try:
        # Sử dụng fpdf2 hỗ trợ Unicode và Bytes trực tiếp
        pdf = FPDF()
        pdf.add_page()
        
        # Cấu hình Font (Phải có file arial.ttf trong cùng thư mục)
        font_path = "arial.ttf"
        font_name = 'Helvetica'
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', size=16)

        # Tích hợp QR Code vào góc phải PDF
        qr_content = f"MST: {row.get('mst')}\nDV: {row.get('ten_don_vi')}"
        qr_buf = generate_qr(qr_content)
        if qr_buf:
            temp_qr = f"temp_{row.get('mst')}.png"
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
            "Kế toán": "ke_toan", "SĐT": "sdt_ke_toan"
        }
        for label, key in fields.items():
            val = str(row.get(key, key)) if key in row else str(key)
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)

        # --- ĐÂY LÀ PHẦN SỬA LỖI QUAN TRỌNG ---
        # Lệnh bytes() sẽ lấy luồng nhị phân sạch, không bị lỗi utf-8
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return b""

# --- 4. GIAO DIỆN CHÍNH ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        u = st.text_input("Admin")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
    st.stop()

try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    
    # Sửa lỗi so sánh str vs float
    df_raw['huyen_cu'] = df_raw['huyen_cu'].fillna("Chưa rõ").astype(str)

    # SIDEBAR: Phân tích và tiện ích
    with st.sidebar:
        st.header("📊 Dashboard")
        st.metric("Tổng đơn vị", len(df_raw))
        st.write("---")
        st.link_button("🌐 Tra cứu MST", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-site.com", use_container_width=True)
        
        st.write("---")
        with st.expander("📈 Phân tích dữ liệu", expanded=False):
            valid_stats = df_raw.notna().sum().drop(['id'], errors='ignore')
            fig = px.bar(x=valid_stats.values, y=valid_stats.index, orientation='h')
            st.plotly_chart(fig, use_container_width=True)

    # Bảng hiển thị
    st.subheader("📋 Quản lý đơn vị")
    search = st.text_input("🔍 Tìm nhanh...")
    df_f = df_raw
    if search:
        df_f = df_raw[df_raw.apply(lambda x: search.lower() in str(x.values).lower(), axis=1)]

    st.dataframe(df_f[['mst', 'ten_don_vi', 'huyen_cu', 'sdt_ke_toan']], 
                 use_container_width=True, hide_index=True, 
                 selection_mode="single-row", key="table_select", on_select="rerun")

    if st.session_state.table_select.selection.rows:
        row = df_f.iloc[st.session_state.table_select.selection.rows[0]]
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            pdf_data = export_pdf(row)
            if pdf_data:
                st.download_button("📄 Tải PDF (Có QR)", pdf_data, f"{row['mst']}.pdf", use_container_width=True)
        with col2:
            sdt = str(row['sdt_ke_toan'])
            if sdt != "nan":
                st.link_button("💬 Zalo", f"https://zalo.me/{sdt}", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
