import streamlit as st
import requests
from supabase import create_client, Client
import re
from datetime import datetime
import time
import pandas as pd
import os # Bổ sung thư viện os để kiểm tra tệp tồn tại

# --- 1. KẾT NỐI HỆ THỐNG ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

# Cấu hình API và Telegram
X_CLIENT_ID = "YOUR_CLIENT_ID" 
X_API_KEY = "YOUR_API_KEY"
TELE_TOKEN = "8208357912:AAHm-dNSkmCl4HgxpgnSCjoH6uGdjjZvsMA"
TELE_CHAT_ID = "7446579212" 

# === PHẦN LOGO MỚI ĐƯỢC BỔ SUNG ===
# Tên tệp logo của bạn. Tệp này cần được đặt cùng cấp với tệp code .py này.
# Ví dụ: "logo.png", "logo.jpg", v.v.
LOGO_FILE = "logo.png"

# --- 2. HÀM HỖ TRỢ ---
@st.cache_data
def load_danhmuc():
    file_name = 'danhmuc.csv'
    try:
        # Sử dụng utf-8-sig cho file csv có dấu
        df = pd.read_csv(file_name, sep=';', engine='python', encoding='utf-8-sig')
        col_name = df.columns[0]
        return sorted(df[col_name].dropna().unique().tolist())
    except Exception as e:
        # Nếu lỗi tải file, trả về danh mục mặc định
        return ["Huyện Đồng Văn", "Huyện Mèo Vạc", "Khác"]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        payload = {"chat_id": TELE_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        # Có thể thêm log lỗi tại đây
        pass

def speak_male(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={text.replace(' ', '%20')}&tl=vi&client=tw-ob"
    st.components.v1.html(f"<script>new Audio('{tts_url}').play();</script>", height=0)

# Tải danh mục huyện
LIST_HUYEN = load_danhmuc()

# Khởi tạo trạng thái Session State
if 'form' not in st.session_state:
    st.session_state.form = {
        "mst": "", "ten": "", "dc": "", "rep": "", "qhns": "", "thue": "", 
        "ma_kb": "", "tk_kb": "", "kt": "", "sdt_kt": "", "chuc_vu": "", 
        "san_pham": "", # Ô này dùng cho "Mã số máy" nhập tay
        "huyen_cu": LIST_HUYEN[0] if LIST_HUYEN else "Huyện Đồng Văn"
    }
if 'show_confirm' not in st.session_state: st.session_state.show_confirm = False
if 'search_status' not in st.session_state: st.session_state.search_status = None
if 'session_history' not in st.session_state: st.session_state.session_history = []

# --- 3. HÀM LƯU DỮ LIỆU ---
def final_save(mode="NEW"):
    f = st.session_state.form
    now_obj = datetime.now()
    now_str = now_obj.strftime("%H:%M:%S %d/%m/%Y")
    
    # Payload cho 'don_vi' table (với 'san_pham' - mã số máy)
    payload = {
        "mst": f["mst"], "ten_don_vi": f["ten"], "dia_chi": f["dc"], "ma_qhns": f["qhns"],
        "so_tkkb": f["tk_kb"], "ma_kbnn": f["ma_kb"], "co_quan_thue": f["thue"],
        "chu_tai_khoan": f["rep"], "chuc_vu": f["chuc_vu"], "ke_toan": f["kt"],
        "sdt_ke_toan": f["sdt_kt"], "san_pham": f["san_pham"], 
        "huyen_cu": f["huyen_cu"],
        "last_update": now_obj.isoformat()
    }
    
    try:
        # Ghi/Cập nhật dữ liệu đơn vị vào table 'don_vi'
        supabase.table("don_vi").upsert(payload, on_conflict="mst").execute()
        
        # Lưu lịch sử log vào table 'lich_su_cap_nhat'
        log_data = {
            "mst": f["mst"], "ten_don_vi": f["ten"], 
            "hanh_dong": "GHI ĐÈ" if mode == "OVERWRITE" else "THÊM MỚI",
            "thoi_gian": now_obj.isoformat()
        }
        supabase.table("lich_su_cap_nhat").insert(log_data).execute()
        
        # Thêm vào nhật ký phiên làm việc
        st.session_state.session_history.insert(0, f"🕒 {now_str} | {mode}: {f['ten']}")
        
        # Gửi thông báo đến Telegram
        prefix = "⚠️ *GHI ĐÈ DỮ LIỆU*" if mode == "OVERWRITE" else "🆕 *THÊM MỚI ĐƠN VỊ*"
        msg = f"{prefix}\n🏢 {f['ten']}\n📍 {f['huyen_cu']}\n🆔 MST: {f['mst']}\n👨‍💼 {f['kt']} ({f['sdt_kt']})"
        send_telegram(msg)
        
        # Trạng thái thành công
        st.session_state.show_confirm = False
        st.balloons()
        speak_male("Cập nhật dữ liệu thành công")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Lỗi lưu dữ liệu: {e}")

# --- 4. GIAO DIỆN ---
st.set_page_config(page_title="HN11 - Quản lý đơn vị", layout="wide")

# Thiết lập CSS
st.markdown("""
<style>
    .field-label { font-weight: bold; color: #004a99; margin-bottom: 2px; font-size: 14px; }
    .red-star { color: #ff0000; font-weight: bold; }
    /* Giảm padding cho ô search để nó vừa với nút tra cứu */
    div[data-testid="stTextInput"] div[data-testid="stInputWidget"] input {
        padding-top: 6px;
        padding-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR VỚI LOGO ---
with st.sidebar:
    # === PHẦN LOGO MỚI ĐƯỢC BỔ SUNG ===
    # Hiển thị logo ở trên cùng của Sidebar
    if os.path.exists(LOGO_FILE):
        # use_container_width=True giúp logo tự động căn giữa và điều chỉnh độ rộng
        st.image(LOGO_FILE, use_container_width=True) 
    else:
        # Nếu không tìm thấy file, hiển thị thông báo thay thế
        st.error(f"Không tìm thấy tệp logo tại: {LOGO_FILE}")
    
    st.divider()

    # Phần thông tin hệ thống
    st.markdown(f"""
    <div style="background-color: #fdfae6; padding: 25px; border-radius: 12px; border: 1px solid #d4a017; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
    <div style="display: flex; align-items: center; margin-bottom: 15px;">
        <div style="background-color: #8b4513; color: white; padding: 8px; border-radius: 50%; margin-right: 15px; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 20px;">👤</span>
        </div>
        <h4 style="color: #5d4037; margin: 0; font-size: 1.2em; font-weight: 600;">Hoàn Thiện Thông Tin Người Dùng</h4>
    </div>
    
    <div style="margin-left: 55px;">
        <p style="color: #4e342e; margin: 0; line-height: 1.6; font-size: 1em;">
            Kính thưa Anh/Chị, để đảm bảo quyền lợi và nhận được sự hỗ trợ chuyên biệt nhất trong quá trình xử lý nghiệp vụ, kính mời Anh/Chị vui lòng rà soát và cập nhật đầy đủ thông tin cá nhân. 
        </p>
        <p style="color: #795548; margin-top: 8px; font-size: 0.9em; font-style: italic;">
            (Sự chính xác của thông tin sẽ giúp chúng tôi phục vụ Anh/Chị chu đáo và bảo mật hơn)
        </p>
        
        <div style="margin-top: 20px;">
            <a href="#" style="background-color: #8b4513; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 0.9em; display: inline-block; transition: background 0.3s;">
                CẬP NHẬT THÔNG TIN
            </a>
        </div>
    </div>
</div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # --- LIÊN KẾT TRANG QUẢN TRỊ (MỚI) ---
    st.link_button("🚀 ĐĂNG NHẬP QUẢN TRỊ", "https://quan-ly-don-vi-mzbftixs3wct4ammhpdmvq.streamlit.app/", use_container_width=True, type="primary")
    
    st.divider()
    # Nút kiểm tra cập nhật (Theo yêu cầu trước đó)
    st.link_button("🔄 KIỂM TRA CẬP NHẬT", "https://your-update-link.com", use_container_width=True)

    st.divider()
    st.subheader("📜 Nhật ký phiên làm việc")
    if st.session_state.session_history:
        for item in st.session_state.session_history[:8]:
            st.caption(item)
    else:
        st.write("Chưa có dữ liệu mới.")

# Xử lý xác nhận ghi đè
if st.session_state.show_confirm:
    st.warning(f"### ⚠️ XÁC NHẬN GHI ĐÈ\nMST {st.session_state.form['mst']} đã tồn tại. Bạn muốn cập nhật?")
    c1, c2 = st.columns(2)
    if c1.button("✅ ĐỒNG Ý", type="primary", use_container_width=True): final_save(mode="OVERWRITE")
    if c2.button("❌ HỦY", use_container_width=True): st.session_state.show_confirm = False; st.rerun()
    st.stop()

# Tiêu đề chính
st.markdown('<h1 style="text-align:center; color:#1E90FF; margin-bottom: 20px;">🏦 HỆ THỐNG CẬP NHẬT ĐƠN VỊ HN11</h1>', unsafe_allow_html=True)

# --- 5. TRA CỨU ---
c_search, c_btn = st.columns([ 1.8, 1.2 ])
with c_search:
    txt_mst = st.text_input("Search", placeholder="Nhập mã số thuế để tra cứu...", label_visibility="collapsed")

with c_btn:
    if st.button("🔍 TRA CỨU", type="primary", use_container_width=True):
        # Làm sạch mã số thuế (chỉ giữ số)
        v_mst = re.sub(r'[^0-9]', '', txt_mst)
        
        if v_mst:
            # 5a. Tra cứu trong Supabase trước
            res = supabase.table("don_vi").select("*").eq("mst", v_mst).execute()
            if res.data:
                # Đã tồn tại đơn vị
                d = res.data[0]
                st.session_state.form.update({
                    "mst": v_mst, "ten": d.get("ten_don_vi"), "dc": d.get("dia_chi"),
                    "qhns": d.get("ma_qhns"), "tk_kb": d.get("so_tkkb"), "ma_kb": d.get("ma_kbnn"),
                    "thue": d.get("co_quan_thue"), "rep": d.get("chu_tai_khoan"), "chuc_vu": d.get("chuc_vu"),
                    "kt": d.get("ke_toan"), "sdt_kt": d.get("sdt_ke_toan"), "san_pham": d.get("san_pham"),
                    "huyen_cu": d.get("huyen_cu", LIST_HUYEN[0] if LIST_HUYEN else "")
                })
                st.session_state.search_status = "found"
            else:
                # 5b. Tra cứu qua API XInvoice nếu chưa có trong DB
                try:
                    # Gửi request API (Bạn nên sử dụng st.secrets cho bảo mật)
                    r = requests.get(f"https://api.xinvoice.vn/gdt-api/tax-payer/{v_mst}", headers={'client-id': X_CLIENT_ID, 'api-key': X_API_KEY}, timeout=10)
                    info = r.json().get("data", r.json())
                    if info and info.get("name"):
                        # Chuẩn hóa tên đơn vị
                        ten_dv_toupper = str(info.get("name", "")).upper()
                        st.session_state.form.update({"mst": v_mst, "ten": ten_dv_toupper, "dc": info.get("address", "")})
                        st.session_state.search_status = "found"
                    else: st.session_state.search_status = "not_found"
                except Exception as e: st.session_state.search_status = "not_found"
            
            # Thông báo khi không tìm thấy
            if st.session_state.search_status == "not_found":
                speak_male("Không tìm thấy thông tin mã số thuế, vui lòng nhập tay")
            st.rerun()

# Hiển thị thông báo trạng thái tra cứu
if st.session_state.search_status == "not_found":
    st.error("❌ Không tìm thấy thông tin. Vui lòng kiểm tra lại MST hoặc nhập tay toàn bộ thông tin.")
elif st.session_state.search_status == "found":
    st.success("✅ Đã tìm thấy dữ liệu đơn vị.")

st.divider()

# --- 6. FORM NHẬP LIỆU (3 CỘT) ---
f = st.session_state.form
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<p class="field-label">🏢 Tên đơn vị <span class="red-star">*</span></p>', unsafe_allow_html=True)
    # value=f["ten"] lấy dữ liệu từ form tìm được hoặc để trống
    f["ten"] = st.text_input("f1", value=f["ten"], label_visibility="collapsed")
    st.markdown('<p class="field-label">🆔 Mã số thuế <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["mst"] = st.text_input("f2", value=f["mst"], label_visibility="collapsed")
    st.markdown('<p class="field-label">📍 Địa chỉ <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["dc"] = st.text_input("f3", value=f["dc"], label_visibility="collapsed")
    
    st.markdown('<p class="field-label">Khu vực cũ (Huyện)</p>', unsafe_allow_html=True)
    # Xác định index cho selectbox dựa trên giá trị form hiện có
    if f["huyen_cu"] in LIST_HUYEN:
        idx_huyen = LIST_HUYEN.index(f["huyen_cu"])
    else:
        idx_huyen = 0
    f["huyen_cu"] = st.selectbox("f_huyen", LIST_HUYEN, index=idx_huyen, label_visibility="collapsed")

with col2:
    st.markdown('<p class="field-label">🏦 Mã QHNS (7 chữ số) <span class="red-star">*</span></p>', unsafe_allow_html=True)
    qhns_val = st.text_input("f5", value=f["qhns"], label_visibility="collapsed", max_chars=7)
    # Xử lý tự động điền 'Số TK kho bạc' nếu 'Mã QHNS' đủ 7 ký tự
    if qhns_val != f["qhns"]:
        # Giữ lại logic tự động điền cũ của bạn
        if len(qhns_val) == 7:
            st.session_state.form["qhns"] = qhns_val
            f["tk_kb"] = f"9523.4.{qhns_val}"
            st.rerun() # Reload để update ô Số TK kho bạc
        else:
            f["qhns"] = qhns_val

    st.markdown('<p class="field-label">💰 Số TK kho bạc <span class="red-star">*</span></p>', unsafe_allow_html=True)
    # Ô này tự động điền từ Mã QHNS
    f["tk_kb"] = st.text_input("f6", value=f["tk_kb"], label_visibility="collapsed")
    
    st.markdown('<p class="field-label">🏛️ Mã Kho bạc Nhà nước <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["ma_kb"] = st.text_input("f7", value=f["ma_kb"], label_visibility="collapsed")
    
    st.markdown('<p class="field-label">🧾 Mã số máy (DTSoft điền)</p>', unsafe_allow_html=True)
    f["san_pham"] = st.text_input("f4", value=f["san_pham"], label_visibility="collapsed")

with col3:
    st.markdown('<p class="field-label">👤 Họ tên Thủ trưởng (Rep) <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["rep"] = st.text_input("f9", value=f["rep"], label_visibility="collapsed")
    st.markdown('<p class="field-label">🎖️ Chức danh <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["chuc_vu"] = st.text_input("f10", value=f["chuc_vu"], label_visibility="collapsed")
    st.markdown('<p class="field-label">👨‍💼 Kế toán trưởng/Kế toán viên <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["kt"] = st.text_input("f11", value=f["kt"], label_visibility="collapsed")
    st.markdown('<p class="field-label">📞 SĐT kế toán <span class="red-star">*</span></p>', unsafe_allow_html=True)
    f["sdt_kt"] = st.text_input("f12", value=f["sdt_kt"], label_visibility="collapsed")

# --- 7. NÚT XÁC NHẬN ---
if st.button("📤 XÁC NHẬN CẬP NHẬT DỮ LIỆU", type="primary", use_container_width=True):
    # Kiểm tra các trường bắt buộc
    required = {"ten": "Tên đơn vị", "qhns": "Mã QHNS", "rep": "Chủ tài khoản", "mst": "Mã số thuế", "tk_kb": "Số TK kho bạc", "chuc_vu": "Chức danh", "dc": "Địa chỉ", "ma_kb": "Mã Kho bạc", "kt": "Kế toán", "sdt_kt": "SĐT kế toán"}
    
    missing = []
    # Kiểm tra từng trường và tạo danh sách các trường thiếu
    for k, label in required.items():
        if not str(f[k]).strip(): # Strip khoảng trắng
            missing.append(label)
    
    if missing:
        # Hiển thị thông báo lỗi nếu thiếu thông tin
        st.error(f"❌ CẢNH BÁO: Vui lòng bổ sung đầy đủ thông tin: {', '.join(missing)}")
        speak_male("Bạn vui lòng bổ sung thông tin mới cho cập nhật")
    else:
        # Nếu đủ thông tin, kiểm tra xem MST đã tồn tại trong DB chưa
        check = supabase.table("don_vi").select("mst").eq("mst", f["mst"]).execute()
        if check.data:
            # Nếu MST tồn tại, hiển thị xác nhận ghi đè
            st.session_state.show_confirm = True
            speak_male("Mã số thuế đã tồn tại, bạn có muốn ghi đè không")
            st.rerun()
        else:
            # Nếu MST mới, lưu trực tiếp
            final_save(mode="NEW")
