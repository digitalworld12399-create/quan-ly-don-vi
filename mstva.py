import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from supabase import create_client, Client
import re
from datetime import datetime
import pandas as pd
import io
import time

# --- 1. KẾT NỐI HỆ THỐNG SUPABASE ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

# Khởi tạo session state
if 'form' not in st.session_state:
    st.session_state.form = {
        "mst": "", "ten": "", "dc": "", "rep": "", 
        "qhns": "", "thue": "", "ma_kb": "", "tk_kb": "",
        "kt": "",      
        "sdt_kt": ""   
    }
if 'session_history' not in st.session_state:
    st.session_state.session_history = []
if 'confirm_overwrite' not in st.session_state:
    st.session_state.confirm_overwrite = False
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- HÀM TRỢ GIÚP ---
def validate_mst(mst):
    """Kiểm tra MST hợp lệ theo quy chuẩn 10 hoặc 13 số."""
    mst = str(mst).strip()
    if not mst.isdigit():
        return False, "⚠️ Mã số thuế chỉ được chứa các chữ số."
    if len(mst) not in [10, 13]:
        return False, f"⚠️ Mã số thuế phải có 10 hoặc 13 chữ số (Hiện tại: {len(mst)})."
    return True, ""

def update_tk_kb():
    """Tự động cập nhật số tài khoản khi nhập mã QHNS."""
    qhns_val = st.session_state.qhns_input
    if qhns_val:
        st.session_state.form["tk_kb"] = f"9523.4.{qhns_val}"
        st.session_state.form["qhns"] = qhns_val

def add_to_history(mst, ten):
    st.session_state.session_history = [item for item in st.session_state.session_history if item['mst'] != mst]
    st.session_state.session_history.insert(0, {"mst": mst, "ten": ten})

def load_from_history(mst):
    res = supabase.table("don_vi").select("*").eq("mst", mst).execute()
    if res.data:
        data = res.data[0]
        st.session_state.form.update({
            "mst": data.get("mst", ""),
            "ten": data.get("ten_don_vi", ""),
            "dc": data.get("dia_chi", ""),
            "rep": data.get("chu_tai_khoan", ""),
            "qhns": data.get("ma_qhns", ""),
            "thue": data.get("co_quan_thue", ""),
            "ma_kb": data.get("ma_kbnn", ""),
            "tk_kb": data.get("so_tkkb", ""),
            "kt": data.get("ke_toan", ""),
            "sdt_kt": data.get("sdt_ke_toan", "")
        })

def fetch_data(mst_code):
    try:
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        url = f"https://masothue.com/Search/?q={mst_code}&type=auto"
        res = scraper.get(url, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "html.parser")
            name_tag = soup.find("th", {"itemprop": "name"})
            if name_tag: 
                st.session_state.form["ten"] = name_tag.get_text().strip().upper()
            for row in soup.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) < 2: continue
                label, val = cols[0].get_text().strip(), " ".join(cols[-1].get_text().split()).strip()
                if "Địa chỉ" in label or "Trụ sở" in label: st.session_state.form["dc"] = val
                if any(x in label for x in ["Người đại diện", "Giám đốc", "Chủ hộ"]):
                    st.session_state.form["rep"] = re.sub(r'\(.*?\)', '', val).strip().upper()
                if "Quản lý bởi" in label: st.session_state.form["thue"] = val
            return True
    except: return False

# --- 2. SIDEBAR (THANH ĐIỀU HƯỚNG) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>⚙️ QUẢN TRỊ</h1>", unsafe_allow_html=True)
    menu = st.radio("Menu chính:", ["🏠 Cập nhật đơn vị", "📋 Toàn bộ danh sách"], label_visibility="collapsed")
    st.divider()
    st.subheader(f"🕒 Lịch sử ({len(st.session_state.session_history)})")
    if st.button("🗑️ Làm mới phiên làm việc", use_container_width=True):
        st.session_state.session_history = []
        st.session_state.form = {k: "" for k in st.session_state.form}
        st.rerun()
    for item in st.session_state.session_history:
        if st.button(f"📌 {item['mst']}\n{item['ten'][:25]}", key=f"btn_{item['mst']}", use_container_width=True):
            load_from_history(item['mst'])
            st.rerun()
    st.divider()
    st.info("📞 **Hỗ trợ kỹ thuật:**\n\nNguyễn Văn Ánh HN11\n\nĐT: **0969.338.332**", icon="👨‍💻")
    st.caption("📌 Version: 1.0.6")

