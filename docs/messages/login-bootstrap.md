# Message schema và vector local-login

Các frame dưới đây là fixture nhỏ, không chứa tài khoản hoặc dữ liệu lấy từ
server bên thứ ba. Byte hiển thị ở dạng hex.

## `0xE5` handshake

Client request rỗng:

```text
E5 00 00
```

Server payload:

```text
[seedLength:u8] [seed] [shift:u8] [text:string16]
```

Fixture identity:

```text
E5 00 0A 01 00 00 00 05 6C 6F 63 61 6C
```

Response này được gửi trước khi server bật transform cho các frame tiếp theo.

## `0xA9/0` transport sync

Capture client localhost ngày 2026-09-28 xác nhận client có thể gửi message
này ngay sau response `0xE5`, trước FIFO `0xBB/0x07`:

```text
[subcommand:u8=0]
[storedText:string16]
[counter94:u32 BE]
[counter90:u32 BE]
```

Với `storedText = "local"` và hai counter zero, payload dài 16 byte. Server
local parse nghiêm ngặt rồi trả `0xA9/2` payload `02` để yêu cầu reset counters
của phiên không có lịch sử, sau đó tiếp tục chờ initial `0xBB`. Không gửi
`0xA9/0` ngược lại vì nhánh nhận đó làm client đóng/reset socket. Việc chọn
`/2` thay vì `/1` là hành vi server `Inferred` đang được kiểm chứng runtime.

## Pre-login runtime `0x3A`, `0x72`, `0xFD`, `0xB2`

Client thật trong phiên localhost cô lập đã xác nhận thứ tự có thể xuất hiện:

```text
client 0x3A [value:u8]
client 0x72 [value1:u8] [value2:u8] [text:string16]
client 0xFD empty
server 0xFD [status:u8]
client 0xBB ...
client 0xB2 [value:u32 BE]
client 0x07 empty
```

Schema sender `0x72` được đối chiếu với native; kích thước của `0x3A`, `0xFD`
và `0xB2` được xác nhận bằng runtime. Ý nghĩa nghiệp vụ của các field vẫn
`Unknown`, server chỉ parse nghiêm ngặt rồi loại bỏ. `0xFD` được client xử lý
qua callback nhận một byte; fixture local dùng `status = 1`, nhưng ý nghĩa
success/failure của giá trị này vẫn `Inferred` vì thử `0` và `1` cho cùng
chuỗi wire quan sát được.

## `0x9A` heartbeat

Sau khi transform được bật, server gửi frame rỗng `0x9A` mỗi 10 giây:

```text
9A 00 00
```

Không heartbeat, client thật đóng socket sau khoảng 18–20 giây im lặng. Với
`0x9A`, cùng socket được giữ qua hơn 40 giây và bốn heartbeat liên tiếp. Vai
trò keepalive vì vậy là `Confirmed` ở runtime; app dispatcher không cần gửi
response cho command này.

## `0xBB` client/session

Client payload:

```text
[fieldFromControl38:string16]
[fieldFromControl30:string16]
[mode:u8]
```

Tên và ý nghĩa thật của hai field là `Unknown`; không ghi log giá trị này ở
M5. Cấu trúc submit và thứ tự field là `Confirmed`.

Server payload:

```text
[listForMode1:string16]
[rawForMode1:string16]
[listForMode0:string16]
[rawForMode0:string16]
```

Fixture dùng bốn chuỗi `local`:

```text
BB 00 1C
00 05 6C 6F 63 61 6C
00 05 6C 6F 63 61 6C
00 05 6C 6F 63 61 6C
00 05 6C 6F 63 61 6C
```

## `0xE2` version bootstrap

Payload:

```text
[e1Version:u8] [e0Version:u8] [daVersion:u8]
```

Fixture:

```text
E2 00 03 01 01 01
```

Client có thể request bất kỳ tập con nào của `0xDA`, `0xE1`, `0xE0`, theo
bất kỳ thứ tự nào, vì cache local có thể đã khớp một hoặc nhiều version.

## `0xDA` empty collection

Payload:

```text
[version:u8] [blobLength:u32 BE] [blob]
blob := [recordCount:u8] records...
```

Fixture count zero:

```text
DA 00 06 01 00 00 00 01 00
```

## `0xE1` ba empty collection

Payload:

```text
[version:u8]
[blob1Length:u32 BE] [blob1]  # blob1 count:u16 BE
[blob2Length:u32 BE] [blob2]  # blob2 count:u16 BE
[blob3Length:u32 BE] [blob3]  # blob3 count:u8
```

Response `0xE1` dùng outer length 4 byte:

```text
E1 00 00 00 12
01
00 00 00 02 00 00
00 00 00 02 00 00
00 00 00 01 00
```

Request client vẫn là frame length-2:

```text
E1 00 00
```

## `0xE0` empty collection subset

Payload fixture:

```text
[version:u8] [firstCount:u8=0] [secondCount:u16 BE=0]
```

```text
E0 00 04 01 00 00 00
```

Codec M4 chỉ hỗ trợ subset count zero. Record non-empty bị từ chối rõ ràng
vì schema đầy đủ chưa được xác nhận.

## `0x07` và `0xDB`

Cả hai request đã thấy đều rỗng và dùng length 2 byte:

```text
07 00 00
DB 00 00
```

Ngữ nghĩa `0x07` là `Unknown`. `0xDB` được gửi khi ba nhánh bootstrap đã hội
tụ; gọi nó là ready notification vẫn là `Inferred`.
