import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import io

# --- 1. KẾT NỐI ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin", layout="wide")

# --- 2. LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    _, col_login, _ = st.columns([1.5, 1, 1.5])
    with col_login:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🔐 HN11 LOGIN</h3>", unsafe_allow_html=True)
            u = st.text_input("Tài khoản", placeholder="Tài khoản", label_visibility="collapsed")
            p = st.text_input("Mật khẩu", type="password", placeholder="Mật khẩu", label_visibility="collapsed")
            if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
                if u == "kh" and p == "a11": st.session_state.auth = True; st.rerun()
                else: st.error("Sai thông tin!")
    st.stop()

# --- 3. XỬ LÝ DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df = pd.DataFrame(res.data)

    with st.sidebar:
        st.header("🛡️ HN11 ADMIN")
        huyen_list = ["Tất cả"] + sorted(df['huyen_cu'].dropna().unique().tolist())
        sel_huyen = st.selectbox("Lọc theo Huyện cũ:", huyen_list)
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True): st.session_state.auth = False; st.rerun()

    df_f = df if sel_huyen == "Tất cả" else df[df['huyen_cu'] == sel_huyen]

    st.markdown("### 📊 DANH SÁCH ĐƠN VỊ")
    st.caption("💡 Mẹo: Click chuột vào một dòng trong bảng để xem chi tiết đơn vị đó.")

    # --- 4. BẢNG HIỂN THỊ CÓ TÍNH NĂNG CHỌN DÒNG ---
    # Sử dụng on_select='rerun' để cập nhật giao diện ngay khi click
    event = st.dataframe(
        df_f, 
        use_container_width=True, 
        hide_index=True,
        selection_mode="single", # Cho phép chọn 1 dòng
        on_select="rerun"        # Tự động chạy lại khi chọn
    )

    # Lấy chỉ số dòng được chọn
    selected_rows = event.selection.rows

    # --- 5. HIỂN THỊ CHI TIẾT KHI CÓ DÒNG ĐƯỢC CHỌN ---
    if len(selected_rows) > 0:
        st.divider()
        # Lấy dữ liệu của dòng được chọn từ dataframe đã lọc
        row_idx = selected_rows[0]
        row = df_f.iloc[row_idx]
        
        st.subheader(f"📋 CHI TIẾT: {row['ten_don_vi'].upper()}")
        
        labels = {
            "mst": "Mã số thuế", "ten_don_vi": "Tên đơn vị", "dia_chi": "Địa chỉ", 
            "huyen_cu": "Khu vực", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK Kho bạc",
            "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "ke_toan": "Kế toán",
            "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã số máy (DTSoft)"
        }
        
        with st.container(border=True):
            cols = st.columns(3)
            for i, (k, label) in enumerate(labels.items()):
                with cols[i % 3]:
                    val = row.get(k, "Trống")
                    st.markdown(f"**📌 {label}**")
                    st.info(val if val else "Trống")
            
            st.divider()
            # Nút xuất dữ liệu
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame([row]).to_excel(writer, index=False)
            st.download_button(
                label=f"📊 XUẤT EXCEL: {row['ten_don_vi']}",
                data=output.getvalue(),
                file_name=f"{row['mst']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
    else:
        st.info("👆 Vui lòng chọn một dòng trong bảng trên để xem chi tiết và xuất tệp.")

except Exception as e: 
    st.error(f"🚨 Lỗi hệ thống: {e}")
