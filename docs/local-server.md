# Server Army3 cục bộ tối thiểu

Server Python hiện triển khai chuỗi kết nối/local-login đã xác định ở M3/M4
và các bước pre-login bổ sung được client thật xác nhận trong M6. Nó chưa phải
game server đầy đủ.

## Yêu cầu

- Python 3.10 trở lên;
- không cần package bên thứ ba;
- chạy từ repository root.

## Khởi động

```powershell
python -m server
```

Mặc định server chỉ listen tại:

```text
127.0.0.1:19150
```

Có thể chọn một port khác:

```powershell
python -m server --port 19151
```

Heartbeat mặc định là 10 giây; có thể đổi trong khoảng 0.1–300 giây:

```powershell
python -m server --heartbeat-interval 10
```

`--host` chỉ chấp nhận địa chỉ IP loopback dạng số, ví dụ `127.0.0.1` hoặc
`::1`. Các địa chỉ `0.0.0.0`, `::` và IP LAN/public bị từ chối trước khi mở
socket. Dùng `Ctrl+C` để dừng server.

## State machine mỗi kết nối

```text
AWAIT_CLIENT_E5
  client 0xE5 empty
  server 0xE5 identity handshake
  enable independent inbound/outbound transform cursors

AWAIT_INITIAL_BB
  optional client 0xA9/0 -> server 0xA9/2
  client 0x3A and 0x72: validate and discard
  client 0xFD empty -> server 0xFD(status byte)
  client 0xBB(two strings, mode)
  server 0xBB(four local strings)
  server 0xE2(version 2, 2, 2)

BOOTSTRAP
  client 0xB2(u32): validate and discard
  client 0x3A/0x72: transport metadata, validate and discard
  client 0xFD: return status; client 0xBB retry: replay 0xBB then 0xE2
  client 0x07: accept and ignore
  client 0xDA/0xE1/0xE0: return matching empty collection
  client 0xDB: enter ACCOUNT_PANEL_READY

ACCOUNT_PANEL_READY
  client 0xBB(two strings, mode 0/1)
  server 0xBB(four local strings)
```

Khi transform đã bật và socket im lặng, server gửi `0x9A` rỗng mỗi 10 giây.
Runtime M6 xác nhận client giữ cùng socket qua hơn 40 giây với heartbeat này;
không có heartbeat, client đóng socket sau khoảng 18–20 giây.

Ba request bootstrap có thể đến theo bất kỳ thứ tự nào hoặc không đến nếu
cache client đã khớp. Retry `0xBB` trong bootstrap replay cả response phiên và
version để hành vi deterministic; retry sau `0xDB` cũng được trả lời.

Runtime client thật đã parse và ghi cache version `2` từ ba response rỗng,
nhưng chưa gửi `0xDB` và vẫn đứng ở `Chuẩn bị tài nguyên... 100%`. Vì vậy server
hiện mới hoàn tất transport/cache bootstrap, chưa được coi là vượt đăng nhập.

Thứ tự server gửi `0xBB` rồi `0xE2` là lựa chọn triển khai `Inferred`; schema
và các transition client-side liên quan là `Confirmed` từ phân tích tĩnh.

## Logging và dữ liệu đầu vào

Log chỉ chứa connection ID, state, command và kích thước payload. Hai chuỗi
trong request `0xBB` không được lưu và không được ghi log. Server từ chối:

- command không hợp lệ trong state hiện tại;
- payload rỗng nhưng lại chứa dữ liệu;
- `0xBB` lỗi schema hoặc mode ngoài `0/1`;
- length vượt giới hạn 65535 byte;
- UTF-8 lỗi hoặc payload truncated.

Lỗi protocol chỉ đóng kết nối gây lỗi, không làm listener dừng.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```

Integration test mở listener trên `127.0.0.1` với port do hệ điều hành cấp,
chạy client mô phỏng qua toàn chuỗi handshake/bootstrap và đóng listener sau
test. Nó không chạy client gốc và không tạo kết nối outbound.

## Ngoài phạm vi server hiện tại

- profile, persistence, lobby, room, map và gameplay.
