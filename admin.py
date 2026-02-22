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

# Cấu hình layout rộng để các khung hiển thị vừa vặn
st.set_page_config(page_title="HN11 - Admin Dashboard", layout="wide", page_icon="🛡️")

# --- 2. LOGIC XỬ LÝ DỮ LIỆU ---
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

# --- 3. FIX LỖI PDF & FONT (Sửa lỗi image_3c16ad & image_d069bf) ---
class VietPDF(FPDF):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_path = "arial.ttf" # Cần có file này trong thư mục gốc
        if os.path.exists(self.font_path):
            # Khai báo font chuẩn để tránh lỗi Undefined font
            self.add_font('VietFont', '', self.font_path)
            self.add_font('VietFont', 'B', self.font_path)
            self.vfont = 'VietFont'
        else: self.vfont = None

def tao_phieu_pdf(row):
    pdf = VietPDF()
    if not pdf.vfont: return None
    pdf.add_page()
    pdf.set_font(pdf.vfont, 'B', 16)
    pdf.set_text_color(30, 144, 255)
    pdf.cell(0, 15, "PHIẾU CHI TIẾT THÔNG TIN ĐƠN VỊ", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(8)
    # Lặp in toàn bộ dữ liệu vào PDF
    for col, val in row.items():
        if col in ['xa_phuong', 'tinh_thanh']: continue
        pdf.set_fill_color(240, 240, 240); pdf.set_font(pdf.vfont, 'B', 10)
        pdf.cell(50, 10, f" {str(col).upper()}", border=1, fill=True)
        pdf.set_fill_color(255, 255, 255); pdf.set_font(pdf.vfont, '', 10)
        pdf.multi_cell(0, 10, f" {str(val)}", border=1, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    # Xuất định dạng bytes để fix lỗi Invalid binary format
    return bytes(pdf.output())

# --- 4. ĐĂNG NHẬP (KÍCH THƯỚC VỪA PHẢI) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col_login, _ = st.columns([1.2, 1, 1.2]) # Điều chỉnh tỷ lệ cột để khung to hơn trước một chút
    with col_login:
        st.write("")
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🔐 HN11 LOGIN</h3>", unsafe_allow_html=True)
            u = st.text_input("Tài khoản", placeholder="Nhập tài khoản...", label_visibility="collapsed")
            p = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...", label_visibility="collapsed")
            if st.button("ĐĂNG NHẬP", width='stretch', type="primary"):
                if u == "kh" and p == "a11":
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Sai thông tin đăng nhập!")
    st.stop()

# --- 5. GIAO DIỆN CHÍNH ---
try:
    res = supabase.table("don_vi").select("*").execute()
    if res.data:
        df_raw = pd.DataFrame(res.data)
        df_raw[['xa_phuong', 'tinh_thanh']] = df_raw['dia_chi'].apply(lambda x: pd.Series(tach_dia_chi(x)))

        with st.sidebar:
            st.markdown("### 🛡️ HN11 ADMIN PRO\n**Admin:** Nguyễn Văn Ánh")
            st.divider()
            st.markdown("#### 🔍 BỘ LỌC")
            sel_tinh = st.selectbox("Tỉnh/Thành:", ["Tất cả"] + sorted(df_raw['tinh_thanh'].unique()))
            df_lv2 = df_raw[df_raw['tinh_thanh'] == sel_tinh] if sel_tinh != "Tất cả" else df_raw
            sel_xa = st.selectbox("Xã/Phường:", ["Tất cả"] + sorted(df_lv2['xa_phuong'].unique()))
            
            st.divider()
            st.link_button("🔄 KIỂM TRA CẬP NHẬT", "https://your-storage-link.com/updates", width='stretch')
            if st.button("🚪 Đăng xuất", width='stretch'):
                st.session_state.authenticated = False
                st.rerun()

        df_f = df_lv2 if sel_xa == "Tất cả" else df_lv2[df_lv2['xa_phuong'] == sel_xa]

        # --- BIỂU ĐỒ & THỐNG KÊ ---
        st.markdown("### 📊 TỔNG QUAN DỮ LIỆU")
        col_stat1, col_stat2 = st.columns([1, 2])
        with col_stat1:
            st.metric("Kết quả hiển thị", f"{len(df_f)} đơn vị")
            st.metric("Tổng trên hệ thống", f"{len(df_raw)}")
        with col_stat2:
            # Biểu đồ hình tròn thống kê
            fig = px.pie(values=[len(df_f), len(df_raw)-len(df_f)], 
                         names=['Đang lọc', 'Khác'], 
                         hole=0.5, height=180,
                         color_discrete_sequence=['#00B4D8', '#CAF0F8'])
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

        # Tìm kiếm & Bảng
        q = st.text_input("🔎 Tìm kiếm theo từ khóa bất kỳ...", placeholder="MST, Tên, Số điện thoại...")
        if q:
            q_n = loai_bo_dau(q)
            mask = df_f.apply(lambda r: r.astype(str).apply(loai_bo_dau).str.contains(q_n).any(), axis=1)
            df_f = df_f[mask]
        
        st.dataframe(df_f, width='stretch', hide_index=True)

        # --- XEM TRƯỚC CHI TIẾT (FULL DATA) ---
        st.divider()
        st.subheader("📋 DASHBOARD XEM TRƯỚC (HIỂN THỊ TOÀN BỘ DỮ LIỆU)")
        selected = st.selectbox("🎯 Chọn đơn vị để xem đầy đủ thông tin:", ["-- Chọn đơn vị --"] + df_f['ten_don_vi'].tolist())
        
        if selected != "-- Chọn đơn vị --":
            row = df_f[df_f['ten_don_vi'] == selected].iloc[0]
            with st.container(border=True):
                st.markdown(f"#### 🏢 {row['ten_don_vi'].upper()}")
                
                # Tự động hiển thị toàn bộ các cột thông tin có trong Data
                cols = st.columns(3) # Chia 3 cột cho cân đối, không bị nhỏ quá
                items = list(row.items())
                for i, (key, val) in enumerate(items):
                    with cols[i % 3]:
                        st.markdown(f"**📌 {key.replace('_', ' ').upper()}:**")
                        st.success(val if val else "Chưa cập nhật")
                
                st.divider()
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    pdf_data = tao_phieu_pdf(row)
                    if pdf_data:
                        # Fix lỗi binary: Đảm bảo data là bytes và có MIME type
                        st.download_button("📄 XUẤT PHIẾU PDF", pdf_data, f"Phieu_{row['id']}.pdf", "application/pdf", width='stretch', type="primary")
                    else:
                        st.error("Lỗi: Thiếu font arial.ttf để tạo PDF!")
                with c_btn2:
                    towrite = io.BytesIO()
                    df_f.to_excel(towrite, index=False)
                    st.download_button("📊 XUẤT EXCEL DANH SÁCH", towrite.getvalue(), "HN11_Export.xlsx", width='stretch')

# Sửa lỗi SyntaxError tại dòng 138 (đảm bảo khối except đúng vị trí)
except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
