import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import io
import re

# --- KẾT NỐI ---
URL = "https://niqehefvnzwbfwafncej.supabase.co"
KEY = "sb_publishable_3clZvjfg6EoOxZQ0QzsBOQ_m2v9KiKN"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="HN11 Admin", layout="wide")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    with st.container(border=True):
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.button("Login"):
            if u == "kh" and p == "a11": st.session_state.auth = True; st.rerun()
            else: st.error("Sai!")
    st.stop()

# --- DATA ---
try:
    res = supabase.table("don_vi").select("*").execute()
    df = pd.DataFrame(res.data)

    with st.sidebar:
        st.header("🛡️ HN11 ADMIN")
        # Bộ lọc Huyện cũ
        huyen_list = ["Tất cả"] + sorted(df['huyen_cu'].dropna().unique().tolist())
        sel_huyen = st.selectbox("Lọc theo Huyện cũ:", huyen_list)
        st.divider()
        if st.button("🚪 Thoát"): st.session_state.auth = False; st.rerun()

    df_f = df if sel_huyen == "Tất cả" else df[df['huyen_cu'] == sel_huyen]

    # Dashboard mini
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Tổng đơn vị", len(df))
    c2.metric("Đang hiển thị", len(df_f))
    
    with c3:
        fig = px.bar(df_f['huyen_cu'].value_counts().reset_index(), x='count', y='huyen_cu', 
                     orientation='h', height=150, title="Thống kê vùng")
        fig.update_layout(margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_f, use_container_width=True, hide_index=True)

    # Chi tiết
    st.subheader("📋 CHI TIẾT ĐƠN VỊ")
    target = st.selectbox("Chọn đơn vị:", ["-- Chọn --"] + df_f['ten_don_vi'].tolist())
    
    if target != "-- Chọn --":
        row = df_f[df_f['ten_don_vi'] == target].iloc[0]
        labels = {
            "mst": "MST", "ten_don_vi": "Tên", "dia_chi": "Địa chỉ", 
            "huyen_cu": "Khu vực", "ma_qhns": "QHNS", "so_tkkb": "TK Kho bạc",
            "ma_kbnn": "Mã Kho bạc", "chu_tai_khoan": "Chủ TK", "ke_toan": "Kế toán",
            "sdt_ke_toan": "SĐT KT", "san_pham": "Mã máy DTSoft"
        }
        
        with st.container(border=True):
            cols = st.columns(3)
            for i, (k, v) in enumerate(labels.items()):
                with cols[i % 3]:
                    st.write(f"**{v}:** {row.get(k, 'N/A')}")
            
            st.divider()
            # Xuất Excel cho đơn vị đang chọn
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame([row]).to_excel(writer, index=False)
            st.download_button("📊 XUẤT EXCEL ĐƠN VỊ", output.getvalue(), f"{row['mst']}.xlsx", use_container_width=True)

except Exception as e: st.error(f"Lỗi: {e}")
