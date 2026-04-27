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

        ten_dv_hoa = str(row.get('ten_don_vi', '')).upper()
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
            val = str(row.get(key, key)) if isinstance(key, str) and key in row else str(key)
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return None

# --- 3. HÀM XUẤT EXCEL THEO BIỂU MẪU ĐẶC THÙ (FIX LỖI THIẾU DỮ LIỆU) ---
def export_special_excel(df):
    try:
        if df.empty:
            return None
        
        # Tạo bản sao để không làm ảnh hưởng đến dữ liệu gốc trên màn hình
        data_to_export = df.copy()
        
        export_df = pd.DataFrame()
        
        # Ánh xạ chính xác các trường dựa trên yêu cầu
        export_df['STT'] = range(1, len(data_to_export) + 1)
        
        # Lấy dữ liệu và xử lý giá trị trống (NaN) thành chuỗi rỗng
        export_df['ĐỊA DANH'] = data_to_export['huyen_cu'].fillna('')
        
        # Đảm bảo Tên khách hàng luôn viết hoa
        export_df['TÊN KHÁCH HÀNG'] = data_to_export['ten_don_vi'].fillna('').apply(lambda x: str(x).upper())
        
        export_df['MÃ QUAN HỆ NGÂN SÁCH'] = data_to_export['ma_qhns'].fillna('')
        export_df['MÃ KHÁCH HÀNG (SỐ SERIAL)'] = data_to_export['san_pham'].fillna('')
        
        # Các thông tin mặc định cố định
        export_df['PHẦN MỀM'] = "KTHC"
        export_df['LOẠI CÀI ĐẶT'] = "Chuyển giao"
        export_df['NGÀY KÝ HỢP ĐỒNG'] = datetime.now().strftime("%d/%m/%Y")
        export_df['LÝ DO'] = "Cài mới"
        
        # Tạo file Excel trong bộ nhớ
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='NHAPLIEU')
            
            workbook = writer.book
            worksheet = writer.sheets['NHAPLIEU']
            
            # Định dạng tiêu đề (Header) cho giống tệp mẫu
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BC',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            # Áp dụng định dạng và độ rộng cột
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25)
                
        return output.getvalue()
    except Exception as e:
        st.error(f"Lỗi kết xuất Excel: {e}")
        return None

# --- 4. GIAO DIỆN ĐĂNG NHẬP ---
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

# --- 5. TẢI DỮ LIỆU ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # Đảm bảo tên đơn vị hiển thị trên bảng luôn viết hoa
    if not df_raw.empty and 'ten_don_vi' in df_raw.columns:
        df_raw['ten_don_vi'] = df_raw['ten_don_vi'].astype(str).str.upper()

    # --- 6. SIDEBAR: THỐNG KÊ ---
    with st.sidebar:
        st.header("📊 DASHBOARD")
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

    # --- 7. MÀN HÌNH CHÍNH ---
    tab_mgt, tab_bi = st.tabs(["📋 QUẢN LÝ NGHIỆP VỤ", "📈 PHÂN TÍCH CHUYÊN SÂU"])

    with tab_mgt:
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            sel_h = st.selectbox("Vùng:", ["Tất cả"] + sorted(df_raw['huyen_cu'].dropna().unique().tolist()))
        with col_s2:
            search_q = st.text_input("🔍 Tìm kiếm thông minh", placeholder="Tên đơn vị, MST, SĐT, Kế toán...")

        # Lọc dữ liệu
        df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu'] == sel_h]
        if search_q:
            q = search_q.lower()
            df_f = df_f[df_f.apply(lambda x: q in str(x.values).lower(), axis=1)]

        # Hiển thị bảng
        st.dataframe(
            df_f[['mst', 'ten_don_vi', 'huyen_cu', 'ke_toan', 'sdt_ke_toan', 'san_pham']],
            use_container_width=True, hide_index=True,
            selection_mode="single-row", key="table_select", on_select="rerun"
        )

        # Cụm nút xuất Excel ngay dưới bảng
        if not df_f.empty:
            c_ex1, c_ex2 = st.columns(2)
            with c_ex1:
                buf_all = io.BytesIO()
                df_f.to_excel(buf_all, index=False)
                st.download_button("📥 Tải danh sách đang lọc (Gốc)", buf_all.getvalue(), "Data_Goc.xlsx", use_container_width=True)
            with c_ex2:
                # GỌI HÀM XUẤT MẪU LICENSE
                special_excel = export_special_excel(df_f)
                if special_excel:
                    st.download_button("📝 XUẤT MẪU CẤP LICENSE (ALL)", special_excel, "Mau_Cap_License.xlsx", type="primary", use_container_width=True)

        # Xử lý khi chọn dòng
        if st.session_state.table_select.selection.rows:
            idx = st.session_state.table_select.selection.rows[0]
            row_data = df_f.iloc[idx]
            
            st.divider()
            st.subheader(f"🛠️ Hiệu chỉnh: {row_data['ten_don_vi']}")
            
            with st.form("edit_form_final"):
                f1, f2, f3 = st.columns(3)
                up = {}
                with f1:
                    up['ten_don_vi'] = st.text_input("Tên đơn vị", value=str(row_data['ten_don_vi']).upper())
                    up['mst'] = st.text_input("MST", row_data['mst'])
                    up['dia_chi'] = st.text_input("Địa chỉ", row_data['dia_chi'])
                with f2:
                    up['huyen_cu'] = st.text_input("Khu vực", row_data['huyen_cu'])
                    up['ma_qhns'] = st.text_input("Mã QHNS", row_data['ma_qhns'])
                    up['so_tkkb'] = st.text_input("Số TK Kho bạc", row_data['so_tkkb'])
                with f3:
                    up['ke_toan'] = st.text_input("Kế toán", row_data['ke_toan'])
                    up['sdt_ke_toan'] = st.text_input("SĐT", row_data['sdt_ke_toan'])
                    up['san_pham'] = st.text_input("Mã máy", row_data['san_pham'])
                
                if st.form_submit_button("💾 LƯU THAY ĐỔI", type="primary", use_container_width=True):
                    up['ten_don_vi'] = up['ten_don_vi'].upper()
                    supabase.table("don_vi").update(up).eq("mst", row_data['mst']).execute()
                    st.success("Cập nhật thành công!")
                    st.rerun()

            # Nút tác vụ riêng cho dòng được chọn
            b1, b2, b3 = st.columns(3)
            with b1:
                sdt = str(row_data['sdt_ke_toan']).strip()
                if sdt and sdt != "nan":
                    st.link_button("💬 ZALO KẾ TOÁN", f"https://zalo.me/{sdt}", use_container_width=True)
            with b2:
                pdf_data = export_pdf(row_data)
                st.download_button("📄 XUẤT PDF", pdf_data, f"HN11_{row_data['mst']}.pdf", use_container_width=True)
            with b3:
                # Xuất mẫu License chỉ cho 1 dòng này
                one_row_excel = export_special_excel(pd.DataFrame([row_data]))
                st.download_button("📊 XUẤT MẪU LICENSE (DÒNG NÀY)", one_row_excel, f"License_{row_data['mst']}.xlsx", use_container_width=True)

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
