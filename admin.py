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

st.set_page_config(page_title="HN11 Admin Pro", layout="wide")

# --- 2. HÀM TẠO PDF HỖ TRỢ TIẾNG VIỆT ---
def export_pdf(row):
    try:
        # Sử dụng fpdf2 để hỗ trợ Unicode tốt hơn
        pdf = FPDF()
        pdf.add_page()
        
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
            font_name = 'ArialVN'
        else:
            # Fallback nếu thiếu font (sẽ bị lỗi dấu nhưng không crash)
            pdf.set_font('Helvetica', size=16)
            font_name = 'Helvetica'
            st.warning("⚠️ Không tìm thấy file 'arial.ttf'. PDF sẽ không hiển thị đúng tiếng Việt.")

        # Tiêu đề
        pdf.cell(0, 15, txt=f"PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        
        fields = {
            "Tên đơn vị": "ten_don_vi", "Mã số thuế": "mst", "Địa chỉ": "dia_chi",
            "Khu vực": "huyen_cu", "Mã QHNS": "ma_qhns", "Số TK Kho bạc": "so_tkkb",
            "Mã Kho bạc": "ma_kbnn", "Chủ tài khoản": "chu_tai_khoan", "Chức vụ": "chuc_vu",
            "Kế toán": "ke_toan", "SĐT liên hệ": "sdt_ke_toan", "Mã số máy": "san_pham"
        }

        for label, key in fields.items():
            val = str(row.get(key, "Trống"))
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
        
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. KIỂM TRA ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Hệ thống Quản trị HN11")
        u = st.text_input("Tài khoản", placeholder="Nhập tài khoản...")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin đăng nhập!")
    st.stop()

# --- 4. TẢI DỮ LIỆU & THỐNG KÊ SIDEBAR ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    with st.sidebar:
        st.header("📊 DASHBOARD")
        # KPI Cards
        col_kpi1, col_kpi2 = st.columns(2)
        col_kpi1.metric("Tổng đơn vị", len(df_raw))
        missing = df_raw['sdt_ke_toan'].isna().sum()
        col_kpi2.metric("Thiếu SĐT", missing, delta=f"-{missing}", delta_color="inverse")

        # Biểu đồ tròn Màu Vàng - Nâu
        st.subheader("Tỷ lệ theo vùng")
        if not df_raw.empty:
            df_stats = df_raw['huyen_cu'].value_counts().reset_index()
            fig = px.pie(
                df_stats, values='count', names='huyen_cu',
                color_discrete_sequence=['#8B4513', '#D2B48C', '#DAA520', '#F4A460', '#BC8F8F']
            )
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=220)
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        h_list = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
        sel_h = st.selectbox("Lọc nhanh vùng:", h_list)
        
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 5. TÌM KIẾM ĐA NĂNG & BẢNG QUẢN TRỊ ---
    st.title("📂 QUẢN LÝ NGHIỆP VỤ KẾ TOÁN HN11")
    
    search_q = st.text_input("🔍 Tìm kiếm", placeholder="Nhập Tên đơn vị, MST, Tên kế toán hoặc Số điện thoại...")

    df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]

    if search_q:
        q = search_q.lower()
        mask = (
            df_f['ten_don_vi'].str.lower().str.contains(q, na=False) |
            df_f['mst'].astype(str).str.contains(q, na=False) |
            df_f['ke_toan'].str.lower().str.contains(q, na=False) |
            df_f['sdt_ke_toan'].astype(str).str.contains(q, na=False)
        )
        df_f = df_f[mask]

    # Hiển thị bảng với các cột cơ bản
    view_cols = {
        'mst': 'MST', 'ten_don_vi': 'Tên Đơn Vị', 'huyen_cu': 'Huyện cũ', 
        'ke_toan': 'Kế toán', 'sdt_ke_toan': 'Số điện thoại', 
        'ma_kbnn': 'Mã Kho bạc', 'san_pham': 'Mã số máy'
    }

    st.write(f"Đang hiển thị **{len(df_f)}** đơn vị")
    event = st.dataframe(
        df_f[list(view_cols.keys())].rename(columns=view_cols),
        use_container_width=True, hide_index=True,
        selection_mode="single-row", on_select="rerun"
    )

    # Nút xuất báo cáo hàng loạt cho những gì đang hiển thị
    if not df_f.empty:
        buf_all = io.BytesIO()
        with pd.ExcelWriter(buf_all, engine='xlsxwriter') as w:
            df_f.to_excel(w, index=False)
        st.download_button("📥 Tải danh sách đang lọc (Excel)", buf_all.getvalue(), "HN11_Export.xlsx")

    # --- 6. CHI TIẾT & CHỈNH SỬA DỮ LIỆU ---
    if event.selection.rows:
        idx = event.selection.rows[0]
        row_data = df_f.iloc[idx]
        
        st.divider()
        st.subheader(f"🛠️ Hiệu chỉnh: {row_data['ten_don_vi']}")

        with st.form("update_form"):
            c1, c2, c3 = st.columns(3)
            up_data = {}
            with c1:
                up_data['ten_don_vi'] = st.text_input("Tên đơn vị", row_data['ten_don_vi'])
                up_data['mst'] = st.text_input("Mã số thuế", row_data['mst'])
                up_data['dia_chi'] = st.text_input("Địa chỉ", row_data['dia_chi'])
                up_data['huyen_cu'] = st.text_input("Khu vực", row_data['huyen_cu'])
            with c2:
                up_data['ma_qhns'] = st.text_input("Mã QHNS", row_data['ma_qhns'])
                up_data['so_tkkb'] = st.text_input("Số TK Kho bạc", row_data['so_tkkb'])
                up_data['ma_kbnn'] = st.text_input("Mã Kho bạc", row_data['ma_kbnn'])
                up_data['chu_tai_khoan'] = st.text_input("Chủ tài khoản", row_data['chu_tai_khoan'])
            with c3:
                up_data['chuc_vu'] = st.text_input("Chức vụ", row_data['chuc_vu'])
                up_data['ke_toan'] = st.text_input("Kế toán trưởng", row_data['ke_toan'])
                up_data['sdt_ke_toan'] = st.text_input("Số điện thoại", row_data['sdt_ke_toan'])
                up_data['san_pham'] = st.text_input("Mã số máy", row_data['san_pham'])

            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
            with btn_col1:
                save_btn = st.form_submit_button("💾 LƯU THÔNG TIN", use_container_width=True, type="primary")
            with btn_col2:
                sdt_zalo = str(row_data['sdt_ke_toan']).strip()
                if sdt_zalo and sdt_zalo != "nan":
                    st.link_button("💬 CHAT ZALO", f"https://zalo.me/{sdt_zalo}", use_container_width=True)
            with btn_col3:
                pdf_data = export_pdf(row_data)
                if pdf_data:
                    st.download_button("📄 XUẤT PDF", pdf_data, f"HN11_{row_data['mst']}.pdf", use_container_width=True)
            with btn_col4:
                buf_row = io.BytesIO()
                pd.DataFrame([row_data]).to_excel(buf_row, index=False)
                st.download_button("📊 XUẤT EXCEL", buf_row.getvalue(), f"HN11_{row_data['mst']}.xlsx", use_container_width=True)

            if save_btn:
                try:
                    supabase.table("don_vi").update(up_data).eq("mst", row_data['mst']).execute()
                    st.success("✅ Đã cập nhật dữ liệu thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

except Exception as e:
    st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
