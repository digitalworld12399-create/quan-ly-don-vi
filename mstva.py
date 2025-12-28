import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from supabase import create_client, Client
import re
from datetime import datetime
import pandas as pd
import time
import io

# --- 1. KẾT NỐI HỆ THỐNG SUPABASE ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

# --- 2. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Quản lý Đơn vị HN11", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .main-title { 
        color: #0d47a1; 
        font-weight: 800; 
        text-align: center; 
        margin-bottom: 30px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .field-label { font-weight: 600; color: #263238; margin-top: 10px; font-size: 0.95rem; }
    .red-star { color: #e53935; font-weight: bold; margin-left: 2px; }
    .guide-container {
        border-left: 5px solid #1e88e5;
        border-radius: 4px;
        padding: 15px;
        background-color: #e3f2fd;
    }
    .guide-text { font-size: 0.9rem; line-height: 1.6; color: #1565c0; }
    div.stButton > button:first-child { border-radius: 6px; font-weight: 600; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    .support-box {
        background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
        padding: 15px; border-radius: 12px; color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Khởi tạo session state
if 'form' not in st.session_state:
    st.session_state.form = {"mst": "", "ten": "", "dc": "", "rep": "", "qhns": "", "thue": "", "ma_kb": "", "tk_kb": "", "kt": "", "sdt_kt": ""}
if 'history' not in st.session_state: st.session_state.history = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'trigger_reset' not in st.session_state: st.session_state.trigger_reset = False

# --- 3. XỬ LÝ RESET & HÀM BỔ TRỢ ---
def clean_mst(mst_string):
    """Loại bỏ tất cả ký tự lạ, chỉ giữ lại số và dấu gạch ngang '-'"""
    if not mst_string:
        return ""
    return re.sub(r'[^0-9\-]', '', mst_string)

if st.session_state.trigger_reset:
    keep = ["ma_kb", "kt", "sdt_kt"]
    for key in list(st.session_state.form.keys()):
        if key not in keep: st.session_state.form[key] = ""
    if "qhns_input" in st.session_state: st.session_state.qhns_input = ""
    st.session_state.trigger_reset = False

def update_tk_kb():
    if st.session_state.qhns_input:
        st.session_state.form["tk_kb"] = f"9523.4.{st.session_state.qhns_input}"
        st.session_state.form["qhns"] = st.session_state.qhns_input

def add_to_history(name):
    timestamp = datetime.now().strftime("%H:%M")
    entry = f"{timestamp} - {name}"
    if entry not in st.session_state.history:
        st.session_state.history.insert(0, entry)
        st.session_state.history = st.session_state.history[:5]

def fetch_online_data(mst_code):
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
                    if "Địa chỉ" in label: st.session_state.form["dc"] = val
                    if any(x in label for x in ["Người đại diện", "Giám đốc", "Chủ hộ"]):
                        st.session_state.form["rep"] = re.sub(r'\(.*?\)', '', val).strip().upper()
                    if "Quản lý bởi" in label: st.session_state.form["thue"] = val
                return True
        return False
    except: return False

def save_data(payload, is_update=False):
    p_bar = st.progress(0, text="📡 Đang đồng bộ...")
    for i in range(100): time.sleep(0.005); p_bar.progress(i + 1)
    try:
        # Làm sạch MST một lần cuối trước khi lưu vào DB
        payload["mst"] = clean_mst(payload["mst"])
        if is_update: supabase.table("don_vi").update(payload).eq("mst", payload["mst"]).execute()
        else:
            payload["created_at"] = datetime.now().isoformat()
            supabase.table("don_vi").insert(payload).execute()
        add_to_history(payload["ten_don_vi"])
        p_bar.empty(); st.balloons(); st.success("🎉 Cập nhật thành công!")
        st.session_state.trigger_reset = True
        time.sleep(2); st.rerun()
    except Exception as e: p_bar.empty(); st.error(f"Lỗi: {str(e)}")

@st.dialog("Xác nhận thay thế")
def confirm_overwrite_dialog(payload):
    st.warning(f"⚠️ MST **{payload['mst']}** đã tồn tại.")
    c1, c2 = st.columns(2)
    if c1.button("✅ ĐỒNG Ý", type="primary", use_container_width=True): save_data(payload, is_update=True)
    if c2.button("❌ HỦY", use_container_width=True): st.rerun()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #0d47a1;'>🛡️ HỆ THỐNG</h2>", unsafe_allow_html=True)
    menu = st.radio("Menu", ["📝 Cập nhật đơn vị", "🗂️ Danh sách tổng hợp"], label_visibility="collapsed")
    st.divider()
    st.markdown(f"⏳ **Lịch sử gần đây ({len(st.session_state.history)})**")
    if st.button("🧹 Làm mới phiên", use_container_width=True):
        st.session_state.history = []
        st.rerun()
    for item in st.session_state.history:
        st.markdown(f"<p style='font-size: 0.85em; color: #546e7a; margin: 0;'>• {item}</p>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"""<div class="support-box">
            <p style="margin: 0; font-weight: bold; font-size: 0.9rem;">💎 Hỗ trợ kỹ thuật:</p>
            <p style="margin: 5px 0 0 5px; opacity: 0.9;">Nguyễn Văn Ánh HN11</p>
            <p style="margin: 0 0 0 5px; font-weight: bold;">📞 0969.338.332</p>
        </div>""", unsafe_allow_html=True)
    st.markdown("<p style='color: #90a4ae; font-size: 0.8em; margin-top: 15px; text-align: center;'>🔖 Version: 1.0.8</p>", unsafe_allow_html=True)
    if st.session_state.logged_in and st.button("🔒 Đăng xuất", use_container_width=True):
        st.session_state.logged_in = False; st.rerun()

# --- 8. GIAO DIỆN CHÍNH ---
if menu == "📝 Cập nhật đơn vị":
    st.markdown("<h1 class='main-title'>🏦 QUẢN LÝ DỮ LIỆU ĐƠN VỊ</h1>", unsafe_allow_html=True)
    c_guide, _ = st.columns([1, 2])
    with c_guide:
        with st.expander("💡 Hướng dẫn nhanh"):
            st.markdown("""<div class="guide-container"><div class="guide-text">
                1. Nhập MST -> Lấy dữ liệu.<br>2. Kiểm tra Tên & Địa chỉ.<br>3. Xác nhận lại MST.<br>
                4. Nhập 7 số Mã QHNS.<br>5. Nhập Mã KB, Kế toán, SĐT.<br>6. Nhấn Gửi dữ liệu.</div></div>""", unsafe_allow_html=True)

    st.write("")
    col_search, col_btn_fetch = st.columns([3, 2])
    mst_lookup = col_search.text_input("Tra cứu", value=st.session_state.form["mst"], placeholder="Mời bạn nhập Mã số thuế (10 đến 13 số) Để lấy dữ liệu tự động", label_visibility="collapsed")
    
    if col_btn_fetch.button("🔍 LẤY DỮ LIỆU", type="primary", use_container_width=True):
        if mst_lookup:
            # LÀM SẠCH DỮ LIỆU TRƯỚC KHI TRA CỨU
            mst_cleaned = clean_mst(mst_lookup)
            
            fetch_pbar = st.progress(0, text="📡 Đang quét dữ liệu...")
            for i in range(100): time.sleep(0.005); fetch_pbar.progress(i + 1)
            
            st.session_state.form["mst"] = mst_cleaned
            res = supabase.table("don_vi").select("*").eq("mst", mst_cleaned).execute()
            found = False
            if res.data:
                found = True
                d = res.data[0]
                st.session_state.form.update({"ten": d.get("ten_don_vi"), "dc": d.get("dia_chi"), "rep": d.get("chu_tai_khoan"), "qhns": d.get("ma_qhns"), "thue": d.get("co_quan_thue"), "ma_kb": d.get("ma_kbnn"), "tk_kb": d.get("so_tkkb"), "kt": d.get("ke_toan"), "sdt_kt": d.get("sdt_ke_toan")})
                st.session_state.qhns_input = d.get("ma_qhns")
            else: 
                found = fetch_online_data(mst_cleaned)
            
            fetch_pbar.empty()
            if found: 
                st.success(f"✅ Đã tìm thấy thông tin cho MST: {mst_cleaned}")
                time.sleep(1); st.rerun()
            else: 
                st.error("❌ Không tìm thấy thông tin.")

    # Form nhập liệu
    st.markdown("<p class='field-label'>🏢 Tên đơn vị <span class='red-star'>*</span></p>", unsafe_allow_html=True)
    st.session_state.form["ten"] = st.text_input("ten_in", value=st.session_state.form["ten"], label_visibility="collapsed")
    st.markdown("<p class='field-label'>📍 Địa chỉ trụ sở</p>", unsafe_allow_html=True)
    st.session_state.form["dc"] = st.text_input("dc_in", value=st.session_state.form["dc"], label_visibility="collapsed")

    cl, cr = st.columns(2)
    with cl:
        st.markdown("<p class='field-label'>🆔 Mã QHNS <span class='red-star'>*</span></p>", unsafe_allow_html=True)
        st.text_input("qhns_w", max_chars=7, key="qhns_input", on_change=update_tk_kb, label_visibility="collapsed")
        st.markdown("<p class='field-label'>🔢 MST xác nhận <span class='red-star'>*</span></p>", unsafe_allow_html=True)
        # MST trong form cũng tự động được làm sạch
        raw_mst_val = st.text_input("mst_in", value=st.session_state.form["mst"], label_visibility="collapsed")
        st.session_state.form["mst"] = clean_mst(raw_mst_val)
        
        st.markdown("<p class='field-label'>🏪 Mã kho bạc <span class='red-star'>*</span></p>", unsafe_allow_html=True)
        st.session_state.form["ma_kb"] = st.text_input("kb_in", value=st.session_state.form["ma_kb"], label_visibility="collapsed")
        st.markdown("<p class='field-label'>👤 Kế toán viên <span class='red-star'>*</span></p>", unsafe_allow_html=True)
        st.session_state.form["kt"] = st.text_input("kt_in", value=st.session_state.form["kt"], label_visibility="collapsed").upper()
    with cr:
        st.markdown("<p class='field-label'>💳 Số TK kho bạc <span class='red-star'>*</span></p>", unsafe_allow_html=True)
        st.session_state.form["tk_kb"] = st.text_input("tk_in", value=st.session_state.form["tk_kb"], label_visibility="collapsed")
        st.markdown("<p class='field-label'>🏛️ Cơ quan thuế</p>", unsafe_allow_html=True)
        st.session_state.form["thue"] = st.text_input("thue_in", value=st.session_state.form["thue"] or "Đang cập nhật", label_visibility="collapsed")
        st.markdown("<p class='field-label'>👤 Chủ tài khoản <span class='red-star'>*</span></p>", unsafe_allow_html=True)
        st.session_state.form["rep"] = st.text_input("rep_in", value=st.session_state.form["rep"], label_visibility="collapsed")
        st.markdown("<p class='field-label'>📞 Số điện thoại <span class='red-star'>*</span></p>", unsafe_allow_html=True)
        st.session_state.form["sdt_kt"] = st.text_input("sdt_in", value=st.session_state.form["sdt_kt"], label_visibility="collapsed")

    st.write("---")
    if st.button("📤 CẬP NHẬT DỮ LIỆU LÊN HỆ THỐNG", type="primary", use_container_width=True):
        final_mst = clean_mst(st.session_state.form["mst"])
        payload = {"mst": final_mst, "ten_don_vi": st.session_state.form["ten"], "dia_chi": st.session_state.form["dc"] or "Đang cập nhật", "ma_qhns": st.session_state.form["qhns"], "chu_tai_khoan": st.session_state.form["rep"], "ma_kbnn": st.session_state.form["ma_kb"], "so_tkkb": st.session_state.form["tk_kb"], "ke_toan": st.session_state.form["kt"], "sdt_ke_toan": st.session_state.form["sdt_kt"], "co_quan_thue": st.session_state.form["thue"], "last_update": datetime.now().isoformat()}
        if not all([payload["mst"], payload["ten_don_vi"], payload["ma_qhns"]]): st.error("❌ Thiếu thông tin bắt buộc (*)")
        else:
            check = supabase.table("don_vi").select("mst").eq("mst", payload["mst"]).execute()
            if check.data: confirm_overwrite_dialog(payload)
            else: save_data(payload)

elif menu == "🗂️ Danh sách tổng hợp":
    if not st.session_state.logged_in:
        with st.columns([1,2,1])[1]:
            with st.form("auth"):
                st.markdown("🔐 **Xác thực quyền quản trị**")
                u, p = st.text_input("Tài khoản"), st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("ĐĂNG NHẬP"):
                    if u == "kh" and p == "a11": st.session_state.logged_in = True; st.rerun()
                    else: st.error("Thông tin không chính xác")
    else:
        st.markdown("<h3 style='text-align: center; color: #0d47a1;'>📊 DANH SÁCH ĐƠN VỊ ĐÃ CẬP NHẬT</h3>", unsafe_allow_html=True)
        res = supabase.table("don_vi").select("*").order("last_update", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False, sheet_name='Data')
            st.download_button(label="📥 Tải tệp Excel (.xlsx)", data=output.getvalue(), file_name="Data_DVC.xlsx")
            st.dataframe(df, use_container_width=True, hide_index=True)
