import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from fpdf import FPDF
import plotly.express as px

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Pro - Dashboard", layout="wide")

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

        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
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
            else: st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

# --- 4. TẢI DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # --- 5. SIDEBAR (BÊN TRÁI): THỐNG KÊ BIỂU ĐỒ ---
    with st.sidebar:
        st.header("📊 THỐNG KÊ TỔNG QUAN")
        
        # Chỉ số KPI nhanh
        st.metric("Tổng số đơn vị", len(df_raw))
        
        # Biểu đồ tròn - Màu Vàng Nâu
        if not df_raw.empty:
            st.write("**Tỷ lệ đơn vị theo vùng**")
            df_stats = df_raw['huyen_cu'].value_counts().reset_index()
            fig_side = px.pie(
                df_stats, values='count', names='huyen_cu',
                color_discrete_sequence=['#8B4513', '#DAA520', '#D2B48C', '#F4A460']
            )
            fig_side.update_layout(
                showlegend=True, 
                legend=dict(orientation="h", yanchor="bottom", y=-0.5),
                margin=dict(t=0, b=0, l=0, r=0), 
                height=300
            )
            st.plotly_chart(fig_side, use_container_width=True)

        st.divider()
        st.link_button("🌐 Tra cứu MST Thuế", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 6. MÀN HÌNH CHÍNH (BÊN PHẢI) ---
    tab_manage, tab_analytics = st.tabs(["📋 QUẢN LÝ & TRA CỨU", "📈 PHÂN TÍCH CHI TIẾT"])

    with tab_manage:
        col_search1, col_search2 = st.columns([1, 2])
        with col_search1:
            sel_h = st.selectbox("Lọc nhanh khu vực:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
        with col_search2:
            search_q = st.text_input("🔎 Tìm kiếm (MST, Tên, SĐT, Kế toán...)", placeholder="Nhập từ khóa...")

        # Lọc dữ liệu
        df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]
        if search_q:
            q = search_q.lower()
            df_f = df_f[df_f.apply(lambda x: q in str(x.values).lower(), axis=1)]

        st.write(f"Hiển thị: **{len(df_f)}** dòng")
        event = st.dataframe(
            df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ke_toan', 'sdt_ke_toan', 'san_pham']],
            use_container_width=True, hide_index=True,
            selection_mode="single-row", on_select="rerun"
        )

        # Xuất file Excel hàng loạt cho danh sách đang lọc
        if not df_f.empty:
            buf_all = io.BytesIO()
            df_f.to_excel(buf_all, index=False)
            st.download_button("📥 Tải danh sách lọc (Excel)", buf_all.getvalue(), "HN11_Filtered.xlsx")

        # FORM CHỈNH SỬA KHI CHỌN DÒNG
        if event.selection.rows:
            idx = event.selection.rows[0]
            row_data = df_f.iloc[idx]
            st.divider()
            st.subheader(f"🛠️ Hiệu chỉnh thông tin: {row_data['ten_don_vi']}")
            
            with st.form("edit_form_ultimate"):
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
                    up_data['san_pham'] = st.text_input("Mã máy", row_data['san_pham'])
                
                if st.form_submit_button("💾 LƯU THAY ĐỔI", type="primary", use_container_width=True):
                    supabase.table("don_vi").update(up_data).eq("mst", row_data['mst']).execute()
                    st.success("✅ Đã cập nhật thành công!")
                    st.rerun()

            # Nút tương tác nhanh
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                sdt = str(row_data['sdt_ke_toan']).strip()
                if sdt and sdt != "nan":
                    st.link_button("💬 CHAT ZALO", f"https://zalo.me/{sdt}", use_container_width=True)
            with btn_col2:
                pdf_bytes = export_pdf(row_data)
                st.download_button("📄 TẢI PDF", pdf_bytes, f"HN11_{row_data['mst']}.pdf", use_container_width=True)
            with btn_col3:
                buf_row = io.BytesIO()
                pd.DataFrame([row_data]).to_excel(buf_row, index=False)
                st.download_button("📊 TẢI EXCEL", buf_row.getvalue(), f"HN11_{row_data['mst']}.xlsx", use_container_width=True)

    with tab_analytics:
        st.subheader("📊 Phân tích dữ liệu chuyên sâu")
        # Biểu đồ cột ngang thống kê độ đầy đủ dữ liệu
        valid_stats = df_raw.notna().sum().drop(['id'], errors='ignore')
        fig_bar = px.bar(
            x=valid_counts.values if 'valid_counts' in locals() else valid_stats.values, 
            y=valid_stats.index, 
            orientation='h',
            title="Độ phủ thông tin các trường dữ liệu",
            color_discrete_sequence=['#DAA520']
        )
        st.plotly_chart(fig_bar, use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
