import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from fpdf import FPDF
import plotly.express as px  # Thêm thư viện biểu đồ

# --- 1. KẾT NỐI HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin - Quản lý tổng thể", layout="wide")

# --- 2. HÀM TẠO PDF ---
def export_pdf(row):
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
            pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ CHI TIẾT", ln=True, align='C')
            pdf.set_font('ArialVN', size=11)
        else:
            pdf.set_font('Helvetica', size=12)
            pdf.cell(0, 10, txt="PHIEU THONG TIN (Thieu font arial.ttf)", ln=True, align='C')

        pdf.ln(10)
        labels = {
            "ten_don_vi": "1. Tên đơn vị", "mst": "2. Mã số thuế", "dia_chi": "3. Địa chỉ",
            "huyen_cu": "4. Khu vực", "ma_qhns": "5. Mã QHNS", "so_tkkb": "6. Số tài khoản KB",
            "ma_kbnn": "7. Mã Kho bạc", "chu_tai_khoan": "8. Chủ tài khoản", "chuc_vu": "9. Chức vụ",
            "ke_toan": "10. Kế toán", "sdt_ke_toan": "11. Số điện thoại", "san_pham": "12. Mã số máy"
        }

        for key, label in labels.items():
            val = str(row.get(key, "Trống"))
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
        
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Quản trị HN11")
        u = st.text_input("Tài khoản")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- 4. TẢI DỮ LIỆU & THỐNG KÊ ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    with st.sidebar:
        st.title("🛡️ HN11 ADMIN")
        
        # Biểu đồ thống kê (Màu Vàng Nâu chủ đạo)
        st.subheader("📊 Thống kê khu vực")
        if not df_raw.empty:
            df_stats = df_raw['huyen_cu'].value_counts().reset_index()
            fig = px.pie(
                df_stats, values='count', names='huyen_cu',
                color_discrete_sequence=['#8B4513', '#D2B48C', '#DAA520', '#F4A460', '#BC8F8F']
            )
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200)
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        h_list = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
        sel_h = st.selectbox("Lọc theo vùng:", h_list)
        
        # Nút kiểm tra cập nhật (Theo yêu cầu trước đó)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        
        if st.button("🚪 Đăng xuất", use_container_width=True): 
            st.session_state.auth = False
            st.rerun()

    # --- 5. TÌM KIẾM ĐA NĂNG ---
    st.subheader("🔍 Tra cứu hệ thống")
    search_q = st.text_input(
        "Tìm kiếm:", 
        placeholder="Nhập Tên đơn vị, MST, Tên kế toán hoặc Số điện thoại..."
    )

    df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]

    if search_q:
        # Tìm kiếm trên nhiều cột cùng lúc
        search_q = search_q.lower()
        mask = (
            df_f['ten_don_vi'].str.lower().str.contains(search_q, na=False) |
            df_f['mst'].astype(str).str.contains(search_q, na=False) |
            df_f['ke_toan'].str.lower().str.contains(search_q, na=False) |
            df_f['sdt_ke_toan'].astype(str).str.contains(search_q, na=False)
        )
        df_f = df_f[mask]

    # --- 6. BẢNG HIỂN THỊ QUẢN TRỊ ---
    # Cấu hình lại các cột hiển thị theo yêu cầu
    view_cols = {
        'mst': 'MST',
        'ten_don_vi': 'Tên Đơn Vị',
        'huyen_cu': 'Huyện cũ',
        'ke_toan': 'Kế toán',
        'sdt_ke_toan': 'Số điện thoại',
        'ma_kbnn': 'Mã Kho bạc',
        'san_pham': 'Mã số máy'
    }

    event = st.dataframe(
        df_f[list(view_cols.keys())].rename(columns=view_cols),
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # --- 7. CHI TIẾT & XUẤT FILE ---
    if event.selection.rows:
        row = df_f.iloc[event.selection.rows[0]]
        st.divider()
        st.markdown(f"### 📋 CHI TIẾT: {row['ten_don_vi'].upper()}")
        
        full_labels = {
            "mst": "Mã số thuế", "ten_don_vi": "Tên đơn vị", "dia_chi": "Địa chỉ",
            "huyen_cu": "Khu vực", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK Kho bạc",
            "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ tài khoản", "chuc_vu": "Chức vụ",
            "ke_toan": "Kế toán", "sdt_ke_toan": "SĐT Kế toán", "san_pham": "Mã máy"
        }
        
        with st.container(border=True):
            keys = list(full_labels.keys())
            for i in range(0, len(keys), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(keys):
                        k = keys[i + j]
                        with cols[j]:
                            st.caption(full_labels[k])
                            st.info(row.get(k, "Trống"))

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
                    pd.DataFrame([row]).to_excel(w, index=False)
                st.download_button("📊 TẢI EXCEL", buf.getvalue(), f"HN11_{row['mst']}.xlsx", use_container_width=True)
            with c2:
                pdf_bytes = export_pdf(row)
                if pdf_bytes:
                    st.download_button("📄 TẢI PDF", pdf_bytes, f"HN11_{row['mst']}.pdf", "application/pdf", use_container_width=True, type="primary")

except Exception as e:
    st.error(f"Đã xảy ra lỗi hệ thống: {e}")
