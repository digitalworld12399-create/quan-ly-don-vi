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

# --- 3. PDF ENGINE ---
class VietPDF(FPDF):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_path = "arial.ttf" 
        if os.path.exists(self.font_path):
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
    for col, val in row.items():
        if col in ['xa_phuong', 'tinh_thanh']: continue
        pdf.set_fill_color(240, 240, 240); pdf.set_font(pdf.vfont, 'B', 10)
        pdf.cell(50, 10, f" {str(col).upper()}", border=1, fill=True)
        pdf.set_fill_color(255, 255, 255); pdf.set_font(pdf.vfont, '', 10)
        pdf.multi_cell(0, 10, f" {str(val)}", border=1, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())

# --- 4. LOGIN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col_login, _ = st.columns([1.5, 1, 1.5])
    with col_login:
        st.write("")
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🔐 HN11 LOGIN</h3>", unsafe_allow_html=True)
            u = st.text_input("Tài khoản", placeholder="Nhập tài khoản...", label_visibility="collapsed")
            p = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...", label_visibility="collapsed")
            if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
                if u == "kh" and p == "a11":
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Sai thông tin đăng nhập!")
    st.stop()

# --- 5. MAIN APP ---
try:
    res = supabase.table("don_vi").select("*").execute()
    if res.data:
        df_raw = pd.DataFrame(res.data)
        df_raw[['xa_phuong', 'tinh_thanh']] = df_raw['dia_chi'].apply(lambda x: pd.Series(tach_dia_chi(x)))

        # SIDEBAR
        with st.sidebar:
            st.markdown("### 🛡️ HN11 ADMIN PRO")
            st.caption("Admin: **Nguyễn Văn Ánh**")
            st.divider()
            st.markdown("#### 🔍 BỘ LỌC VÙNG")
            sel_tinh = st.selectbox("Tỉnh/Thành:", ["Tất cả"] + sorted(df_raw['tinh_thanh'].unique()))
            df_lv2 = df_raw[df_raw['tinh_thanh'] == sel_tinh] if sel_tinh != "Tất cả" else df_raw
            sel_xa = st.selectbox("Xã/Phường:", ["Tất cả"] + sorted(df_lv2['xa_phuong'].unique()))
            
            st.divider()
            st.link_button("🔄 KIỂM TRA CẬP NHẬT", "https://your-storage-link.com/updates", use_container_width=True)
            if st.button("🚪 Đăng xuất", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()

        # Dữ liệu lọc cơ bản
        df_f = df_lv2 if sel_xa == "Tất cả" else df_lv2[df_lv2['xa_phuong'] == sel_xa]
        
        # --- TIÊU ĐỀ CHÍNH ---
        st.markdown("## 📊 HỆ THỐNG QUẢN LÝ DỮ LIỆU HN11")
        
        # --- THAY ĐỔI TỶ LỆ: TÌM KIẾM (1) : THỐNG KÊ (3) ---
        col_search, col_chart = st.columns([1, 3])
        
        with col_search:
            with st.container(border=True):
                st.markdown("##### 🔎 Tìm kiếm")
                q = st.text_input("Từ khóa...", placeholder="MST, Tên...", label_visibility="collapsed")
                if q:
                    q_n = loai_bo_dau(q)
                    mask = df_f.apply(lambda r: r.astype(str).apply(loai_bo_dau).str.contains(q_n).any(), axis=1)
                    df_f = df_f[mask]
                
                st.divider()
                st.metric("Kết quả lọc", f"{len(df_f)}")
                st.caption(f"Tổng: {len(df_raw)}")

        with col_chart:
            with st.container(border=True):
                # Tạo 3 cột nhỏ bên trong khu vực thống kê để hiển thị các số liệu phụ
                stat_1, stat_2, chart_area = st.columns([1, 1, 3])
                with stat_1:
                    st.metric("Tỷ lệ hiển thị", f"{(len(df_f)/len(df_raw)*100):.1f}%")
                with stat_2:
                    st.metric("Vùng lọc", sel_xa if sel_xa != "Tất cả" else "Toàn tỉnh")
                
                with chart_area:
                    # Biểu đồ thanh hiển thị phân bổ xã phường
                    chart_data = df_f['xa_phuong'].value_counts().reset_index().head(5)
                    chart_data.columns = ['Khu vực', 'SL']
                    fig = px.bar(chart_data, x='SL', y='Khu vực', orientation='h',
                                 color='SL', color_continuous_scale='Blues',
                                 height=120, text_auto=True)
                    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), coloraxis_showscale=False, 
                                      xaxis_visible=False, yaxis_title=None)
                    st.plotly_chart(fig, use_container_width=True)

        # BẢNG DỮ LIỆU CHÍNH
        st.dataframe(df_f, use_container_width=True, hide_index=True)

        # --- CHI TIẾT ĐƠN VỊ ---
        st.divider()
        st.subheader("📋 THÔNG TIN CHI TIẾT")
        selected = st.selectbox("🎯 Chọn đơn vị:", ["-- Chọn đơn vị --"] + df_f['ten_don_vi'].tolist())
        
        if selected != "-- Chọn đơn vị --":
            row = df_f[df_f['ten_don_vi'] == selected].iloc[0]
            with st.container(border=True):
                st.markdown(f"#### 🏢 {row['ten_don_vi'].upper()}")
                
                # Hiển thị 3 cột thông tin
                items = list(row.items())
                for i in range(0, len(items), 3):
                    cols = st.columns(3)
                    for j in range(3):
                        if i + j < len(items):
                            k, v = items[i + j]
                            with cols[j]:
                                st.markdown(f"**📌 {k.replace('_', ' ').upper()}**")
                                st.info(v if v else "Chưa có dữ liệu")
                
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    pdf_data = tao_phieu_pdf(row)
                    if pdf_data:
                        st.download_button("📄 XUẤT PHIẾU PDF", pdf_data, f"Phieu_{row['id']}.pdf", "application/pdf", use_container_width=True, type="primary")
                with c2:
                    towrite = io.BytesIO()
                    df_f.to_excel(towrite, index=False)
                    st.download_button("📊 XUẤT EXCEL DANH SÁCH", towrite.getvalue(), "HN11_Export.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"🚨 Lỗi: {e}")
