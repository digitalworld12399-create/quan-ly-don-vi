import requests

# Thay link app của bạn vào đây
URL = "https://quan-ly-don-vi-fjkqqt42dehhosixg4r3zy.streamlit.app/"

def wake_up():
    try:
        response = requests.get(URL)
        if response.status_code == 200:
            print("Thành công: Ứng dụng đã được đánh thức!")
        else:
            print(f"Thông báo: App phản hồi mã lỗi {response.status_code}")
    except Exception as e:
        print(f"Lỗi kết nối: {e}")

if __name__ == "__main__":
    wake_up()
