# Bản đồ nhiệt độ TPHCM (IoT demo)

Demo giám sát nhiệt độ theo thời gian thực cho 22 quận/huyện TP.HCM — dữ liệu giả lập gửi qua MQTT vào ThingsBoard, tự động re-publish sang EMQX (broker trung tâm), hiển thị bằng bản đồ nhiệt mượt (CesiumJS).

## Yêu cầu

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 


## Chạy demo 

```bash
docker compose up --build
```

Lần đầu chạy sẽ mất khoảng **1-2 phút** (ThingsBoard cần thời gian khởi tạo database). Chờ tới khi thấy dòng log:
```
iot-temp-init | === INIT XONG ===
```

## Mở xem

| Địa chỉ | Nội dung |
|---|---|
| **http://localhost:8080** | Bản đồ nhiệt độ (mở cái này để xem demo) |
| http://localhost:3001 | Giao diện quản trị ThingsBoard (`tenant@thingsboard.org` / `tenant`) |
| http://localhost:18083 | Giao diện quản trị EMQX (`admin` / `public`) |

## Dừng demo

```bash
docker compose down
```

Muốn xoá luôn dữ liệu (device, lịch sử...) để chạy lại từ đầu:
```bash
docker compose down -v
```

## Kiến trúc

```
simulator (giả lập 22 trạm) --MQTT--> ThingsBoard --Rule Chain--> EMQX --WebSocket--> trình duyệt
                                            |
                                        server.py (chỉ dùng lúc mở trang, lấy vị trí/tên quận)
```

- **`init`**: chạy 1 lần lúc khởi động — tự tạo 22 Device trên ThingsBoard, lấy Access Token, và tự nối Rule Chain để dữ liệu tự động chảy sang EMQX (không cần làm tay).
- **`simulator`**: giả lập nhiệt độ 22 quận, gửi qua MQTT mỗi 3 giây.
- **`server`**: cấp vị trí/tên quận cho trình duyệt lúc mở trang (dữ liệu này không có trong MQTT).
- **`frontend`**: trang bản đồ, sau khi tải xong thì **kết nối thẳng vào EMQX** để nhận nhiệt độ real-time — không cần hỏi lại `server` liên tục.


