import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import os
import qrcode
from fpdf import FPDF
import plotly.express as px
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin Ultimate", layout="wide")

# --- 2. HÀM TẠO MÃ QR ---
def generate_qr(data):
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        return img_buffer
    except:
        return None

# --- 3. HÀM XUẤT PDF (SỬA LỖI CODEC & UNICODE) ---
def export_pdf(row):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Xử lý Font
        font_path = "arial.ttf"
        font_name = 'Helvetica'
        if os.path.exists(font_path):
            try:
                pdf.add_font('ArialVN', '', font_path, unicode=True)
                font_name = 'ArialVN'
            except: pass

        # Chèn Mã QR
        qr_content = f"MST: {row.get('mst')}\nDV: {row.get('ten_don_vi')}\nSĐT: {row.get('sdt_ke_toan')}"
        qr_img = generate_qr(qr_content)
        if qr_img:
            temp_name = f"qr_{row.get('mst')}.png"
            with open(temp_name, "wb") as f:
                f.write(qr_img.getvalue())
            pdf.image(temp_name, x=165, y=10, w=30)
            if os.path.exists(temp_name): os.remove(temp_name)

        # Tiêu đề
        pdf.set_font(font_name, size=16)
        pdf.cell(0, 15, txt="PHIẾU THÔNG TIN ĐƠN VỊ", ln=True, align='C')
        
        # Nội dung
        pdf.set_font(font_name, size=11)
        pdf.ln(10)
        fields = {
            "Tên đơn vị": str(row.get('ten_don_vi', '')).upper(),
            "Mã số thuế": "mst", "Địa chỉ": "dia_chi", "Khu vực": "huyen_cu",
            "Mã QHNS": "ma_qhns", "Số TK Kho bạc": "so_tkkb", "Mã Kho bạc": "ma_kbnn",
            "Chủ tài khoản": "chu_tai_khoan", "Kế toán trưởng": "ke_toan", "Số điện thoại": "sdt_ke_toan"
        }
        for label, key in fields.items():
            val = str(row.get(key, key)) if key in row else str(key)
            pdf.multi_cell(0, 8, txt=f"{label}: {val}")
            pdf.ln(1)

        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Lỗi tạo PDF: {e}")
        return b""

# --- 4. HÀM XUẤT EXCEL LICENSE ---
def export_special_excel(df):
    try:
        export_df = pd.DataFrame()
        export_df['STT'] = range(1, len(df) + 1)
        export_df['ĐỊA DANH'] = df['huyen_cu'].fillna("Chưa rõ")
        export_df['TÊN KHÁCH HÀNG'] = df['ten_don_vi'].str.upper()
        export_df['MÃ QUAN HỆ NGÂN SÁCH'] = df['ma_qhns']
        export_df['MÃ KHÁCH HÀNG (SỐ SERIAL)'] = df['san_pham']
        export_df['NGÀY'] = datetime.now().strftime("%d/%m/%Y")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='License')
        return output.getvalue()
    except: return None

# --- 5. AUTHENTICATION ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        st.subheader("🛡️ Admin Login")
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.button("Đăng nhập", use_container_width=True):
            if u == "kh" and p == "a11":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 6. MAIN APP ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df_raw = pd.DataFrame(res.data)

    # --- SỬA LỖI SO SÁNH (FIX: str vs float) ---
    # Chuyển cột huyen_cu về string và thay thế NaN bằng chuỗi trống để sort không lỗi
    df_raw['huyen_cu_clean'] = df_raw['huyen_cu'].fillna("").astype(str)
    list_huyen = sorted([h for h in df_raw['huyen_cu_clean'].unique() if h.strip() != ""])

    # SIDEBAR
    with st.sidebar:
        st.header("📊 DASHBOARD")
        st.metric("Tổng đơn vị", len(df_raw))
        
        st.write("---")
        st.subheader("🔗 TIỆN ÍCH")
        st.link_button("🌐 Tra cứu MST", "https://tracuunnt.gdt.gov.vn/", use_container_width=True)
        # Nút Kiểm tra cập nhật dẫn link về thư mục lưu trữ phiên bản mới
        st.link_button("🔄 Kiểm tra cập nhật", "https://your-update-link.com", use_container_width=True)
        
        st.write("---")
        with st.expander("📈 PHÂN TÍCH CHUYÊN SÂU", expanded=False):
            valid_stats = df_raw.notna().sum().drop(['id'], errors='ignore')
            fig = px.bar(x=valid_stats.values, y=valid_stats.index, orientation='h')
            fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # CENTER UI
    st.subheader("📋 QUẢN LÝ ĐƠN VỊ")
    sel_h = st.selectbox("Vùng:", ["Tất cả"] + list_huyen)
    search = st.text_input("🔍 Tìm nhanh", placeholder="MST, Tên...")

    df_f = df_raw if sel_h == "Tất cả" else df_raw[df_raw['huyen_cu_clean'] == sel_h]
    if search:
        df_f = df_f[df_f.apply(lambda x: search.lower() in str(x.values).lower(), axis=1)]

    st.dataframe(df_f[['mst', 'ten_don_vi', 'huyen_cu', 'sdt_ke_toan']], 
                 use_container_width=True, hide_index=True, 
                 selection_mode="single-row", key="table_select", on_select="rerun")

    if st.session_state.table_select.selection.rows:
        row = df_f.iloc[st.session_state.table_select.selection.rows[0]]
        st.divider()
        
        # FORM SỬA
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            up = {}
            with c1:
                up['ten_don_vi'] = st.text_input("Tên", value=row['ten_don_vi'])
                up['mst'] = st.text_input("MST", value=row['mst'])
            with c2:
                up['sdt_ke_toan'] = st.text_input("SĐT", value=row['sdt_ke_toan'])
                up['huyen_cu'] = st.text_input("Khu vực", value=row['huyen_cu'])
            
            if st.form_submit_button("Lưu thay đổi"):
                supabase.table("don_vi").update(up).eq("mst", row['mst']).execute()
                st.success("Đã lưu!")
                st.rerun()

        # NÚT XUẤT FILE
        b1, b2 = st.columns(2)
        with b1:
            pdf_data = export_pdf(row)
            if pdf_data:
                st.download_button("📄 Tải PDF (QR)", pdf_data, f"{row['mst']}.pdf", use_container_width=True)
        with b2:
            sdt = str(row['sdt_ke_toan'])
            if sdt != 'nan' and sdt.strip() != "":
                st.link_button("💬 Zalo", f"https://zalo.me/{sdt}", use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
