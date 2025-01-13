import sys
import time
import requests
import logging

# # Log yapılandırması
# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[
#         logging.StreamHandler(),  # Konsola log yazdır
#         logging.FileHandler("application.log", mode="a", encoding="utf-8")  # Dosyaya log yazdır
#     ]
# )


# Global değişkenler
session = None
login_cookies = None
login_headers = None

# Giriş işlemi
def login():
    global session, login_cookies, login_headers
    login_url = "http://192.168.58.2/action/login"
    login_data = {"username": "admin", "password": "123"}
    session = requests.Session()
    try:
        login_response = session.post(login_url, data=login_data)

        if login_response.status_code == 200:
            login_cookies = session.cookies.get_dict()
            login_headers = login_response.headers
        else:
            logging.error(f"Giriş başarısız: {login_response.status_code}")
            logging.error("Hata mesajı: %s", login_response.text)
            sys.exit()
    except requests.RequestException as e:
        logging.exception("Giriş sırasında bir hata oluştu.")
        sys.exit()

# Komut gönderme fonksiyonu
def send_command(cmd_data):
    global session, login_cookies, login_headers

    # Giriş kontrolü
    if not login_cookies or not login_headers:
        login()

    set_url = "http://192.168.58.2/action/set"
    cookie_value = login_cookies.get("-goahead-session-", "")
    headers = {
        "accept": login_headers.get("accept", "application/json, text/plain, */*"),
        "accept-encoding": login_headers.get("accept-encoding", "gzip, deflate"),
        "accept-language": login_headers.get("accept-language", "en-US,en;q=0.9"),
        "connection": "keep-alive",
        "content-type": "application/json;charset=UTF-8",
        "cookie": f"-goahead-session-={cookie_value}",
        "origin": "http://192.168.58.2",
        "referer": "http://192.168.58.2/index.html",
        "user-agent": login_headers.get("user-agent", "Mozilla/5.0 (X11; Linux x86_64)")
    }
    
    try:
        response = session.post(set_url, headers=headers, json=cmd_data)
        if response.status_code == 200:
            return response.text
        else:
            logging.error(f"İstek başarısız: {response.status_code}")
            logging.error("Hata mesajı: %s", response.text)
            return None
    except requests.RequestException as e:
        logging.exception("Komut gönderme sırasında bir hata oluştu.")
        return None