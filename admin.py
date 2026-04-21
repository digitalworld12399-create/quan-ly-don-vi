import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import io

# --- 1. KẾT NỐI HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 - Admin Dashboard", layout="wide", page_icon="🛡️")

# --- 2. KIỂM TRA ĐĂNG NHẬP ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    _, col_login, _ = st.columns([1.5, 1, 1.5])
    with col_login:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🔐 HN11 LOGIN</h3>", unsafe_allow_html=True)
            u = st.text_input("Tài khoản", placeholder="Tài khoản", label_visibility="collapsed")
            p = st.text_input("Mật khẩu", type="password", placeholder="Mật khẩu", label_visibility="collapsed")
            if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
                if u == "kh" and p == "a11":
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Sai thông tin đăng nhập!")
    st.stop()

# --- 3. TẢI DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    if res.data:
        df_raw = pd.DataFrame(res.data)

        # --- 4. THANH BÊN (SIDEBAR) ---
        with st.sidebar:
            st.markdown("### 🛡️ HN11 ADMIN PRO")
            st.caption("Quản trị: **Nguyễn Văn Ánh**")
            st.divider()
            
            st.markdown("#### 🔍 BỘ LỌC VÙNG")
            list_huyen = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
            sel_huyen = st.selectbox("Huyện cũ (HN11):", list_huyen)
            
            df_filtered = df_raw if sel_huyen == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_huyen]
            
            st.divider()
            # Nút dẫn link cập nhật theo yêu cầu trước đó
            st.link_button("🔄 KIỂM TRA CẬP NHẬT", "https://your-storage-link.com/updates", use_container_width=True)
            if st.button("🚪 Đăng xuất", use_container_width=True):
                st.session_state.auth = False
                st.rerun()

        # --- 5. GIAO DIỆN CHÍNH ---
        st.markdown("### 📊 QUẢN LÝ DỮ LIỆU HN11")
        
        # Bổ sung chức năng Tìm kiếm (đã có trước đó)
        search_q = st.text_input("🔎 Tìm kiếm thông tin", placeholder="Nhập Mã số thuế hoặc Tên đơn vị để tìm nhanh...")
        
        if search_q:
            # Lọc theo MST hoặc Tên đơn vị
            df_f = df_filtered[
                df_filtered['mst'].astype(str).str.contains(search_q, case=False) | 
                df_filtered['ten_don_vi'].str.contains(search_q, case=False)
            ]
        else:
            df_f = df_filtered

        # Thống kê nhanh
        c1, c2, c3 = st.columns([1, 1, 2])
        c1.metric("Tổng đơn vị", len(df_raw))
        c2.metric("Kết quả lọc", len(df_f))
        with c3:
            chart_data = df_f['huyen_cu'].value_counts().reset_index()
            fig = px.bar(chart_data, x='count', y='huyen_cu', orientation='h', height=130, 
                         color='count', color_continuous_scale='Blues')
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # --- 6. BẢNG DỮ LIỆU (CLICK CHỌN DÒNG) ---
        st.info("💡 **Hướng dẫn:** Gõ tìm kiếm phía trên, sau đó **Click chọn một dòng** bên dưới để xem chi tiết.")
        
        event = st.dataframe(
            df_f, 
            use_container_width=True, 
            hide_index=True,
            selection_mode="single-row", # Chỉ chọn 1 dòng
            on_select="rerun"
        )

        selected_rows = event.selection.rows

        # --- 7. HIỂN THỊ CHI TIẾT ---
        if len(selected_rows) > 0:
            st.divider()
            row_idx = selected_rows[0]
            row = df_f.iloc[row_idx]
            
            st.markdown(f"#### 📋 CHI TIẾT ĐƠN VỊ: {row['ten_don_vi'].upper()}")
            
            labels = {
                "mst": "Mã số thuế", "ten_don_vi": "Tên đơn vị", "dia_chi": "Địa chỉ", 
                "huyen_cu": "Khu vực", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK Kho bạc",
                "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "chuc_vu": "Chức danh",
                "ke_toan": "Kế toán", "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã số máy (DTSoft)"
            }
            
            with st.container(border=True):
                grid_cols = st.columns(3)
                for i, (key, label) in enumerate(labels.items()):
                    with grid_cols[i % 3]:
                        val = row.get(key, "")
                        st.markdown(f"**📌 {label}**")
                        st.info(val if val else "Chưa có dữ liệu")
                
                st.divider()
                
                # Chức năng xuất Excel (đã sửa lỗi engine)
                output = io.BytesIO()
                try:
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        pd.DataFrame([row]).to_excel(writer, index=False)
                    
                    st.download_button(
                        label=f"📊 TẢI FILE EXCEL: {row['ten_don_vi']}",
                        data=output.getvalue(),
                        file_name=f"HN11_{row['mst']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                except Exception as ex:
                    st.error(f"Vui lòng cài đặt thư viện để xuất Excel: pip install xlsxwriter")
        else:
            st.write("---")
            st.caption("Gợi ý: Chọn một dòng trong bảng danh sách để thực hiện các thao tác quản lý.")

except Exception as e:
    st.error(f"🚨 Lỗi hệ thống: {e}")
