"""
Gia lap nhiet do cho nhieu quan/huyen TPHCM, gui ve ThingsBoard qua MQTT.
Moi quan la 1 "tram do" rieng, nhiet do bien thien doc lap (random walk),
co lech nen theo dac diem khu vuc (noi thanh nong hon, ngoai thanh/ven song mat hon).

Cai thu vien: pip install paho-mqtt

Chay: py simulate_districts.py
"""

import sys
import time
import random
import json
import threading
import paho.mqtt.client as mqtt

# Console Windows mac dinh dung codepage cp1252, khong encode duoc ky tu co
# dau tieng Viet (vd "Quận") -> print() se crash thread ngay lap tuc. Ep
# stdout/stderr sang UTF-8 truoc khi in bat ky gi.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

THINGSBOARD_HOST = "localhost"
THINGSBOARD_PORT = 1883
SEND_INTERVAL_SECONDS = 3

# id, ten hien thi, lat, lng, token, nhiet do nen (bias) — noi thanh dong duc
# nong hon (hieu ung dao nhiet do thi - urban heat island), ngoai thanh/ven
# song/bien mat hon.
#
# LUU Y: cac "token" ben duoi la Access Token demo, gan voi Device tren
# ThingsBoard local cua nguoi viet code nay — KHONG dung duoc cho ThingsBoard
# cua ban. Vao ThingsBoard cua ban -> Devices -> tao/chon device -> "Manage
# credentials" de lay token that, roi thay vao dung vi tri tuong ung o day.
DISTRICTS = [
    {"id": "Q1",         "name": "Quận 1",          "lat": 10.7756, "lng": 106.7019, "token": "P3UI6rfIWv5dsADYYDMA", "base": 34.5},
    {"id": "Q3",         "name": "Quận 3",          "lat": 10.7843, "lng": 106.6829, "token": "NGeWDUcBkzVlQW75rrkC", "base": 34.0},
    {"id": "Q4",         "name": "Quận 4",          "lat": 10.7579, "lng": 106.7017, "token": "rydMqBg0daUqfgIEFznA", "base": 34.0},
    {"id": "Q5",         "name": "Quận 5",          "lat": 10.7546, "lng": 106.6634, "token": "UKKsDDHQQmKJNs6eGXxj", "base": 34.2},
    {"id": "Q6",         "name": "Quận 6",          "lat": 10.7461, "lng": 106.6349, "token": "YkT76Ec2vIIEtvjtTpSO", "base": 33.8},
    {"id": "Q7",         "name": "Quận 7",          "lat": 10.7340, "lng": 106.7217, "token": "Msuu0V4FjfdFn6NN5xlm", "base": 33.0},
    {"id": "Q8",         "name": "Quận 8",          "lat": 10.7231, "lng": 106.6285, "token": "pVMqWdsJO7ew7VXuBtAm", "base": 33.5},
    {"id": "Q10",        "name": "Quận 10",         "lat": 10.7726, "lng": 106.6674, "token": "WV6bHLP4Ye75ttNvox1g", "base": 34.3},
    {"id": "Q11",        "name": "Quận 11",         "lat": 10.7631, "lng": 106.6501, "token": "xQ0cC6WCqde5UujfqYxn", "base": 34.0},
    {"id": "Q12",        "name": "Quận 12",         "lat": 10.8671, "lng": 106.6413, "token": "wt3FapP5btwmOMbDELxp", "base": 32.5},
    {"id": "BinhThanh",  "name": "Bình Thạnh",      "lat": 10.8106, "lng": 106.7091, "token": "qmSfR9NUlNorvhnngvHR", "base": 33.8},
    {"id": "TanBinh",    "name": "Tân Bình",        "lat": 10.8014, "lng": 106.6525, "token": "ujxRQCxB2MrGc00uGOSv", "base": 34.0},
    {"id": "TanPhu",     "name": "Tân Phú",         "lat": 10.7900, "lng": 106.6280, "token": "hnEZhDyAuyNBECtLdCNg", "base": 33.7},
    {"id": "PhuNhuan",   "name": "Phú Nhuận",       "lat": 10.7990, "lng": 106.6797, "token": "5vMDoVPQ2WDUnroVv5Ik", "base": 33.9},
    {"id": "GoVap",      "name": "Gò Vấp",          "lat": 10.8386, "lng": 106.6653, "token": "cIaq10Re2Zp3YtKY9KPN", "base": 33.3},
    {"id": "BinhTan",    "name": "Bình Tân",        "lat": 10.7652, "lng": 106.6060, "token": "E1v48kj9TxNGfjG50W0o", "base": 33.2},
    {"id": "ThuDuc",     "name": "TP Thủ Đức",      "lat": 10.8494, "lng": 106.7537, "token": "duUi2teHXW2NumPokrHh", "base": 32.8},
    {"id": "BinhChanh",  "name": "Bình Chánh",      "lat": 10.6929, "lng": 106.5949, "token": "OylPHhuKbYNGZ9XkBT1q", "base": 32.0},
    {"id": "HocMon",     "name": "Hóc Môn",         "lat": 10.8862, "lng": 106.5921, "token": "d8FjUnXPxhcPCIxLUmsE", "base": 31.8},
    {"id": "CuChi",      "name": "Củ Chi",          "lat": 10.9736, "lng": 106.4930, "token": "azNlWWLSqwlRQM9i794G", "base": 31.5},
    {"id": "NhaBe",      "name": "Nhà Bè",          "lat": 10.6949, "lng": 106.7419, "token": "6nrOiUALEdsDXqvGGldB", "base": 31.7},
    {"id": "CanGio",     "name": "Cần Giờ",         "lat": 10.4113, "lng": 106.9560, "token": "UMA1RlNnhJiYbeteK7ND", "base": 30.0},
]


def simulate_district(district):
    client = mqtt.Client()
    client.username_pw_set(district["token"])
    client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, keepalive=60)
    client.loop_start()

    temperature = district["base"]

    print(f"[{district['name']}] Bat dau gui du lieu...")

    try:
        while True:
            temperature += random.uniform(-0.4, 0.4)
            # keo nhe ve gia tri nen — tranh random walk troi qua xa theo thoi gian
            temperature += (district["base"] - temperature) * 0.05
            temperature = max(district["base"] - 3, min(district["base"] + 3, temperature))

            payload = json.dumps({"temperature": round(temperature, 1)})
            client.publish("v1/devices/me/telemetry", payload)

            time.sleep(SEND_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


def main():
    threads = []
    for district in DISTRICTS:
        t = threading.Thread(target=simulate_district, args=(district,), daemon=True)
        t.start()
        threads.append(t)

    print(f"Dang gia lap {len(DISTRICTS)} tram do nhiet do TPHCM. Ctrl+C de dung.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDa dung gia lap.")


if __name__ == "__main__":
    main()
