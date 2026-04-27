import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
from fpdf import FPDF
import plotly.express as px

# --- 1. CẤU HÌNH & KẾT NỐI ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Hệ thống Quản trị HN11 Pro", layout="wide")

# --- 2. HÀM TRỢ GIÚP ---
def export_pdf(row):
    try:
        pdf = FPDF()
        pdf.add_page()
        # Ưu tiên font ArialVN nếu có, nếu không dùng Helvetica
        font_path = "arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font('ArialVN', '', font_path)
            pdf.set_font('ArialVN', size=16)
        else:
            pdf.set_font('Helvetica', size=16)
        
        pdf.cell(0, 15, txt=f"PHIẾU THÔNG TIN: {row['ten_don_vi']}", ln=True, align='C')
        pdf.ln(10)
        
        fields = [
            ("Mã số thuế", "mst"), ("Địa chỉ", "dia_chi"), ("Khu vực", "huyen_cu"),
            ("Mã QHNS", "ma_qhns"), ("TK Kho bạc", "so_tkkb"), ("Mã KBNN", "ma_kbnn"),
            ("Chủ tài khoản", "chu_tai_khoan"), ("Chức vụ", "chuc_vu"),
            ("Kế toán", "ke_toan"), ("SĐT liên hệ", "sdt_ke_toan"), ("Mã máy", "san_pham")
        ]
        
        for label, key in fields:
            pdf.set_font('Helvetica', size=11) # Dùng font chuẩn để an toàn
            pdf.multi_cell(0, 8, txt=f"{label}: {row.get(key, 'Trống')}")
        
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. KIỂM TRA ĐĂNG NHẬP ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Đăng nhập Hệ thống HN11")
        u = st.text_input("Tài khoản")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- 4. TẢI DỮ LIỆU & XỬ LÝ ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # --- SIDEBAR: THỐNG KÊ & BỘ LỌC ---
    with st.sidebar:
        st.title("🛡️ HN11 ADMIN")
        
        # KPI nhanh
        c1, c2 = st.columns(2)
        c1.metric("Tổng đơn vị", len(df_raw))
        missing_count = df_raw['sdt_ke_toan'].isna().sum()
        c2.metric("Thiếu SĐT", missing_count, delta_color="inverse")

        st.divider()
        st.subheader("📊 Tỷ lệ khu vực")
        if not df_raw.empty:
            df_stats = df_raw['huyen_cu'].value_counts().reset_index()
            fig = px.pie(
                df_stats, values='count', names='huyen_cu',
                color_discrete_sequence=['#8B4513', '#D2B48C', '#DAA520', '#F4A460']
            )
            fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=200)
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        h_list = ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist())
        sel_h = st.selectbox("Lọc theo vùng:", h_list)
        
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 5. GIAO DIỆN CHÍNH ---
    # Thanh tìm kiếm đa năng
    search_q = st.text_input("🔍 Tìm kiếm thông minh", placeholder="Nhập Tên, MST, SĐT, Kế toán...")

    # Lọc dữ liệu
    df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]
    if search_q:
        q = search_q.lower()
        df_f = df_f[
            df_f['ten_don_vi'].str.lower().str.contains(q, na=False) |
            df_f['mst'].astype(str).str.contains(q, na=False) |
            df_f['ke_toan'].str.lower().str.contains(q, na=False) |
            df_f['sdt_ke_toan'].astype(str).str.contains(q, na=False)
        ]

    # Hiển thị bảng quản trị
    view_cols = {
        'mst': 'MST', 'ten_don_vi': 'Tên Đơn Vị', 'huyen_cu': 'Huyện cũ', 
        'ke_toan': 'Kế toán', 'sdt_ke_toan': 'SĐT', 'ma_kbnn': 'Mã KB', 'san_pham': 'Mã máy'
    }
    
    st.info(f"Tìm thấy {len(df_f)} kết quả. Click chọn 1 dòng để xem/sửa.")
    event = st.dataframe(
        df_f[list(view_cols.keys())].rename(columns=view_cols),
        use_container_width=True, hide_index=True,
        selection_mode="single-row", on_select="rerun"
    )

    # Nút xuất báo cáo hàng loạt (tất cả những gì đang lọc)
    if not df_f.empty:
        buf_all = io.BytesIO()
        with pd.ExcelWriter(buf_all, engine='xlsxwriter') as w:
            df_f.to_excel(w, index=False, sheet_name="Bao_Cao")
        st.download_button("📥 Xuất toàn bộ danh sách đang lọc (Excel)", buf_all.getvalue(), "Danh_sach_HN11.xlsx")

    # --- 6. FORM CHI TIẾT & CHỈNH SỬA ---
    if event.selection.rows:
        row_idx = event.selection.rows[0]
        row_data = df_f.iloc[row_idx]
        
        st.divider()
        st.subheader(f"🛠️ CHI TIẾT & CẬP NHẬT: {row_data['ten_don_vi']}")

        # Chia Form thành 3 cột để chỉnh sửa
        with st.form("edit_form"):
            col1, col2, col3 = st.columns(3)
            
            # Lưu các widget vào dict để lấy giá trị sau khi submit
            new_data = {}
            with col1:
                new_data['ten_don_vi'] = st.text_input("Tên đơn vị", row_data['ten_don_vi'])
                new_data['mst'] = st.text_input("Mã số thuế", row_data['mst'])
                new_data['dia_chi'] = st.text_input("Địa chỉ", row_data['dia_chi'])
                new_data['huyen_cu'] = st.text_input("Vùng/Huyện", row_data['huyen_cu'])
            with col2:
                new_data['ma_qhns'] = st.text_input("Mã QHNS", row_data['ma_qhns'])
                new_data['so_tkkb'] = st.text_input("Số TK Kho bạc", row_data['so_tkkb'])
                new_data['ma_kbnn'] = st.text_input("Mã KBNN", row_data['ma_kbnn'])
                new_data['chu_tai_khoan'] = st.text_input("Chủ tài khoản", row_data['chu_tai_khoan'])
            with col3:
                new_data['chuc_vu'] = st.text_input("Chức vụ", row_data['chuc_vu'])
                new_data['ke_toan'] = st.text_input("Kế toán", row_data['ke_toan'])
                new_data['sdt_ke_toan'] = st.text_input("Số điện thoại", row_data['sdt_ke_toan'])
                new_data['san_pham'] = st.text_input("Mã số máy", row_data['san_pham'])

            c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
            with c_btn1:
                submitted = st.form_submit_button("💾 LƯU THAY ĐỔI", use_container_width=True, type="primary")
            with c_btn2:
                # Tính năng gửi Zalo
                sdt = str(row_data['sdt_ke_toan']).strip()
                if sdt and sdt != "nan":
                    st.link_button(f"💬 CHAT ZALO", f"https://zalo.me/{sdt}", use_container_width=True)
            with c_btn3:
                # Xuất PDF
                pdf_bytes = export_pdf(row_data)
                if pdf_bytes:
                    st.download_button("📄 TẢI PDF", pdf_bytes, f"HN11_{row_data['mst']}.pdf", use_container_width=True)
            with c_btn4:
                # Xuất Excel lẻ
                buf_single = io.BytesIO()
                pd.DataFrame([row_data]).to_excel(buf_single, index=False)
                st.download_button("📊 TẢI EXCEL", buf_single.getvalue(), f"HN11_{row_data['mst']}.xlsx", use_container_width=True)

            if submitted:
                # Cập nhật vào Supabase
                try:
                    supabase.table("don_vi").update(new_data).eq("mst", row_data['mst']).execute()
                    st.success("Đã cập nhật dữ liệu thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi cập nhật: {e}")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
