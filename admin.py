import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import io
import os
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- 1. KẾT NỐI SUPABASE ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

# Cấu hình giao diện rộng, chuyên nghiệp
st.set_page_config(page_title="HN11 - Hệ thống Quản trị", layout="wide", page_icon="🛡️")

# --- 2. LOGIC TÌM KIẾM & XỬ LÝ CHUỖI ---
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

# --- 3. XỬ LÝ PDF (ĐÃ FIX LỖI VIETFONTB & BINARY FORMAT) ---
class VietPDF(FPDF):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_path = "arial.ttf" # Cần có file này trong cùng thư mục
        if os.path.exists(self.font_path):
            # Đăng ký cả font thường và font đậm để tránh lỗi vietfontB
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
    # Lặp in toàn bộ dữ liệu có trong data
    for col, val in row.items():
        if col in ['xa_phuong', 'tinh_thanh']: continue
        pdf.set_fill_color(240, 240, 240); pdf.set_font(pdf.vfont, 'B', 10)
        pdf.cell(60, 10, f" {str(col).upper()}", border=1, fill=True)
        pdf.set_fill_color(255, 255, 255); pdf.set_font(pdf.vfont, '', 10)
        pdf.multi_cell(0, 10, f" {str(val)}", border=1, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output()) # Fix lỗi Invalid binary data format

# --- 4. GIAO DIỆN ĐĂNG NHẬP (KHUNG VỪA PHẢI) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col_login, _ = st.columns([1.2, 1, 1.2]) # Điều chỉnh kích thước khung login vừa vặn
    with col_login:
        st.write("")
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🔐 HN11 LOGIN</h3>", unsafe_allow_html=True)
            u = st.text_input("Tài khoản", placeholder="Nhập tài khoản", label_visibility="collapsed")
            p = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu", label_visibility="collapsed")
            if st.button("ĐĂNG NHẬP HỆ THỐNG", width='stretch', type="primary"):
                if u == "kh" and p == "a11":
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

# --- 5. QUẢN TRỊ DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    if res.data:
        df_raw = pd.DataFrame(res.data)
        df_raw[['xa_phuong', 'tinh_thanh']] = df_raw['dia_chi'].apply(lambda x: pd.Series(tach_dia_chi(x)))

        # SIDEBAR: Bộ lọc & Cập nhật
        with st.sidebar:
            st.markdown("### 🛡️ HN11 ADMIN\n**Admin:** Nguyễn Văn Ánh")
            st.divider()
            st.markdown("#### 📍 BỘ LỌC ĐỊA BÀN")
            sel_tinh = st.selectbox("Chọn Tỉnh/Thành:", ["Tất cả"] + sorted(df_raw['tinh_thanh'].unique()))
            df_lv2 = df_raw[df_raw['tinh_thanh'] == sel_tinh] if sel_tinh != "Tất cả" else df_raw
            sel_xa = st.selectbox("Chọn Xã/Phường:", ["Tất cả"] + sorted(df_lv2['xa_phuong'].unique()))
            st.divider()
            st.link_button("🔄 KIỂM TRA CẬP NHẬT", "https://your-storage-link.com/updates", width='stretch')
            if st.button("🚪 Đăng xuất", width='stretch'):
                st.session_state.authenticated = False
                st.rerun()

        # Áp dụng bộ lọc và TÌM KIẾM (Đã khôi phục và tối ưu)
        df_filtered = df_lv2 if sel_xa == "Tất cả" else df_lv2[df_lv2['xa_phuong'] == sel_xa]
        
        st.title("📊 HỆ THỐNG QUẢN TRỊ DỮ LIỆU")
        q = st.text_input("🔎 TÌM KIẾM THÔNG MINH:", placeholder="Nhập Tên, MST, Số điện thoại hoặc bất kỳ từ khóa nào...")
        
        if q:
            q_norm = loai_bo_dau(q)
            mask = df_filtered.apply(lambda r: r.astype(str).apply(loai_bo_dau).str.contains(q_norm).any(), axis=1)
            df_filtered = df_filtered[mask]

        # --- THỐNG KÊ BIỂU ĐỒ HÌNH TRÒN (Đã sửa logic hiển thị đúng) ---
        st.divider()
        c_chart, c_metric = st.columns([2, 1])
        with c_chart:
            df_chart = df_filtered['xa_phuong'].value_counts().reset_index()
            df_chart.columns = ['Địa phương', 'Số lượng']
            fig = px.pie(df_chart, values='Số lượng', names='Địa phương', 
                         hole=0.5, height=300, title="Tỷ lệ phân bổ đơn vị theo Xã/Phường")
            fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, use_container_width=True)
        
        with c_metric:
            st.metric("Đang hiển thị", f"{len(df_filtered)} đơn vị")
            st.metric("Tổng hệ thống", len(df_raw))
            st.info(f"📍 Đang lọc: {sel_tinh} - {sel_xa}")

        st.dataframe(df_filtered, width='stretch', hide_index=True)

        # --- XEM TRƯỚC VỚI MÀU SẮC PHÂN LOẠI & KÍCH THƯỚC VỪA PHẢI ---
        st.divider()
        st.subheader("📋 DASHBOARD XEM TRƯỚC CHI TIẾT (HIỂN THỊ TOÀN BỘ DATA)")
        selected = st.selectbox("🎯 Chọn đơn vị cụ thể:", ["-- Vui lòng chọn --"] + df_filtered['ten_don_vi'].tolist())
        
        if selected != "-- Vui lòng chọn --":
            row_data = df_filtered[df_filtered['ten_don_vi'] == selected].iloc[0]
            with st.container(border=True):
                st.markdown(f"#### 🏛️ {row_data['ten_don_vi'].upper()}")
                
                # Hiển thị đa cột với màu sắc chuyên nghiệp
                p_cols = st.columns(3) # 3 cột giúp khung hiển thị vừa vặn, không bị nhỏ
                for idx, (key, val) in enumerate(row_data.items()):
                    with p_cols[idx % 3]:
                        label = key.replace('_', ' ').upper()
                        # Phân loại màu sắc theo nội dung
                        if any(x in key for x in ['mst', 'ma', 'id']):
                            st.info(f"**{label}:**\n{val}")
                        elif any(x in key for x in ['ten', 'chu', 'ke_toan']):
                            st.warning(f"**{label}:**\n{val}")
                        else:
                            st.success(f"**{label}:**\n{val}")
                
                st.divider()
                # Công cụ tải xuống
                btn_pdf, btn_xlsx = st.columns(2)
                with btn_pdf:
                    pdf_bytes = tao_phieu_pdf(row_data)
                    if pdf_bytes:
                        st.download_button("📄 XUẤT PHIẾU PDF CHI TIẾT", pdf_bytes, f"Phieu_{row_data.get('id')}.pdf", "application/pdf", width='stretch', type="primary")
                    else: st.error("Cần file arial.ttf trong thư mục gốc để in PDF.")
                with btn_xlsx:
                    buffer = io.BytesIO()
                    df_filtered.to_excel(buffer, index=False)
                    st.download_button("📊 XUẤT EXCEL DANH SÁCH LỌC", buffer.getvalue(), "HN11_Report.xlsx", width='stretch')

except Exception as e:
    # Đã sửa lỗi SyntaxError dòng 138
    st.error(f"Hệ thống gặp sự cố: {e}")
