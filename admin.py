import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import io

# --- 1. KẾT NỐI SUPABASE ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 - Admin Panel", layout="wide")

# --- 2. HỆ THỐNG XÁC THỰC ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: #1E90FF;'>🔐 ĐĂNG NHẬP QUẢN TRỊ</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        user = st.text_input("Tên đăng nhập")
        pw = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập", use_container_width=True, type="primary"):
            if user == "kh" and pw == "a11":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

# --- 3. GIAO DIỆN SAU KHI ĐĂNG NHẬP ---
with st.sidebar:
    st.markdown(f"""
    <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid #1E90FF;">
        <h3 style="margin-top:0;">🛡️ HN11 ADMIN</h3>
        <p style="margin-bottom:5px;">👤 <b>Admin:</b> Nguyễn Văn Ánh</p>
        <p style="margin-bottom:5px;">📞 <b>ĐT:</b> 0969.338.332</p>
        <p style="margin-bottom:0;">🔖 <b>Phiên bản:</b> 2.0.1</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    st.link_button("🔄 KIỂM TRA CẬP NHẬT", "https://your-storage-link.com/updates", use_container_width=True)
    if st.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("📊 QUẢN LÝ DỮ LIỆU HN11")
tab1, tab2 = st.tabs(["📂 Danh sách đơn vị", "🕒 Nhật ký chi tiết"])

with tab1:
    try:
        # Lấy dữ liệu từ Supabase
        res = supabase.table("don_vi").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            
            # Chỉ định các cột hiển thị để tránh lỗi dữ liệu lạ
            display_cols = ['mst', 'ten_don_vi', 'ma_qhns', 'so_tkkb', 'ma_kbnn', 'chu_tai_khoan', 'ke_toan', 'sdt_ke_toan']
            existing_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(df[existing_cols], use_container_width=True)

            # --- XỬ LÝ XUẤT EXCEL (Sử dụng ExcelWriter an toàn) ---
            towrite = io.BytesIO()
            # Dùng engine 'xlsxwriter' nếu có, nếu không sẽ dùng mặc định
            df.to_excel(towrite, index=False, header=True)
            towrite.seek(0)
            
            st.download_button(
                label="📥 TẢI FILE EXCEL (.xlsx)",
                data=towrite,
                file_name=f"HN11_Data_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.info("Chưa có dữ liệu đơn vị.")
    except Exception as e:
        st.error(f"Lỗi hiển thị dữ liệu: {e}")

with tab2:
    try:
        res_log = supabase.table("lich_su_cap_nhat").select("*").order("thoi_gian", desc=True).execute()
        if res_log.data:
            df_log = pd.DataFrame(res_log.data)
            st.table(df_log[['mst', 'ten_don_vi', 'han_dong', 'thoi_gian']].head(20))
        else:
            st.info("Nhật ký trống.")
    except:
        st.warning("Không thể tải nhật ký.")
