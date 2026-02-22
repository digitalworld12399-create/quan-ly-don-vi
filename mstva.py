import streamlit as st
import requests
from supabase import create_client, Client
import re
from datetime import datetime
import time

# --- 1. KẾT NỐI HỆ THỐNG (Lấy từ Secrets) ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
    X_CLIENT_ID = st.secrets.get("X_CLIENT_ID", "YOUR_ID")
    X_API_KEY = st.secrets.get("X_API_KEY", "YOUR_KEY")
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Lỗi cấu hình Secrets. Vui lòng kiểm tra lại tab Secrets trên Streamlit Cloud.")
    st.stop()

# --- 2. HÀM HỖ TRỢ ---
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        payload = {"chat_id": TELE_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except: pass

def speak_male(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={text.replace(' ', '%20')}&tl=vi&client=tw-ob"
    st.components.v1.html(f"<script>new Audio('{tts_url}').play();</script>", height=0)

# Khởi tạo trạng thái
if 'form' not in st.session_state:
    st.session_state.form = {
        "mst": "", "ten": "", "dc": "", "rep": "", "qhns": "", "thue": "", 
        "ma_kb": "", "tk_kb": "", "kt": "", "sdt_kt": "", "chuc_vu": "", 
        "san_pham": "Kế toán hành chính"
    }
if 'show_confirm' not in st.session_state: st.session_state.show_confirm = False
if 'search_status' not in st.session_state: st.session_state.search_status = None
if 'session_history' not in st.session_state: st.session_state.session_history = []

# --- 3. HÀM LƯU DỮ LIỆU ---
def final_save(mode="NEW"):
    f = st.session_state.form
    now_obj = datetime.now()
    now_str = now_obj.strftime("%H:%M:%S %d/%m/%Y")
    
    payload = {
        "mst": f["mst"], "ten_don_vi": f["ten"], "dia_chi": f["dc"], "ma_qhns": f["qhns"],
        "so_tkkb": f["tk_kb"], "ma_kbnn": f["ma_kb"], "co_quan_thue": f["thue"],
        "chu_tai_khoan": f["rep"], "chuc_vu": f["chuc_vu"], "ke_toan": f["kt"],
        "sdt_ke_toan": f["sdt_kt"], "san_pham": f["san_pham"], "last_update": now_obj.isoformat()
    }
    
    try:
        supabase.table("don_vi").upsert(payload, on_conflict="mst").execute()
        st.session_state.session_history.insert(0, f"🕒 {now_str} | {mode}: {f['ten']}")
        
        prefix = "⚠️ *GHI ĐÈ DỮ LIỆU*" if mode == "OVERWRITE" else "🆕 *THÊM MỚI ĐƠN VỊ*"
        msg = f"{prefix}\n🏢 {f['ten']}\n🆔 MST: {f['mst']}\n👨‍💼 {f['kt']} ({f['sdt_kt']})"
        send_telegram(msg)
        
        st.session_state.show_confirm = False
        st.balloons()
        speak_male("Cập nhật dữ liệu thành công")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Lỗi lưu dữ liệu: {e}")

# --- 4. GIAO DIỆN ---
st.set_page_config(page_title="HN11 - Quản lý đơn vị", layout="wide")
st.markdown("<style>.field-label { font-weight: bold; color: #004a99; margin-bottom: 2px; font-size: 14px; } .red-star { color: #ff0000; font-weight: bold; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"""
    <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid #1E90FF;">
        <h3 style="margin-top:0;">🛡️ HN11 SYSTEM</h3>
        <p style="margin-bottom:5px;">👤 <b>Phát triển:</b> Nguyễn Văn Ánh</p>
        <p style="margin-bottom:5px;">📞 <b>ĐT:</b> 0969.338.332</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    st.subheader("📜 Nhật ký phiên")
    for item in st.session_state.session_history[:5]: st.caption(item)
    st.divider()
    # Nút dẫn sang trang Admin
    st.link_button("🚀 ĐĂNG NHẬP QUẢN TRỊ", "https://quan-ly-don-vi-mzbftixs3wct4ammhpdmvq.streamlit.app/", use_container_width=True)

if st.session_state.show_confirm:
    st.warning(f"### ⚠️ XÁC NHẬN GHI ĐÈ\nMST {st.session_state.form['mst']} đã tồn tại.")
    c1, c2 = st.columns(2)
    if c1.button("✅ ĐỒNG Ý", type="primary"): final_save(mode="OVERWRITE")
    if c2.button("❌ HỦY"): st.session_state.show_confirm = False; st.rerun()
    st.stop()

st.markdown('<h1 style="text-align:center; color:#1E90FF;">🏦 CẬP NHẬT ĐƠN VỊ HN11</h1>', unsafe_allow_html=True)

# --- 5. TRA CỨU ---
c_search, c_btn = st.columns([ 2, 1 ])
txt_mst = c_search.text_input("Search", placeholder="Nhập mã số thuế...", label_visibility="collapsed")

if c_btn.button("🔍 TRA CỨU", type="primary", use_container_width=True):
    v_mst = re.sub(r'[^0-9]', '', txt_mst)
    if v_mst:
        res = supabase.table("don_vi").select("*").eq("mst", v_mst).execute()
        if res.data:
            d = res.data[0]
            st.session_state.form.update({
                "mst": v_mst, "ten": d.get("ten_don_vi"), "dc": d.get("dia_chi"),
                "qhns": d.get("ma_qhns"), "tk_kb": d.get("so_tkkb"), "ma_kb": d.get("ma_kbnn"),
                "thue": d.get("co_quan_thue"), "rep": d.get("chu_tai_khoan"), "chuc_vu": d.get("chuc_vu"),
                "kt": d.get("ke_toan"), "sdt_kt": d.get("sdt_ke_toan"), "san_pham": d.get("san_pham")
            })
            st.success("✅ Tìm thấy dữ liệu cũ.")
        else:
            speak_male("Không tìm thấy thông tin, vui lòng nhập tay")
        st.rerun()

st.divider()

# --- 6. FORM ---
f = st.session_state.form
col1, col2, col3 = st.columns(3)
with col1:
    f["ten"] = st.text_input("Tên đơn vị *", value=f["ten"])
    f["mst"] = st.text_input("Mã số thuế *", value=f["mst"])
    f["dc"] = st.text_input("Địa chỉ *", value=f["dc"])
with col2:
    f["qhns"] = st.text_input("Mã QHNS *", value=f["qhns"])
    f["tk_kb"] = st.text_input("Số TK kho bạc *", value=f["tk_kb"])
    f["ma_kb"] = st.text_input("Mã Kho bạc *", value=f["ma_kb"])
with col3:
    f["rep"] = st.text_input("Chủ tài khoản *", value=f["rep"])
    f["chuc_vu"] = st.text_input("Chức danh *", value=f["chuc_vu"])
    f["kt"] = st.text_input("Kế toán *", value=f["kt"])
    f["sdt_kt"] = st.text_input("SĐT kế toán *", value=f["sdt_kt"])

if st.button("📤 XÁC NHẬN CẬP NHẬT DỮ LIỆU", type="primary", use_container_width=True):
    if not all([f["ten"], f["mst"], f["qhns"], f["kt"]]):
        st.error("Vui lòng điền đủ thông tin có dấu *")
    else:
        check = supabase.table("don_vi").select("mst").eq("mst", f["mst"]).execute()
        if check.data:
            st.session_state.show_confirm = True
            st.rerun()
        else: final_save(mode="NEW")
