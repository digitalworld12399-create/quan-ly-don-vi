import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from fpdf import FPDF
import plotly.express as px
import plotly.graph_objects as go

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
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
            font_name = 'ArialVN'
        else:
            pdf.set_font('Helvetica', size=16)
            font_name = 'Helvetica'

        pdf.cell(0, 15, txt=f"PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        
        fields = {
            "Tên đơn vị": "ten_don_vi", "Mã số thuế": "mst", "Địa chỉ": "dia_chi",
            "Khu vực": "huyen_cu", "Mã QHNS": "ma_qhns", "Số TK Kho bạc": "so_tkkb",
            "Mã Kho bạc": "ma_kbnn", "Chủ tài khoản": "chu_tai_khoan", "Chức vụ": "chuc_vu",
            "Kế toán trưởng": "ke_toan", "Số điện thoại": "sdt_ke_toan", "Mã máy": "san_pham"
        }
        for label, key in fields.items():
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
        st.subheader("🛡️ Trung tâm Quản trị HN11")
        u = st.text_input("Tài khoản Admin")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Truy cập bị từ chối!")
    st.stop()

# --- 4. XỬ LÝ DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # Sidebar chung
    with st.sidebar:
        st.header("🎮 ĐIỀU KHIỂN")
        st.link_button("🌐 Tra cứu MST (Tổng cục Thuế)", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Link cập nhật phần mềm", "https://your-update-link.com", use_container_width=True)
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            st.session_state.auth = False
            st.rerun()

    # CHIA TABS CHÍNH
    tab_manage, tab_analytics, tab_logs = st.tabs(["📋 QUẢN LÝ ĐƠN VỊ", "📈 BÁO CÁO BI", "⚙️ CẤU HÌNH"])

    # --- TAB 1: QUẢN LÝ ĐƠN VỊ ---
    with tab_manage:
        col_f1, col_f2 = st.columns([1, 3])
        with col_f1:
            sel_h = st.selectbox("Vùng:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
        with col_f2:
            search_q = st.text_input("🔎 Tìm kiếm nhanh (MST, Tên, Kế toán, SĐT...)", placeholder="Nhập từ khóa...")

        # Filter logic
        df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]
        if search_q:
            q = search_q.lower()
            df_f = df_f[df_f.apply(lambda x: q in str(x.values).lower(), axis=1)]

        st.dataframe(
            df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ke_toan', 'sdt_ke_toan', 'san_pham']],
            use_container_width=True, hide_index=True,
            selection_mode="single-row", key="main_table", on_select="rerun"
        )

        # Hiển thị Chi tiết & Form Edit khi chọn dòng
        if st.session_state.main_table.selection.rows:
            idx = st.session_state.main_table.selection.rows[0]
            row_data = df_f.iloc[idx]
            
            st.markdown(f"### 🛠️ Chỉnh sửa: {row_data['ten_don_vi']}")
            with st.form("edit_form"):
                c1, c2, c3 = st.columns(3)
                up_data = {}
                with c1:
                    up_data['ten_don_vi'] = st.text_input("Tên đơn vị", row_data['ten_don_vi'])
                    up_data['mst'] = st.text_input("Mã số thuế", row_data['mst'])
                    up_data['dia_chi'] = st.text_input("Địa chỉ", row_data['dia_chi'])
                with c2:
                    up_data['huyen_cu'] = st.text_input("Khu vực", row_data['huyen_cu'])
                    up_data['ma_qhns'] = st.text_input("Mã QHNS", row_data['ma_qhns'])
                    up_data['so_tkkb'] = st.text_input("Số TK Kho bạc", row_data['so_tkkb'])
                with c3:
                    up_data['ke_toan'] = st.text_input("Kế toán", row_data['ke_toan'])
                    up_data['sdt_ke_toan'] = st.text_input("Số điện thoại", row_data['sdt_ke_toan'])
                    up_data['san_pham'] = st.text_input("Mã số máy", row_data['san_pham'])
                
                if st.form_submit_button("💾 CẬP NHẬT DATABASE", type="primary"):
                    supabase.table("don_vi").update(up_data).eq("mst", row_data['mst']).execute()
                    st.success("Đã lưu!")
                    st.rerun()

            # Nút tương tác nhanh ngoài Form
            btn_c1, btn_c2, btn_c3, btn_c4 = st.columns(4)
            with btn_c1:
                sdt = str(row_data['sdt_ke_toan']).strip()
                if sdt and sdt != "nan":
                    st.link_button("💬 ZALO KẾ TOÁN", f"https://zalo.me/{sdt}", use_container_width=True)
            with btn_c2:
                pdf = export_pdf(row_data)
                st.download_button("📄 XUẤT PDF", pdf, f"HN11_{row_data['mst']}.pdf", use_container_width=True)
            with btn_c3:
                buf = io.BytesIO()
                pd.DataFrame([row_data]).to_excel(buf, index=False)
                st.download_button("📊 XUẤT EXCEL", buf.getvalue(), f"HN11_{row_data['mst']}.xlsx", use_container_width=True)
            with btn_c4:
                st.button("🗑️ XÓA ĐƠN VỊ (Soft)", help="Chuyển vào trạng thái lưu trữ", use_container_width=True)

    # --- TAB 2: BÁO CÁO BI ---
    with tab_analytics:
        st.subheader("📈 Phân tích Hệ thống")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng đơn vị", len(df_raw))
        m2.metric("Số Huyện quản lý", df_raw['huyen_cu'].nunique())
        m3.metric("Thiếu SĐT", int(df_raw['sdt_ke_toan'].isna().sum()), delta_color="inverse")
        m4.metric("Dữ liệu trống (%)", f"{int((df_raw.isna().sum().sum() / df_raw.size) * 100)}%")

        c_graph1, c_graph2 = st.columns(2)
        with c_graph1:
            st.write("**Phân bổ theo khu vực (Vàng - Nâu)**")
            fig_pie = px.pie(df_raw, names='huyen_cu', hole=0.4,
                             color_discrete_sequence=['#8B4513', '#DAA520', '#D2B48C', '#F4A460'])
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c_graph2:
            st.write("**Độ phủ dữ liệu theo trường thông tin**")
            valid_counts = df_raw.notna().sum().drop(['id'] if 'id' in df_raw.columns else [])
            fig_bar = px.bar(x=valid_counts.values, y=valid_counts.index, orientation='h',
                             color_discrete_sequence=['#DAA520'])
            st.plotly_chart(fig_bar, use_container_width=True)

    # --- TAB 3: CẤU HÌNH ---
    with tab_logs:
        st.subheader("⚙️ Cấu hình & Bảo mật")
        with st.expander("Xuất toàn bộ Database"):
            buf_full = io.BytesIO()
            df_raw.to_excel(buf_full, index=False)
            st.download_button("📥 TẢI TOÀN BỘ FILE EXCEL DỰ PHÒNG", buf_full.getvalue(), "Backup_HN11_Full.xlsx")
        
        st.info("💡 **Ghi chú Admin:** Luôn kiểm tra file arial.ttf trước khi xuất PDF để tránh lỗi font tiếng Việt.")
        st.warning("Tính năng 'Thùng rác' và 'Log hoạt động' đang được phát triển ở phiên bản tiếp theo.")

except Exception as e:
    st.error(f"Hệ thống gặp sự cố: {e}")
