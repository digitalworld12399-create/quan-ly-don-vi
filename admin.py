import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import io
import os
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- 1. KẾT NỐI HỆ THỐNG (Sử dụng Secrets để bảo mật) ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    UPDATE_PAGE_URL = st.secrets.get("UPDATE_URL", "https://your-link.com") # Link cập nhật
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Chưa cấu hình Secrets cho Supabase. Vui lòng kiểm tra lại thiết lập trên Streamlit Cloud.")
    st.stop()

# Cấu hình giao diện
st.set_page_config(page_title="HN11 - Hệ thống Quản trị", layout="wide", page_icon="🛡️")

# --- 2. HÀM HỖ TRỢ XỬ LÝ DỮ LIỆU ---
def loai_bo_dau(s):
    if not isinstance(s, str): return str(s)
    s = s.lower()
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[đ]', 'd', s)
    return s.strip()

def tach_dia_chi(address):
    if not address or not isinstance(address, str):
        return "Không rõ", "Không rõ"
    parts = [p.strip() for p in address.split(',')]
    tinh = parts[-1] if len(parts) > 0 else "Không rõ"
    xa_match = re.search(r'(Xã|Phường|Thị trấn)\s+([^,]+)', address, re.IGNORECASE)
    xa = xa_match.group(0) if xa_match else "Không rõ"
    return xa, tinh

# --- 3. XỬ LÝ XUẤT PDF TIẾNG VIỆT ---
class VietPDF(FPDF):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_path = "arial.ttf" # Bạn cần upload file này lên GitHub cùng thư mục
        if os.path.exists(self.font_path):
            self.add_font('VietFont', '', self.font_path)
            self.add_font('VietFont', 'B', self.font_path)
            self.vfont = 'VietFont'
        else: 
            self.vfont = None

def tao_phieu_pdf(row):
    pdf = VietPDF()
    if not pdf.vfont: return None
    pdf.add_page()
    pdf.set_font(pdf.vfont, 'B', 16)
    pdf.set_text_color(30, 144, 255)
    pdf.cell(0, 15, "PHIẾU CHI TIẾT THÔNG TIN ĐƠN VỊ", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(8)
    for col, val in row.items():
        if col in ['xa_phuong', 'tinh_thanh']: continue
        pdf.set_fill_color(240, 240, 240); pdf.set_font(pdf.vfont, 'B', 10)
        pdf.cell(60, 10, f" {str(col).upper()}", border=1, fill=True)
        pdf.set_fill_color(255, 255, 255); pdf.set_font(pdf.vfont, '', 10)
        pdf.multi_cell(0, 10, f" {str(val)}", border=1, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())

# --- 4. KIỂM TRA ĐĂNG NHẬP ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col_login, _ = st.columns([1.2, 1, 1.2])
    with col_login:
        st.write("")
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🔐 HN11 LOGIN</h3>", unsafe_allow_html=True)
            u = st.text_input("Tài khoản", placeholder="Nhập tài khoản", label_visibility="collapsed")
            p = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu", label_visibility="collapsed")
            if st.button("ĐĂNG NHẬP HỆ THỐNG", use_container_width=True, type="primary"):
                if u == "kh" and p == "a11":
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

# --- 5. TRANG QUẢN TRỊ CHÍNH ---
try:
    res = supabase.table("don_vi").select("*").execute()
    if res.data:
        df_raw = pd.DataFrame(res.data)
        df_raw[['xa_phuong', 'tinh_thanh']] = df_raw['dia_chi'].apply(lambda x: pd.Series(tach_dia_chi(x)))

        # SIDEBAR
        with st.sidebar:
            st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 15px; border-left: 5px solid #0083B8; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #1f77b4;">🛡️ HN11 ADMIN</h3>
                    <p style="margin: 5px 0 0 0; font-weight: bold;">👤 Nguyễn Văn Ánh</p>
                    <p style="color: #0083B8; font-size: 14px;">📞 0969.338.332</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            st.markdown("#### 📍 BỘ LỌC ĐỊA BÀN")
            sel_tinh = st.selectbox("Chọn Tỉnh/Thành:", ["Tất cả"] + sorted(df_raw['tinh_thanh'].unique()))
            df_lv2 = df_raw[df_raw['tinh_thanh'] == sel_tinh] if sel_tinh != "Tất cả" else df_raw
            sel_xa = st.selectbox("Chọn Xã/Phường:", ["Tất cả"] + sorted(df_lv2['xa_phuong'].unique()))
            
            st.divider()
            # NÚT KIỂM TRA CẬP NHẬT THEO YÊU CẦU
            st.link_button("🔄 KIỂM TRA CẬP NHẬT", UPDATE_PAGE_URL, use_container_width=True, type="secondary")
            
            if st.button("🚪 Đăng xuất", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()

        # NỘI DUNG CHÍNH
        st.title("📊 HỆ THỐNG QUẢN TRỊ DỮ LIỆU")
        q = st.text_input("🔎 TÌM KIẾM THÔNG MINH:", placeholder="Nhập Tên, MST, Số điện thoại...")
        
        df_filtered = df_lv2 if sel_xa == "Tất cả" else df_lv2[df_lv2['xa_phuong'] == sel_xa]
        if q:
            q_norm = loai_bo_dau(q)
            mask = df_filtered.apply(lambda r: r.astype(str).apply(loai_bo_dau).str.contains(q_norm).any(), axis=1)
            df_filtered = df_filtered[mask]

        # BIỂU ĐỒ & THÔNG SỐ
        st.divider()
        c_chart, c_metric = st.columns([2, 1])
        with c_chart:
            df_chart = df_filtered['xa_phuong'].value_counts().reset_index()
            df_chart.columns = ['Địa phương', 'Số lượng']
            fig = px.pie(df_chart, values='Số lượng', names='Địa phương', hole=0.5, height=350, title="Phân bổ đơn vị")
            st.plotly_chart(fig, use_container_width=True)
        
        with c_metric:
            st.metric("Kết quả lọc", f"{len(df_filtered)} đơn vị")
            st.metric("Tổng hệ thống", len(df_raw))

        st.dataframe(df_filtered, use_container_width=True, hide_index=True)

        # CHI TIẾT & XUẤT FILE
        st.divider()
        st.subheader("📋 CHI TIẾT ĐƠN VỊ")
        selected = st.selectbox("🎯 Chọn đơn vị:", ["-- Chọn đơn vị --"] + df_filtered['ten_don_vi'].tolist())
        
        if selected != "-- Chọn đơn vị --":
            row_data = df_filtered[df_filtered['ten_don_vi'] == selected].iloc[0]
            with st.container(border=True):
                st.markdown(f"#### 🏛️ {row_data['ten_don_vi'].upper()}")
                cols = st.columns(3)
                for i, (k, v) in enumerate(row_data.items()):
                    with cols[i % 3]:
                        st.write(f"**{k.replace('_',' ').upper()}:** {v}")
                
                st.divider()
                b1, b2 = st.columns(2)
                with b1:
                    pdf_bytes = tao_phieu_pdf(row_data)
                    if pdf_bytes:
                        st.download_button("📄 XUẤT PDF", pdf_bytes, f"{row_data['mst']}.pdf", "application/pdf", use_container_width=True)
                    else: st.warning("Thiếu file arial.ttf để xuất PDF")
                with b2:
                    buf = io.BytesIO()
                    df_filtered.to_excel(buf, index=False)
                    st.download_button("📊 XUẤT EXCEL (DANH SÁCH)", buf.getvalue(), "HN11_Report.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
