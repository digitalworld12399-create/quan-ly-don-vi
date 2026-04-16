import streamlit as st
import requests
from supabase import create_client, Client
import re
from datetime import datetime
import time

# --- 1. KẾT NỐI HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

X_CLIENT_ID = "YOUR_CLIENT_ID" 
X_API_KEY = "YOUR_API_KEY"

TELE_TOKEN = "8208357912:AAHm-dNSkmCl4HgxpgnSCjoH6uGdjjZvsMA"
TELE_CHAT_ID = "7446579212" 

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
        # Lưu bảng chính
        supabase.table("don_vi").upsert(payload, on_conflict="mst").execute()
        
        # Lưu lịch sử (Bảng đã được bạn tạo thành công)
        log_data = {
            "mst": f["mst"], 
            "ten_don_vi": f["ten"], 
            "hanh_dong": "GHI ĐÈ" if mode == "OVERWRITE" else "THÊM MỚI",
            "thoi_gian": now_obj.isoformat()
        }
        supabase.table("lich_su_cap_nhat").insert(log_data).execute()
        
        # Cập nhật danh sách hiển thị tại Sidebar
        st.session_state.session_history.insert(0, f"🕒 {now_str} | {mode}: {f['ten']}")
        
        # Telegram
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
        <p style="margin-bottom:0;">🔖 <b>Phiên bản:</b> 2.0.1</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📜 Nhật ký phiên làm việc")
    if st.session_state.session_history:
        for item in st.session_state.session_history[:8]:
            st.caption(item)
    else:
        st.write("Chưa có dữ liệu mới.")
    
    st.divider()
    st.link_button("🚀 ĐĂNG NHẬP QUẢN TRỊ", "https://quan-ly-don-vi-mzbftixs3wct4ammhpdmvq.streamlit.app/", use_container_width=True)

if st.session_state.show_confirm:
    st.warning(f"### ⚠️ XÁC NHẬN GHI ĐÈ\nMST {st.session_state.form['mst']} đã tồn tại. Bạn muốn cập nhật?")
    c1, c2 = st.columns(2)
    if c1.button("✅ ĐỒNG Ý", type="primary"): final_save(mode="OVERWRITE")
    if c2.button("❌ HỦY"): st.session_state.show_confirm = False; st.rerun()
    st.stop()

st.markdown('<h1 style="text-align:center; color:#1E90FF;">🏦 HỆ THỐNG CẬP NHẬT ĐƠN VỊ HN11</h1>', unsafe_allow_html=True)

# --- 5. TRA CỨU ---
c_search, c_btn = st.columns([ 1.8, 1.2 ])
with c_search:
    txt_mst = st.text_input("Search", placeholder="Nhập mã số thuế để tra cứu...", label_visibility="collapsed")

if st.session_state.search_status == "not_found":
    st.error("❌ Không tìm thấy thông tin. Vui lòng kiểm tra lại hoặc nhập tay.")
elif st.session_state.search_status == "found":
    st.success("✅ Đã tìm thấy dữ liệu đơn vị.")

with c_btn:
    if st.button("🔍 TRA CỨU", type="primary", use_container_width=True):
        v_mst = re.sub(r'[^0-9]', '', txt_mst)
        if v_mst:
            st.session_state.form.update({"ten": "", "rep": "", "qhns": "", "tk_kb": ""})
            res = supabase.table("don_vi").select("*").eq("mst", v_mst).execute()
            if res.data:
                d = res.data[0]
                st.session_state.form.update({
                    "mst": v_mst, "ten": d.get("ten_don_vi"), "dc": d.get("dia_chi"),
                    "qhns": d.get("ma_qhns"), "tk_kb": d.get("so_tkkb"), "ma_kb": d.get("ma_kbnn"),
                    "thue": d.get("co_quan_thue"), "rep": d.get("chu_tai_khoan"), "chuc_vu": d.get("chuc_vu"),
                    "kt": d.get("ke_toan"), "sdt_kt": d.get("sdt_ke_toan"), "san_pham": d.get("san_pham")
                })
                st.session_state.search_status = "found"
            else:
                try:
                    r = requests.get(f"https://api.xinvoice.vn/gdt-api/tax-payer/{v_mst}", headers={'client-id': X_CLIENT_ID, 'api-key': X_API_KEY}, timeout=10)
                    info = r.json().get("data", r.json())
                    if info and info.get("name"):
                        st.session_state.form.update({"mst": v_mst, "ten": str(info.get("name", "")).upper(), "dc": info.get("address", "")})
                        st.session_state.search_status = "found"
                    else: st.session_state.search_status = "not_found"
                except: st.session_state.search_status = "not_found"
            if st.session_state.search_status == "not_found": speak_male("Không tìm thấy thông tin mã số thuế, vui lòng nhập tay")
            st.rerun()

