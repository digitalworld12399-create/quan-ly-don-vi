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

# --- 2. HÀM TRUY XUẤT DỮ LIỆU THÔNG MINH (TRÁNH TRỐNG CỘT) ---
def get_safe_data(df, priority_cols):
    """Tìm cột dữ liệu đầu tiên khớp trong danh sách ưu tiên"""
    for col in priority_cols:
        if col in df.columns:
            return df[col].fillna("")
    return pd.Series([""] * len(df))

# --- 3. HÀM XUẤT EXCEL (ĐÃ HIỆU CHỈNH LẤY ĐỦ THÔNG TIN) ---
def export_special_excel(df):
    try:
        if df.empty:
            return None
        
        export_df = pd.DataFrame()
        export_df['STT'] = range(1, len(df) + 1)
        
        # Lấy thông tin từ các cột tương ứng trong Database
        # ĐỊA DANH lấy từ huyen_cu
        export_df['ĐỊA DANH'] = get_safe_data(df, ['huyen_cu', 'khu_vuc', 'dia_danh'])
        
        # TÊN KHÁCH HÀNG lấy từ ten_don_vi
        ten_dv = get_safe_data(df, ['ten_don_vi', 'ten_khach_hang'])
        export_df['TÊN KHÁCH HÀNG'] = ten_dv.apply(lambda x: str(x).upper())
        
        # MÃ QUAN HỆ NGÂN SÁCH lấy từ ma_qhns
        export_df['MÃ QUAN HỆ NGÂN SÁCH'] = get_safe_data(df, ['ma_qhns', 'qhns'])
        
        # MÃ KHÁCH HÀNG (SỐ SERIAL) lấy từ san_pham
        export_df['MÃ KHÁCH HÀNG (SỐ SERIAL)'] = get_safe_data(df, ['san_pham', 'ma_may', 'serial'])
        
        # Các cột mặc định theo yêu cầu
        export_df['PHẦN MỀM'] = "KTHC"
        export_df['LOẠI CÀI ĐẶT'] = "Chuyển giao"
        export_df['NGÀY KÝ HỢP ĐỒNG'] = datetime.now().strftime("%d/%m/%Y")
        export_df['LÝ DO'] = "Cài mới"
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='NHAPLIEU')
            workbook = writer.book
            worksheet = writer.sheets['NHAPLIEU']
            
            # Định dạng tiêu đề cho giống mẫu
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'
            })
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25)
        return output.getvalue()
    except Exception as e:
        st.error(f"Lỗi kết xuất Excel: {e}")
        return None

# --- 4. ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Hệ thống Quản trị HN11")
        u = st.text_input("Tài khoản")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- 5. TẢI DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.header("📊 DASHBOARD")
        c1, c2 = st.columns(2)
        c1.metric("Tổng đơn vị", len(df_raw))
        missing_sdt = int(df_raw['sdt_ke_toan'].isna().sum())
        c2.metric("Thiếu SĐT", missing_sdt)
        
        st.write("---")
        if not df_raw.empty:
            df_stats = df_raw['huyen_cu'].value_counts().reset_index()
            fig_side = px.pie(df_stats, values='count', names='huyen_cu',
                             color_discrete_sequence=['#8B4513', '#DAA520', '#D2B48C'])
            fig_side.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1), height=230, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig_side, use_container_width=True, config={'displayModeBar': False})
        
        st.divider()
        st.link_button("🌐 Tra cứu MST Thuế", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 7. GIAO DIỆN CHÍNH ---
    tab1, tab2 = st.tabs(["📋 QUẢN LÝ", "📈 THỐNG KÊ"])
    
    with tab1:
        vung = st.selectbox("Lọc theo vùng:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
        tim = st.text_input("🔍 Tìm kiếm đơn vị...")
        
        df_f = df_raw if vung == "Tất cả" else df_raw[df_raw['huyen_cu'] == vung]
        if tim:
            df_f = df_f[df_f.apply(lambda x: tim.lower() in str(x.values).lower(), axis=1)]
        
        st.dataframe(df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ma_qhns', 'san_pham']], 
                     use_container_width=True, hide_index=True, selection_mode="single-row", key="table", on_select="rerun")
        
        # NÚT XUẤT TỔNG HỢP
        if not df_f.empty:
            st.download_button("📝 XUẤT MẪU CẤP LICENSE (DANH SÁCH LỌC)", 
                             export_special_excel(df_f), "HN11_License_List.xlsx", 
                             type="primary", use_container_width=True)

        # CHI TIẾT VÀ XUẤT LẺ
        if st.session_state.table.selection.rows:
            idx = st.session_state.table.selection.rows[0]
            row = df_f.iloc[idx]
            st.divider()
            
            with st.form("edit_form"):
                st.write(f"### Hiệu chỉnh: {row['ten_don_vi']}")
                c1, c2, c3 = st.columns(3)
                up = {
                    'ten_don_vi': c1.text_input("Tên đơn vị", row['ten_don_vi']).upper(),
                    'huyen_cu': c2.text_input("Khu vực", row['huyen_cu']),
                    'ma_qhns': c3.text_input("Mã QHNS", row['ma_qhns']),
                    'san_pham': c3.text_input("Số Serial", row['san_pham'])
                }
                if st.form_submit_button("💾 CẬP NHẬT DATABASE"):
                    supabase.table("don_vi").update(up).eq("mst", row['mst']).execute()
                    st.success("Đã cập nhật!"); st.rerun()

            # Nút xuất lẻ cho dòng được chọn
            st.download_button(f"📊 XUẤT MẪU LICENSE CHO {row['mst']}", 
                             export_special_excel(pd.DataFrame([row])), 
                             f"License_{row['mst']}.xlsx", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
