# Giao thức Army3: phạm vi local-login

Tài liệu này đặc tả phần giao thức đã đủ để xây server localhost tối thiểu.
Nguồn là phân tích tĩnh của client đã hash trong M1; chưa có capture runtime
từ một phiên client hợp lệ.

## Mức độ chắc chắn

- `Confirmed`: control flow, phép đọc/ghi byte hoặc schema thấy trực tiếp
  trong mã native.
- `Inferred`: lựa chọn tương thích cho prototype, cần kiểm chứng runtime.
- `Unknown`: không gán tên nghiệp vụ hoặc hành vi khi chứng cứ chưa đủ.

Codec Python nằm tại `server/army3_protocol/`. Codec không mở socket, không
chứa logic đăng nhập và không truy cập mạng.

## Primitives

Các số nguyên trong payload hiện dùng thứ tự byte big-endian:

| Kiểu | Kích thước | Giới hạn |
| --- | ---: | ---: |
| `u8` | 1 byte | `0..255` |
| `u16` | 2 byte | `0..65535` |
| `u32` | 4 byte | `0..4294967295` |
| `string16` | `u16 length + bytes` | tối đa 65535 byte UTF-8 |

Reader từ chối payload thiếu byte, UTF-8 lỗi, chuỗi quá giới hạn và trailing
bytes khi schema yêu cầu tiêu thụ toàn bộ payload.

## Framing

Frame thông thường:

```text
[command:u8] [payloadLength:u16 BE] [payload]
```

`Confirmed`: mọi request client gửi trong đường đã khảo sát dùng length 2
byte, kể cả request rỗng `0xE1`.

Năm response server → client sau dùng length 4 byte:

```text
88 A4 C4 D7 E1
```

```text
[command:u8] [payloadLength:u32 BE] [payload]
```

Quy tắc length-4 là bất đối xứng theo hướng truyền, không phải thuộc tính
tuyệt đối của command.

`FrameStreamDecoder` giữ buffer giữa các lần `feed()`, nên xử lý được packet
bị chia nhỏ và nhiều packet dính liền. Decoder có giới hạn payload cấu hình
được và từ chối declared length vượt giới hạn trước khi chờ/cấp phát payload.

## Transform sau `0xE5`

Handshake gửi seed và shift. Key hiệu dụng là prefix-XOR:

```text
key[0] = seed[0]
key[i] = seed[i] XOR key[i - 1]
```

Command trên wire:

```text
rawCommand = ((logicalCommand + shift) mod 256) XOR key[index]
logicalCommand = ((rawCommand XOR key[index]) - shift) mod 256
```

Mỗi byte được transform làm cursor tăng một vị trí và quay vòng theo độ dài
key. Hai chiều truyền phải dùng hai cursor độc lập.

Với frame length-2, thứ tự tiêu thụ key là command, hai byte length, rồi
payload. Với năm response length-4, chỉ command tiêu thụ key; length và
payload giữ nguyên raw. Decoder dùng checkpoint nên dữ liệu chưa đủ một frame
không làm cursor tiến sai.

Prototype M5 sẽ dùng seed `00`, shift `00`. Đây là transform identity nhưng
vẫn bật đúng gate phía client và vẫn duy trì cursor.

## Message trong phạm vi

| Command | Hướng | Schema/tác dụng | Mức độ |
| --- | --- | --- | --- |
| `0xE5` | C → S | request rỗng | `Confirmed` |
| `0xE5` | S → C | seed, shift, text | schema `Confirmed`; giá trị local `Inferred` |
| `0xA9/0` | C → S | text đã lưu + hai counter `u32` | schema tĩnh và runtime `Confirmed` |
| `0x3A` | C → S | một byte | thứ tự/kích thước runtime `Confirmed`; nghiệp vụ `Unknown` |
| `0x72` | C → S | hai `u8` + `string16` | schema tĩnh và runtime `Confirmed` |
| `0xFD` | C → S | request rỗng | runtime `Confirmed` |
| `0xFD` | S → C | status `u8` | schema `Confirmed`; giá trị success còn `Inferred` |
| `0xB2` | C → S | một `u32` | kích thước runtime `Confirmed`; nghiệp vụ `Unknown` |
| `0x9A` | S → C | rỗng, heartbeat 10 giây | vai trò keepalive runtime `Confirmed` |
| `0xBB` | C → S | hai `string16`, `mode:u8` | `Confirmed` |
| `0xBB` | S → C | bốn `string16` | `Confirmed` |
| `0x07` | C → S | request rỗng | cấu trúc `Confirmed`; nghiệp vụ `Unknown` |
| `0xE2` | S → C | version E1, E0, DA | `Confirmed` |
| `0xDA` | C → S | request rỗng | `Confirmed` |
| `0xDA` | S → C | version + blob length-32 | `Confirmed` |
| `0xE1` | C → S | request rỗng, outer length-16 | `Confirmed` |
| `0xE1` | S → C | version + ba blob, outer length-32 | `Confirmed` |
| `0xE0` | C → S | request rỗng | `Confirmed` |
| `0xE0` | S → C | fixture hai collection rỗng | subset `Confirmed` |
| `0xDB` | C → S | request rỗng, báo barrier hoàn tất | cấu trúc `Confirmed`; ý nghĩa `Inferred` |

Schema chi tiết và test vector nằm ở
[messages/login-bootstrap.md](messages/login-bootstrap.md).

## API Python

```python
from server.army3_protocol.framing import (
    FrameDirection,
    FrameStreamDecoder,
    encode_frame,
)
from server.army3_protocol.messages import HandshakeResponse

message = HandshakeResponse(seed=b"\x00", shift=0, text="local")
wire = encode_frame(message.to_packet(), FrameDirection.SERVER_TO_CLIENT)

decoder = FrameStreamDecoder(FrameDirection.SERVER_TO_CLIENT)
packet = decoder.feed(wire)[0]
decoded = HandshakeResponse.decode_payload(packet.payload)
```

M5 tạo một `TransformCursor` riêng cho inbound và outbound sau khi đã gửi
response `0xE5` chưa transform.

## Giới hạn đã biết

- Chưa có capture runtime để xác nhận fixture identity với client thật.
- Nhánh frame length-2 không-transform của client có biểu thức native khác
  phép ghép `u16` thông thường; vector hiện dựa trên serializer và đường
  transform identity sẽ dùng ở M5.
- Chỉ subset collection rỗng của `0xE0` được model hóa. Codec chủ động từ
  chối record non-empty thay vì đoán schema.
- Codec chưa mô tả lobby, room, map hoặc gameplay.

## Chạy kiểm thử

Từ repository root:

```powershell
python -m unittest discover -s tests -v
```