st.divider()

# --- 6. FORM NHẬP LIỆU ---
f = st.session_state.form
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<p class="field-label">🏢 Tên đơn vị <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["ten"] = st.text_input("f1", value=f["ten"], label_visibility="collapsed")
    st.markdown('<p class="field-label">🆔 Mã số thuế <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["mst"] = st.text_input("f2", value=f["mst"], label_visibility="collapsed")
    st.markdown('<p class="field-label">📍 Địa chỉ <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["dc"] = st.text_input("f3", value=f["dc"], label_visibility="collapsed")
    st.markdown('<p class="field-label">💻 Huyện cũ</p>', unsafe_allow_html=True)
    list_sp = ["Kế toán hành chính", "QLTS", "Tổng hợp kế toán", "Quản lý thu chi", "Sản phẩm khác"]
    f["san_pham"] = st.selectbox("f4", list_sp, index=list_sp.index(f["san_pham"]) if f["san_pham"] in list_sp else 0, label_visibility="collapsed")

with col2:
    st.markdown('<p class="field-label">🏦 Mã QHNS <span class="red-star">*</span></p>', unsafe_allow_html=True)
    qhns_val = st.text_input("f5", value=f["qhns"], label_visibility="collapsed")
    if qhns_val != f["qhns"]:
        f["qhns"] = qhns_val
        if len(qhns_val) == 7: f["tk_kb"] = f"9523.4.{qhns_val}"
        st.rerun()

    st.markdown('<p class="field-label">💰 Số TK kho bạc <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["tk_kb"] = st.text_input("f6", value=f["tk_kb"], label_visibility="collapsed")
    st.markdown('<p class="field-label">🏛️ Mã Kho bạc <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["ma_kb"] = st.text_input("f7", value=f["ma_kb"], label_visibility="collapsed")
    st.markdown('<p class="field-label">🧾 Mã số máy (DTSoft điền)</p>', unsafe_allow_html=True)
    f["thue"] = st.text_input("f8", value=f["thue"], label_visibility="collapsed")

with col3:
    st.markdown('<p class="field-label">👤 Chủ tài khoản <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["rep"] = st.text_input("f9", value=f["rep"], label_visibility="collapsed")
    st.markdown('<p class="field-label">🎖️ Chức danh <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["chuc_vu"] = st.text_input("f10", value=f["chuc_vu"], label_visibility="collapsed")
    st.markdown('<p class="field-label">👨‍💼 Kế toán <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["kt"] = st.text_input("f11", value=f["kt"], label_visibility="collapsed")
    st.markdown('<p class="field-label">📞 SĐT kế toán <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["sdt_kt"] = st.text_input("f12", value=f["sdt_kt"], label_visibility="collapsed")

# --- 7. NÚT XÁC NHẬN ---
if st.button("📤 XÁC NHẬN CẬP NHẬT DỮ LIỆU", type="primary", use_container_width=True):
    required = {"ten": "Tên đơn vị", "qhns": "Mã QHNS", "rep": "Chủ tài khoản", "mst": "Mã số thuế", "tk_kb": "Số TK kho bạc", "chuc_vu": "Chức danh", "dc": "Địa chỉ", "ma_kb": "Mã Kho bạc", "kt": "Kế toán", "sdt_kt": "SĐT kế toán"}
    missing = [label for k, label in required.items() if not str(f[k]).strip()]
    
    if missing:
        st.error(f"❌ CẢNH BÁO: Vui lòng bổ sung: {', '.join(missing)}")
        speak_male("Bạn vui lòng bổ sung thông tin mới cho cập nhật")
    else:
        check = supabase.table("don_vi").select("mst").eq("mst", f["mst"]).execute()
        if check.data:
            st.session_state.show_confirm = True
            speak_male("Mã số thuế đã tồn tại, bạn có muốn ghi đè không")
            st.rerun()
        else: final_save(mode="NEW")
