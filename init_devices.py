"""
Chay 1 lan khi 'docker-compose up' khoi dong (service "init") — tu dong hoa
toan bo phan truoc day phai lam tay:
  1. Cho ThingsBoard san sang (co the mat 60-90s lan dau)
  2. Tao (hoac tai su dung neu da co) 22 Device dai dien 22 quan/huyen TPHCM
  3. Ghi Access Token that cua tung Device ra file JSON dung chung — de
     service "simulator" doc lai, khong can hardcode token trong code
  4. Them node MQTT "Republish to EMQX" vao Root Rule Chain cua ThingsBoard
     (idempotent — chay lai nhieu lan khong tao node trung)

Bien moi truong (dat san trong docker-compose.yml):
  TB_HOST, TB_USERNAME, TB_PASSWORD, EMQX_HOST, EMQX_PORT, SHARED_DIR
"""

import os
import sys
import time
import json
import requests

sys.stdout.reconfigure(encoding="utf-8")

TB_HOST = os.environ.get("TB_HOST", "http://thingsboard:9090")
TB_USERNAME = os.environ.get("TB_USERNAME", "tenant@thingsboard.org")
TB_PASSWORD = os.environ.get("TB_PASSWORD", "tenant")
EMQX_HOST = os.environ.get("EMQX_HOST", "emqx")
EMQX_PORT = int(os.environ.get("EMQX_PORT", "1883"))
SHARED_DIR = os.environ.get("SHARED_DIR", "/shared")

DISTRICT_IDS = [
    "Q1", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q10", "Q11", "Q12",
    "BinhThanh", "TanBinh", "TanPhu", "PhuNhuan", "GoVap", "BinhTan",
    "ThuDuc", "BinhChanh", "HocMon", "CuChi", "NhaBe", "CanGio",
]


def wait_for_thingsboard(max_wait_s=180):
    print("Cho ThingsBoard san sang (lan dau co the mat 60-90s)...")
    start = time.time()
    while time.time() - start < max_wait_s:
        try:
            r = requests.post(
                f"{TB_HOST}/api/auth/login",
                json={"username": TB_USERNAME, "password": TB_PASSWORD},
                timeout=5,
            )
            if r.status_code == 200:
                print("ThingsBoard da san sang.")
                return r.json()["token"]
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    raise RuntimeError(f"ThingsBoard khong san sang sau {max_wait_s}s.")


def tb_headers(token):
    return {"X-Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def ensure_device(token, device_name):
    """Tra ve Access Token cua device — tao moi neu chua co (idempotent, chay
    lai docker-compose up nhieu lan khong tao trung device)."""
    r = requests.get(
        f"{TB_HOST}/api/tenant/devices?deviceName={device_name}",
        headers=tb_headers(token),
    )
    if r.status_code == 200:
        device_id = r.json()["id"]["id"]
    else:
        r = requests.post(
            f"{TB_HOST}/api/device",
            headers=tb_headers(token),
            json={"name": device_name, "type": "default"},
        )
        r.raise_for_status()
        device_id = r.json()["id"]["id"]

    cred = requests.get(f"{TB_HOST}/api/device/{device_id}/credentials", headers=tb_headers(token))
    cred.raise_for_status()
    return cred.json()["credentialsId"]


def ensure_rule_chain_node(token):
    """Them node MQTT re-publish sang EMQX vao Root Rule Chain — idempotent
    (kiem tra ten node truoc, khong them trung neu chay lai)."""
    r = requests.get(f"{TB_HOST}/api/ruleChains?pageSize=20&page=0", headers=tb_headers(token))
    r.raise_for_status()
    root = next((rc for rc in r.json()["data"] if rc.get("root")), None)
    if root is None:
        print("CANH BAO: khong tim thay Root Rule Chain, bo qua buoc noi EMQX.")
        return
    root_id = root["id"]["id"]

    meta = requests.get(f"{TB_HOST}/api/ruleChain/{root_id}/metadata", headers=tb_headers(token)).json()

    if any(n.get("name") == "Republish to EMQX" for n in meta["nodes"]):
        print("Node 'Republish to EMQX' da co san, bo qua.")
        return

    switch_idx = next(
        (i for i, n in enumerate(meta["nodes"])
         if n["type"] == "org.thingsboard.rule.engine.filter.TbMsgTypeSwitchNode"),
        None,
    )
    if switch_idx is None:
        print("CANH BAO: khong tim thay node 'Message Type Switch', bo qua buoc noi EMQX.")
        return

    new_node = {
        "type": "org.thingsboard.rule.engine.mqtt.TbMqttNode",
        "name": "Republish to EMQX",
        "debugMode": False,
        "configuration": {
            "topicPattern": "twin/${deviceName}/telemetry",
            "host": EMQX_HOST,
            "port": EMQX_PORT,
            "connectTimeoutSec": 10,
            "cleanSession": True,
            "ssl": False,
            "parseToPlainText": False,
            "retainedMessage": True,
            "credentials": {"type": "anonymous"},
        },
        "additionalInfo": {"description": "Re-publish telemetry sang EMQX cho DigitalTwin Backend + Frontend"},
    }
    new_idx = len(meta["nodes"])
    meta["nodes"].append(new_node)
    meta["connections"].append({"fromIndex": switch_idx, "toIndex": new_idx, "type": "Post telemetry"})

    save = requests.post(f"{TB_HOST}/api/ruleChain/metadata", headers=tb_headers(token), json=meta)
    save.raise_for_status()
    print(f"Da them node 'Republish to EMQX' (host={EMQX_HOST}:{EMQX_PORT}) vao Rule Chain.")


def main():
    token = wait_for_thingsboard()

    tokens = {}
    for district_id in DISTRICT_IDS:
        device_name = f"CamBien-{district_id}"
        tokens[district_id] = ensure_device(token, device_name)
        print(f"  {device_name}: OK")

    os.makedirs(SHARED_DIR, exist_ok=True)
    tokens_path = os.path.join(SHARED_DIR, "device_tokens.json")
    with open(tokens_path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False)
    print(f"Da ghi {len(tokens)} token vao {tokens_path}")

    ensure_rule_chain_node(token)
    print("=== INIT XONG ===")


if __name__ == "__main__":
    main()