# --- 3. TRANG 1: CẬP NHẬT ĐƠN VỊ ---
if menu == "🏠 Cập nhật đơn vị":
    st.markdown("<h2 style='text-align: center; color: #1E88E5;'>🏛️ CẬP NHẬT THÔNG TIN ĐƠN VỊ</h2>", unsafe_allow_html=True)
    
    # TÍCH HỢP HƯỚNG DẪN 12 BƯỚC (POPOVER)
    with st.popover("📖 Hướng dẫn sử dụng nhanh (12 bước)"):
        st.markdown("""
        1. **Nhập MST** vào ô tra cứu bên dưới.
        2. Nhấn **LẤY DỮ LIỆU** để hệ thống tự điền Tên & Địa chỉ.
        3. Kiểm tra **Tên đơn vị**.
        4. Kiểm tra **Địa chỉ**.
        5. Xác nhận lại **MST**.
        6. Nhập 7 số **Mã QHNS**.
        7. Hệ thống tự tạo **Số TK Kho bạc** (9523.4...).
        8. Nhập **Mã Kho bạc** (ví dụ: 2471).
        9. Nhập tên **Chủ tài khoản**.
        10. Nhập tên **Kế toán**.
        11. Nhập **SĐT** liên hệ.
        12. Nhấn **GỬI DỮ LIỆU** để lưu vào hệ thống.
        """)

    # Khu vực Tra cứu
    with st.container(border=True):
        c_search, c_btn = st.columns([4, 1])
        with c_search:
            mst_input = st.text_input("Tra cứu MST", value=st.session_state.form["mst"], label_visibility="collapsed", placeholder="Nhập MST (10 hoặc 13 số) để lấy dữ liệu tự động...")
        with c_btn:
            if st.button("⚡ TRA CỨU", type="primary", use_container_width=True):
                if mst_input:
                    is_valid, msg = validate_mst(mst_input)
                    if is_valid:
                        st.session_state.form["mst"] = mst_input
                        if fetch_data(mst_input):
                            add_to_history(mst_input, st.session_state.form["ten"])
                            st.rerun()
                    else: st.error(msg)

    st.markdown("<p style='color:red; font-weight:bold; font-size:13px;'>* Các trường bắt buộc nhập</p>", unsafe_allow_html=True)
    
    # Khu vực Nhập liệu chi tiết
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("🏢 **Tên đơn vị <span style='color:red;'>*</span>**", unsafe_allow_html=True)
            st.session_state.form["ten"] = st.text_input("ten", value=st.session_state.form["ten"], label_visibility="collapsed", help="Tên chính thức của đơn vị trên giấy phép")
            
            st.markdown("📍 **Địa chỉ**", unsafe_allow_html=True)
            st.session_state.form["dc"] = st.text_area("dc", value=st.session_state.form["dc"], label_visibility="collapsed", height=68)
            
            st.markdown("🔢 **Mã số thuế xác nhận <span style='color:red;'>*</span>**", unsafe_allow_html=True)
            st.session_state.form["mst"] = st.text_input("mstxn", value=st.session_state.form["mst"], label_visibility="collapsed", help="Phải khớp với MST đã tra cứu")
            
            st.markdown("🏦 **Cơ quan thuế**", unsafe_allow_html=True)
            st.session_state.form["thue"] = st.text_input("cqt", value=st.session_state.form["thue"], label_visibility="collapsed")
            
        with col2:
            st.markdown("🆔 **Mã QHNS <span style='color:red;'>*</span>**", unsafe_allow_html=True)
            st.session_state.form["qhns"] = st.text_input("qhns", value=st.session_state.form["qhns"], max_chars=7, key="qhns_input", on_change=update_tk_kb, label_visibility="collapsed", help="Mã quan hệ ngân sách gồm 7 chữ số")
            
            st.markdown("💳 **Tài khoản kho bạc <span style='color:red;'>*</span>**", unsafe_allow_html=True)
            st.session_state.form["tk_kb"] = st.text_input("tkkb", value=st.session_state.form["tk_kb"], label_visibility="collapsed", help="Hệ thống tự tạo từ mã QHNS")
            
            st.markdown("🏗️ **Mã kho bạc <span style='color:red;'>*</span>**", unsafe_allow_html=True)
            st.session_state.form["ma_kb"] = st.text_input("makb", value=st.session_state.form["ma_kb"], label_visibility="collapsed", help="Mã định danh của kho bạc địa phương")
            
            st.markdown("👤 **Chủ tài khoản <span style='color:red;'>*</span>**", unsafe_allow_html=True)
            st.session_state.form["rep"] = st.text_input("ctk", value=st.session_state.form["rep"], label_visibility="collapsed", help="Họ tên người đại diện pháp luật")
            
            c_kt_col1, c_kt_col2 = st.columns(2)
            with c_kt_col1:
                st.markdown("👨‍💼 **Kế toán <span style='color:red;'>*</span>**", unsafe_allow_html=True)
                kt_val = st.text_input("kt", value=st.session_state.form["kt"], label_visibility="collapsed")
                st.session_state.form["kt"] = kt_val.upper()
            with c_kt_col2:
                st.markdown("📞 **SĐT <span style='color:red;'>*</span>**", unsafe_allow_html=True)
                st.session_state.form["sdt_kt"] = st.text_input("sdt", value=st.session_state.form["sdt_kt"], label_visibility="collapsed")

    # Xử lý Gửi dữ liệu
    payload = {
        "mst": st.session_state.form["mst"], "ten_don_vi": st.session_state.form["ten"],
        "dia_chi": st.session_state.form["dc"], "chu_tai_khoan": st.session_state.form["rep"],
        "ma_qhns": st.session_state.form["qhns"], "co_quan_thue": st.session_state.form["thue"],
        "ma_kbnn": st.session_state.form["ma_kb"], "so_tkkb": st.session_state.form["tk_kb"],
        "ke_toan": st.session_state.form["kt"], "sdt_ke_toan": st.session_state.form["sdt_kt"],
        "last_update": datetime.now().isoformat()
    }

    st.write("")
    if st.button("💾 GỬI DỮ LIỆU LÊN HỆ THỐNG", type="primary", use_container_width=True):
        required_fields = {
            "Mã số thuế": payload["mst"], "Tên đơn vị": payload["ten_don_vi"],
            "Mã QHNS": payload["ma_qhns"], "Tài khoản kho bạc": payload["so_tkkb"],
            "Mã kho bạc": payload["ma_kbnn"], "Chủ tài khoản": payload["chu_tai_khoan"],
            "Kế toán": payload["ke_toan"], "Số điện thoại": payload["sdt_ke_toan"]
        }
        empty_fields = [k for k, v in required_fields.items() if not v or str(v).strip() == ""]
        if empty_fields:
            st.error(f"❌ Vui lòng nhập đầy đủ: {', '.join(empty_fields)}")
        else:
            is_valid_mst, msg_mst = validate_mst(payload["mst"])
            if not is_valid_mst:
                st.error(msg_mst)
            else:
                res = supabase.table("don_vi").select("mst").eq("mst", payload["mst"]).execute()
                if len(res.data) > 0:
                    st.session_state.confirm_overwrite = True
                else:
                    payload["created_at"] = payload["last_update"]
                    supabase.table("don_vi").insert(payload).execute()
                    add_to_history(payload["mst"], payload["ten_don_vi"])
                    st.success("✅ Đã gửi dữ liệu thành công!")
                    st.balloons()

    if st.session_state.confirm_overwrite:
        st.warning(f"⚠️ MST {st.session_state.form['mst']} đã tồn tại. Bạn muốn ghi đè dữ liệu mới?")
        cy, cn = st.columns(2)
        if cy.button("✅ ĐỒNG Ý GHI ĐÈ", use_container_width=True):
            supabase.table("don_vi").update(payload).eq("mst", payload["mst"]).execute()
            add_to_history(payload["mst"], payload["ten_don_vi"])
            st.session_state.confirm_overwrite = False
            st.success("🎉 Đã cập nhật thành công!")
            st.balloons()
            time.sleep(1)
            st.rerun()
        if cn.button("❌ HỦY BỎ", use_container_width=True):
            st.session_state.confirm_overwrite = False
            st.rerun()

