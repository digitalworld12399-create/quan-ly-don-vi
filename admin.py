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

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM TẠO MÃ QR ---
def generate_qr(data):
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        return img_buffer
    except:
        return None

# --- 3. HÀM XUẤT PDF (SỬA LỖI UNICODE TIẾNG VIỆT) ---
def export_pdf(row):
    try:
        # Sử dụng thư viện fpdf2 (quan trọng)
        pdf = FPDF()
        pdf.add_page()
        
        # Thiết lập Font tiếng Việt (BẮT BUỘC phải có file arial.ttf trong cùng thư mục)
        font_path = "arial.ttf"
        font_name = 'Helvetica'
        
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', size=16)
            st.warning("Thiếu file arial.ttf - Tiếng Việt sẽ bị lỗi hiển thị!")

        # 1. Chèn Mã QR
        qr_content = f"MST: {row.get('mst')}\nDV: {row.get('ten_don_vi')}\nSĐT: {row.get('sdt_ke_toan')}"
        qr_img = generate_qr(qr_content)
        if qr_img:
            temp_qr = f"temp_qr_{row.get('mst')}.png"
            with open(temp_qr, "wb") as f:
                f.write(qr_img.getvalue())
            pdf.image(temp_qr, x=165, y=10, w=30)
            if os.path.exists(temp_qr): os.remove(temp_qr)

        # 2. Tiêu đề
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        
        # 3. Nội dung
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        fields = {
            "Tên đơn vị": str(row.get('ten_don_vi', '')).upper(),
            "Mã số thuế": "mst", "Địa chỉ": "dia_chi", "Khu vực": "huyen_cu",
            "Mã QHNS": "ma_qhns", "Số TK Kho bạc": "so_tkkb", "Kế toán trưởng": "ke_toan", 
            "Số điện thoại": "sdt_ke_toan", "Mã máy": "san_pham"
        }
        
        for label, key in fields.items():
            val = str(row.get(key, key)) if key in row else str(key)
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)

        # KHẮC PHỤC LỖI LATIN-1: Xuất trực tiếp sang dạng bytes không qua encode thủ công
        return bytes(pdf.output())
        
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return b""

# --- 4. CÁC HÀM BỔ TRỢ KHÁC ---
def export_special_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 5. GIAO DIỆN CHÍNH ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Login")
        if st.button("Đăng nhập Admin (Demo)"):
            st.session_state.auth = True
            st.rerun()
    st.stop()

try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    df_raw['huyen_cu_clean'] = df_raw['huyen_cu'].fillna("").astype(str)
    list_huyen = sorted([h for h in df_raw['huyen_cu_clean'].unique() if h.strip() != ""])

    with st.sidebar:
        st.header("📊 DASHBOARD")
        st.metric("Tổng đơn vị", len(df_raw))
        st.write("---")
        st.subheader("🔗 TIỆN ÍCH")
        st.link_button("🌐 Tra cứu MST", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        
        st.write("---")
        with st.expander("📈 PHÂN TÍCH CHUYÊN SÂU", expanded=False):
            valid_stats = df_raw.notna().sum().drop(['id'], errors='ignore')
            fig = px.bar(x=valid_stats.values, y=valid_stats.index, orientation='h')
            st.plotly_chart(fig, use_container_width=True)

        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    st.subheader("📋 QUẢN LÝ ĐƠN VỊ")
    sel_h = st.selectbox("Vùng:", ["Tất cả"] + list_huyen)
    df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu_clean'] == sel_h]

    st.dataframe(df_f[['mst', 'ten_don_vi', 'huyen_cu', 'sdt_ke_toan']], 
                 use_container_width=True, hide_index=True, 
                 selection_mode="single-row", key="table_select", on_select="rerun")

    if st.session_state.table_select.selection.rows:
        row = df_f.iloc[st.session_state.table_select.selection.rows[0]]
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            pdf_data = export_pdf(row)
            if pdf_data:
                st.download_button("📄 Tải PDF (Hỗ trợ tiếng Việt)", pdf_data, f"{row['mst']}.pdf", use_container_width=True)
        with c2:
            sdt = str(row['sdt_ke_toan'])
            if sdt != 'nan' and sdt.strip() != "":
                st.link_button("💬 Zalo", f"https://zalo.me/{sdt}", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
