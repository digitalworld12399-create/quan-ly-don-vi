import requests

# Danh sách các URL cần đánh thức
LIST_URLS = [
    "https://quan-ly-don-vi-fjkqqt42dehhosixg4r3zy.streamlit.app/",
    "https://quan-ly-don-vi-mzbftixs3wct4ammhpdmvq.streamlit.app/"
]

def wake_up():
    print(f"--- Bắt đầu tiến trình đánh thức app ({len(LIST_URLS)} trang) ---")
    
    for url in LIST_URLS:
        try:
            # Gửi yêu cầu truy cập đến từng URL
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                print(f"✅ Thành công: {url}")
            else:
                print(f"⚠️ Thông báo: {url} phản hồi mã lỗi {response.status_code}")
        except Exception as e:
            print(f"❌ Lỗi kết nối tại {url}: {e}")
    
    print("--- Kết thúc tiến trình ---")

if __name__ == "__main__":
    wake_up()