# --- 4. TRANG 2: DANH SÁCH TỔNG ---
elif menu == "📋 Toàn bộ danh sách":
    st.markdown("<h2 style='text-align: center; color: #2E7D32;'>📋 DANH SÁCH DỮ LIỆU TỔNG</h2>", unsafe_allow_html=True)
    if not st.session_state.logged_in:
        with st.columns([1,2,1])[1]:
            with st.form("auth"):
                st.markdown("<h4 style='text-align: center;'>🔐 Đăng nhập Quản trị</h4>", unsafe_allow_html=True)
                u = st.text_input("Tài khoản")
                p = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("XÁC NHẬN", use_container_width=True):
                    if u == "kh" and p == "a11":
                        st.session_state.logged_in = True
                        st.rerun()
                    else: st.error("Sai tài khoản hoặc mật khẩu!")
    else:
        st.sidebar.button("🔓 Đăng xuất", on_click=lambda: st.session_state.update({"logged_in": False}))
        res = supabase.table("don_vi").select("*").order("last_update", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            cols_map = {"mst": "MST", "ten_don_vi": "Tên Đơn Vị", "ma_qhns": "Mã QHNS", "so_tkkb": "Số TK", "ma_kbnn": "Mã KB", "ke_toan": "Kế Toán", "sdt_ke_toan": "SĐT"}
            st.dataframe(df[list(cols_map.keys())].rename(columns=cols_map), use_container_width=True)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 TẢI FILE EXCEL (.XLSX)", output.getvalue(), f"DSDV_{datetime.now().strftime('%d%m%Y')}.xlsx", use_container_width=True)
