"""
Service trung gian: lay nhiet do TAT CA quan/huyen TPHCM tu ThingsBoard,
tra ve 1 API duy nhat cho frontend ve heatmap.

Cai: py -m pip install fastapi uvicorn requests
Chay: py -m uvicorn server:app --reload --port 8001

Test: http://localhost:8001/api/districts/temperatures
"""

import time
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# LUU Y: sua lai cho dung ThingsBoard cua ban — 3 dong duoi la cua may demo
# local (mac dinh ThingsBoard CE: tenant@thingsboard.org / tenant).
TB_HOST = "http://localhost:3001"
TB_USERNAME = "tenant@thingsboard.org"
TB_PASSWORD = "tenant"

# id -> (ten Device tren ThingsBoard, ten hien thi, lat, lng)
DISTRICTS = {
    "Q1":        ("CamBien-Q1", "Quận 1", 10.7756, 106.7019),
    "Q3":        ("CamBien-Q3", "Quận 3", 10.7843, 106.6829),
    "Q4":        ("CamBien-Q4", "Quận 4", 10.7579, 106.7017),
    "Q5":        ("CamBien-Q5", "Quận 5", 10.7546, 106.6634),
    "Q6":        ("CamBien-Q6", "Quận 6", 10.7461, 106.6349),
    "Q7":        ("CamBien-Q7", "Quận 7", 10.7340, 106.7217),
    "Q8":        ("CamBien-Q8", "Quận 8", 10.7231, 106.6285),
    "Q10":       ("CamBien-Q10", "Quận 10", 10.7726, 106.6674),
    "Q11":       ("CamBien-Q11", "Quận 11", 10.7631, 106.6501),
    "Q12":       ("CamBien-Q12", "Quận 12", 10.8671, 106.6413),
    "BinhThanh": ("CamBien-BinhThanh", "Bình Thạnh", 10.8106, 106.7091),
    "TanBinh":   ("CamBien-TanBinh", "Tân Bình", 10.8014, 106.6525),
    "TanPhu":    ("CamBien-TanPhu", "Tân Phú", 10.7900, 106.6280),
    "PhuNhuan":  ("CamBien-PhuNhuan", "Phú Nhuận", 10.7990, 106.6797),
    "GoVap":     ("CamBien-GoVap", "Gò Vấp", 10.8386, 106.6653),
    "BinhTan":   ("CamBien-BinhTan", "Bình Tân", 10.7652, 106.6060),
    "ThuDuc":    ("CamBien-ThuDuc", "TP Thủ Đức", 10.8494, 106.7537),
    "BinhChanh": ("CamBien-BinhChanh", "Bình Chánh", 10.6929, 106.5949),
    "HocMon":    ("CamBien-HocMon", "Hóc Môn", 10.8862, 106.5921),
    "CuChi":     ("CamBien-CuChi", "Củ Chi", 10.9736, 106.4930),
    "NhaBe":     ("CamBien-NhaBe", "Nhà Bè", 10.6949, 106.7419),
    "CanGio":    ("CamBien-CanGio", "Cần Giờ", 10.4113, 106.9560),
}

app = FastAPI(title="TPHCM Temperature Heatmap Bridge")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_jwt_token = None
_jwt_expires_at = 0
_device_id_cache = {}


def get_jwt_token():
    global _jwt_token, _jwt_expires_at
    if _jwt_token and time.time() < _jwt_expires_at:
        return _jwt_token
    resp = requests.post(f"{TB_HOST}/api/auth/login", json={"username": TB_USERNAME, "password": TB_PASSWORD}, timeout=10)
    resp.raise_for_status()
    _jwt_token = resp.json()["token"]
    _jwt_expires_at = time.time() + 60 * 15
    return _jwt_token


def tb_get(path):
    resp = requests.get(f"{TB_HOST}{path}", headers={"X-Authorization": f"Bearer {get_jwt_token()}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_device_id(device_name):
    if device_name in _device_id_cache:
        return _device_id_cache[device_name]
    data = tb_get(f"/api/tenant/devices?deviceName={device_name}")
    device_id = data["id"]["id"]
    _device_id_cache[device_name] = device_id
    return device_id


def get_latest_temperature(device_id):
    data = tb_get(f"/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys=temperature")
    entries = data.get("temperature")
    if not entries or entries[0].get("value") is None:
        return None
    return float(entries[0]["value"])


@app.get("/api/districts/temperatures")
def get_all_temperatures():
    results = []
    for district_id, (device_name, display_name, lat, lng) in DISTRICTS.items():
        try:
            device_id = get_device_id(device_name)
            temperature = get_latest_temperature(device_id)
        except Exception:
            temperature = None
        results.append({
            "id": district_id,
            "name": display_name,
            "lat": lat,
            "lng": lng,
            "temperature": temperature,
        })
    return {"districts": results}
