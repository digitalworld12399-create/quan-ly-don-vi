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

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM HỖ TRỢ PDF UNICODE ---
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

        # Đảm bảo tên đơn vị trên PDF cũng viết hoa
        ten_dv_hoa = str(row['ten_don_vi']).upper()
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        
        fields = {
            "Tên đơn vị": ten_dv_hoa, "Mã số thuế": "mst", "Địa chỉ": "dia_chi",
            "Khu vực": "huyen_cu", "Mã QHNS": "ma_qhns", "Số TK Kho bạc": "so_tkkb",
            "Mã Kho bạc": "ma_kbnn", "Chủ tài khoản": "chu_tai_khoan", "Chức vụ": "chuc_vu",
            "Kế toán trưởng": "ke_toan", "Số điện thoại": "sdt_ke_toan", "Mã máy": "san_pham"
        }
        for label, key in fields.items():
            # Nếu key là chuỗi (tên cột) thì lấy giá trị, nếu không thì lấy giá trị trực tiếp (như ten_dv_hoa)
            val = str(row.get(key, key)) if isinstance(key, str) and key in row else str(key)
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. GIAO DIỆN ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Hệ thống Quản trị HN11")
        u = st.text_input("Tài khoản Admin")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin đăng nhập!")
    st.stop()

# --- 4. TẢI DỮ LIỆU & XỬ LÝ ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # TỰ ĐỘNG VIẾT HOA TÊN ĐƠN VỊ KHI HIỂN THỊ
    if not df_raw.empty and 'ten_don_vi' in df_raw.columns:
        df_raw['ten_don_vi'] = df_raw['ten_don_vi'].str.upper()

    # --- 5. SIDEBAR: THỐNG KÊ TỐI ƯU ---
    with st.sidebar:
        st.header("📊 Chào bạn Nguyễn Ánh")
        c_kpi1, c_kpi2 = st.columns(2)
        c_kpi1.metric("Tổng đơn vị", len(df_raw))
        missing_sdt = int(df_raw['sdt_ke_toan'].isna().sum())
        c_kpi2.metric("Thiếu SĐT", missing_sdt, delta=f"-{missing_sdt}", delta_color="inverse")
        
        st.write("---")
        if not df_raw.empty:
            st.caption("**Tỷ lệ đơn vị theo khu vực**")
            df_stats = df_raw['huyen_cu'].value_counts().reset_index()
            fig_side = px.pie(
                df_stats, values='count', names='huyen_cu',
                color_discrete_sequence=['#8B4513', '#DAA520', '#D2B48C', '#F4A460']
            )
            fig_side.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=10)),
                margin=dict(t=10, b=10, l=10, r=10),
                height=250
            )
            st.plotly_chart(fig_side, use_container_width=True, config={'displayModeBar': False})

        st.write("---")
        st.subheader("🔗 TIỆN ÍCH")
        st.link_button("🌐 Tra cứu MST Thuế", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            st.session_state.auth = False
            st.rerun()

    # --- 6. MÀN HÌNH CHÍNH ---
    tab_mgt, tab_bi = st.tabs(["📋 QUẢN LÝ NGHIỆP VỤ", "📈 PHÂN TÍCH CHUYÊN SÂU"])

    with tab_mgt:
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            sel_h = st.selectbox("Vùng:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
        with col_s2:
            search_q = st.text_input("🔍 Tìm kiếm thông minh", placeholder="Tên đơn vị, MST, SĐT, Kế toán...")

        df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]
        if search_q:
            q = search_q.lower()
            df_f = df_f[df_f.apply(lambda x: q in str(x.values).lower(), axis=1)]

        st.dataframe(
            df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ke_toan', 'sdt_ke_toan', 'san_pham']],
            use_container_width=True, hide_index=True,
            selection_mode="single-row", key="table_select", on_select="rerun"
        )

        if st.session_state.table_select.selection.rows:
            idx = st.session_state.table_select.selection.rows[0]
            row = df_f.iloc[idx]
            
            st.divider()
            st.subheader(f"🛠️ Hiệu chỉnh: {row['ten_don_vi']}")
            
            with st.form("ultimate_edit_form"):
                f1, f2, f3 = st.columns(3)
                up = {}
                with f1:
                    # Viết hoa tự động trong ô nhập liệu
                    up['ten_don_vi'] = st.text_input("Tên đơn vị", value=str(row['ten_don_vi']).upper())
                    up['mst'] = st.text_input("MST", row['mst'])
                    up['dia_chi'] = st.text_input("Địa chỉ", row['dia_chi'])
                with f2:
                    up['huyen_cu'] = st.text_input("Khu vực", row['huyen_cu'])
                    up['ma_qhns'] = st.text_input("Mã QHNS", row['ma_qhns'])
                    up['so_tkkb'] = st.text_input("Số TK Kho bạc", row['so_tkkb'])
                with f3:
                    up['ke_toan'] = st.text_input("Kế toán", row['ke_toan'])
                    up['sdt_ke_toan'] = st.text_input("SĐT", row['sdt_ke_toan'])
                    up['san_pham'] = st.text_input("Mã máy", row['san_pham'])
                
                if st.form_submit_button("💾 LƯU THAY ĐỔI (Sẽ tự động viết hoa tên)", type="primary", use_container_width=True):
                    # Ép kiểu viết hoa trước khi gửi lên Database
                    up['ten_don_vi'] = up['ten_don_vi'].upper()
                    supabase.table("don_vi").update(up).eq("mst", row['mst']).execute()
                    st.success("Đã cập nhật thành công!")
                    st.rerun()

            b1, b2, b3 = st.columns(3)
            with b1:
                sdt = str(row['sdt_ke_toan']).strip()
                if sdt and sdt != "nan":
                    st.link_button("💬 ZALO KẾ TOÁN", f"https://zalo.me/{sdt}", use_container_width=True)
            with b2:
                pdf_data = export_pdf(row)
                st.download_button("📄 XUẤT PDF", pdf_data, f"HN11_{row['mst']}.pdf", use_container_width=True)
            with b3:
                buf_r = io.BytesIO()
                pd.DataFrame([row]).to_excel(buf_r, index=False)
                st.download_button("📊 XUẤT EXCEL", buf_r.getvalue(), f"HN11_{row['mst']}.xlsx", use_container_width=True)

    with tab_bi:
        st.subheader("📊 Phân tích Chất lượng Dữ liệu")
        valid_stats = df_raw.notna().sum().drop(['id'], errors='ignore')
        fig_bar = px.bar(
            x=valid_stats.values, y=valid_stats.index, orientation='h',
            title="Mức độ hoàn thiện thông tin",
            color_discrete_sequence=['#DAA520']
        )
        st.plotly_chart(fig_bar, use_container_width=True)

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
