import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from fpdf import FPDF
import plotly.express as px
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM HỖ TRỢ PDF ---
def export_pdf(row):
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = "arial.ttf"
        pdf.add_font('ArialVN', '', font_path) if os.path.exists(font_path) else None
        pdf.set_font('ArialVN' if os.path.exists(font_path) else 'Helvetica', size=11)
        
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.ln(5)
        for k, v in row.items():
            if k != 'id': pdf.multi_cell(0, 8, txt=f"{k.upper()}: {v}")
        return bytes(pdf.output())
    except: return None

# --- 3. HÀM XUẤT EXCEL (BẢN SỬA LỖI TRIỆT ĐỂ) ---
def export_special_excel(df):
    try:
        if df.empty: return None
        
        # Hàm hỗ trợ tìm cột không phân biệt hoa thường
        def get_col(df, possible_names):
            for name in possible_names:
                for col in df.columns:
                    if col.lower().strip() == name.lower():
                        return df[col]
            return pd.Series([""] * len(df))

        export_df = pd.DataFrame()
        export_df['STT'] = range(1, len(df) + 1)
        
        # Ánh xạ thông minh: Thử tìm theo nhiều tên khác nhau để tránh bị trống
        export_df['ĐỊA DANH'] = get_col(df, ['huyen_cu', 'khu_vuc', 'dia_danh', 'huyen'])
        
        ten_kh = get_col(df, ['ten_don_vi', 'ten_khach_hang', 'don_vi'])
        export_df['TÊN KHÁCH HÀNG'] = ten_kh.astype(str).str.upper()
        
        export_df['MÃ QUAN HỆ NGÂN SÁCH'] = get_col(df, ['ma_qhns', 'qhns', 'ma_ngan_sach'])
        
        export_df['MÃ KHÁCH HÀNG (SỐ SERIAL)'] = get_col(df, ['san_pham', 'so_serial', 'ma_may', 'serial'])
        
        # Thông tin mặc định
        export_df['PHẦN MỀM'] = "KTHC"
        export_df['LOẠI CÀI ĐẶT'] = "Chuyển giao"
        export_df['NGÀY KÝ HỢP ĐỒNG'] = datetime.now().strftime("%d/%m/%Y")
        export_df['LÝ DO'] = "Cài mới"
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='NHAPLIEU')
            workbook, worksheet = writer.book, writer.sheets['NHAPLIEU']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25)
        return output.getvalue()
    except Exception as e:
        st.error(f"Lỗi kết xuất: {e}")
        return None

# --- 4. KHỞI CHẠY & ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Hệ thống Quản trị HN11")
        u, p = st.text_input("Tài khoản"), st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- 5. TẢI DỮ LIỆU ---
try:
    data = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(data.data)
    
    # --- 6. SIDEBAR THỐNG KÊ ---
    with st.sidebar:
        st.header("📊 THỐNG KÊ")
        c1, c2 = st.columns(2)
        c1.metric("Tổng số", len(df_raw))
        c2.metric("Thiếu SĐT", int(df_raw['sdt_ke_toan'].isna().sum()))
        
        if not df_raw.empty:
            fig = px.pie(df_raw['huyen_cu'].value_counts().reset_index(), values='count', names='huyen_cu',
                         color_discrete_sequence=['#8B4513', '#DAA520', '#D2B48C'])
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1), height=250, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.divider()
        st.link_button("🌐 Tra cứu MST", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 7. QUẢN LÝ ---
    tab1, tab2 = st.tabs(["📋 DANH SÁCH", "📈 PHÂN TÍCH"])
    
    with tab1:
        vung = st.selectbox("Lọc vùng:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
        tim = st.text_input("🔍 Tìm nhanh (MST, Tên, SĐT...):")
        
        df_f = df_raw if vung == "Tất cả" else df_raw[df_raw['huyen_cu'] == vung]
        if tim: df_f = df_f[df_f.apply(lambda x: tim.lower() in str(x.values).lower(), axis=1)]
        
        st.dataframe(df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ma_qhns', 'san_pham']], use_container_width=True, hide_index=True, selection_mode="single-row", key="s", on_select="rerun")
        
        if not df_f.empty:
            st.download_button("📝 XUẤT MẪU CẤP LICENSE (ALL)", export_special_excel(df_f), "Mau_License_Tong_Hop.xlsx", type="primary", use_container_width=True)

        if st.session_state.s.selection.rows:
            row = df_f.iloc[st.session_state.s.selection.rows[0]]
            with st.form("edit"):
                st.write(f"### Chỉnh sửa: {row['ten_don_vi']}")
                c1, c2, c3 = st.columns(3)
                new = {
                    'ten_don_vi': c1.text_input("Tên đơn vị", row['ten_don_vi']).upper(),
                    'mst': c1.text_input("MST", row['mst']),
                    'huyen_cu': c2.text_input("Khu vực", row['huyen_cu']),
                    'ma_qhns': c2.text_input("Mã QHNS", row['ma_qhns']),
                    'ke_toan': c3.text_input("Kế toán", row['ke_toan']),
                    'san_pham': c3.text_input("Số Serial (Mã máy)", row['san_pham'])
                }
                if st.form_submit_button("💾 LƯU", use_container_width=True):
                    supabase.table("don_vi").update(new).eq("mst", row['mst']).execute()
                    st.success("Đã lưu!"); st.rerun()
            
            # Xuất lẻ cho dòng đang chọn
            st.download_button(f"📊 XUẤT MẪU LICENSE: {row['mst']}", export_special_excel(pd.DataFrame([row])), f"License_{row['mst']}.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi kết nối: {e}")
