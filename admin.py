import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import io
import os
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- 1. KẾT NỐI (Lấy từ Secrets) ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    # Link cập nhật lấy từ Secrets, nếu không có sẽ dùng link mặc định
    UPDATE_PAGE_URL = st.secrets.get("UPDATE_URL", "https://your-folder-link.com") 
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Chưa cấu hình Secrets. Vui lòng kiểm tra tab Secrets trên Streamlit Cloud.")
    st.stop()

st.set_page_config(page_title="HN11 - Quản trị", layout="wide", page_icon="🛡️")

# --- 2. XỬ LÝ PDF ---
class VietPDF(FPDF):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_path = "arial.ttf"
        if os.path.exists(self.font_path):
            self.add_font('VietFont', '', self.font_path)
            self.vfont = 'VietFont'
        else: self.vfont = None

def tao_phieu_pdf(row):
    pdf = VietPDF()
    if not pdf.vfont: return None
    pdf.add_page()
    pdf.set_font(pdf.vfont, '', 14)
    pdf.cell(0, 10, f"PHIẾU THÔNG TIN: {row['ten_don_vi']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    for k, v in row.items():
        pdf.cell(0, 10, f"{k.upper()}: {v}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())

# --- 3. ĐĂNG NHẬP ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    with st.container(border=True):
        st.subheader("🔐 ĐĂNG NHẬP HỆ THỐNG")
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.button("Đăng nhập"):
            if u == "kh" and p == "a11":
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Sai tài khoản!")
    st.stop()

# --- 4. GIAO DIỆN CHÍNH ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df = pd.DataFrame(res.data)

    with st.sidebar:
        st.title("🛡️ HN11 ADMIN")
        st.divider()
        # NÚT KIỂM TRA CẬP NHẬT THEO YÊU CẦU CỦA BẠN
        st.link_button("🔄 KIỂM TRA CẬP NHẬT", UPDATE_PAGE_URL, use_container_width=True, type="secondary")
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.title("📊 QUẢN LÝ DỮ LIỆU ĐƠN VỊ")
    st.dataframe(df, use_container_width=True)

    selected = st.selectbox("Chọn đơn vị xem chi tiết:", ["-- Chọn --"] + df['ten_don_vi'].tolist())
    if selected != "-- Chọn --":
        row = df[df['ten_don_vi'] == selected].iloc[0]
        st.write(row)
        pdf_data = tao_phieu_pdf(row)
        if pdf_data:
            st.download_button("📄 TẢI PDF", pdf_data, "phieu.pdf", "application/pdf")
        else:
            st.warning("Thiếu file arial.ttf để tạo PDF tiếng Việt.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
