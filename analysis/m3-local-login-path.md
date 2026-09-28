# M3: Đường tối thiểu để client đi qua form account/session

Phân tích tĩnh trên client đã hash ở M1, sau đó được đối chiếu bằng runtime cô
lập trên bản sao đã chuyển hướng về loopback. Không liên hệ server bên thứ ba.
Cấu trúc parser của các vector bên dưới là `Confirmed`; runtime đã xác nhận
client ghi cache rỗng nhưng chưa phát `0xDB` hoặc rời màn hình chuẩn bị tài
nguyên, nên toàn bộ đường UI vẫn chưa được xác nhận.

## Kết quả cần cho server đầu tiên

Đường ngắn nhất hiện đã đủ rõ để triển khai theo state machine sự kiện:

```text
client 0xE5 rỗng
  -> server 0xE5: cài transform
client 0xBB(UUID, config, 1), rồi 0x07 rỗng
  -> server 0xBB: bốn string, mở menu account/session
  -> server chủ động 0xE2: ba version
client có thể yêu cầu bất kỳ tập con nào của 0xDA / 0xE1 / 0xE0
  -> server trả response rỗng-về-nghiệp-vụ nhưng hợp lệ-về-cấu-trúc
client 0xDB rỗng: bootstrap hoàn tất, appReady = 1
người dùng mở panel mode 0 hoặc 1 và submit
client 0xBB(fieldB, fieldA, mode)
  -> server 0xBB: cùng schema bốn string
```

Server không được chờ một thứ tự cố định giữa `0xDA`, `0xE1`, `0xE0`. Nhánh
cache nào khớp version sẽ không phát request; client tự tải cache và tự đặt cờ
hoàn tất của nhánh đó. Server chỉ cần trả lời những request thực sự nhận được.

## `0xBB` là submit thật của panel hai field

`Confirmed` từ `FUN_180458420`, `FUN_180459240` và `FUN_1803151B0`:

- response `0xBB` đầu phiên thay menu row selector `1` từ hai thành bốn mục;
- option thứ ba và thứ tư mở cùng panel với `mode = 0` hoặc `mode = 1`;
- action `0x232B` là submit; hai control con nằm ở `+0x30` và `+0x38`, text
  của mỗi control nằm ở `+0x28`;
- nếu một text rỗng, handler chỉ focus control đó và không gửi mạng;
- nếu cả hai khác rỗng, handler đóng state panel hiện tại rồi gọi sender
  `0xBB` với payload:

```text
[fieldFromControl38:string16]
[fieldFromControl30:string16]
[mode:u8]
```

Vì label localization chưa được giải plaintext, chưa gán chắc hai field thành
username/password. Tuy nhiên đây là command submit thật của panel account/
session, không còn là một login candidate suy ra từ tên hàm. Handler response
không có status byte success/failure và không tự chuyển scene; nó luôn đọc bốn
string rồi cập nhật state/menu. Với local server không xác thực, trả lại một
response `0xBB` hợp lệ là hành vi tương thích tối thiểu. Việc đóng panel xảy ra
ở client trước khi gửi request.

Schema response `0xBB`:

```text
[listForMode1:string16]
[rawForMode1:string16]
[listForMode0:string16]
[rawForMode0:string16]
```

String 1 và 3 được split theo delimiter localization. Nếu delimiter không có
trong input, helper trả mảng một phần tử chứa nguyên string; do đó bốn giá trị
UTF-8 không rỗng như `local` là fixture an toàn về cấu trúc. Writer string của
client dùng UTF-8 và prefix độ dài byte `u16 BE`.

Với cả bốn string là `local`, payload dài `0x1C`:

```text
frame:
BB 00 1C
00 05 6C 6F 63 61 6C
00 05 6C 6F 63 61 6C
00 05 6C 6F 63 61 6C
00 05 6C 6F 63 61 6C
```

## Handshake identity cho prototype

Response `0xE5` có payload:

```text
[N:u8] [seed:N bytes] [shift:u8] [text:string16]
```

Chọn `N = 1`, `seed[0] = 0`, `shift = 0` tạo transform identity: client vẫn
bật đúng state/gate và vẫn tăng hai index gửi/nhận, nhưng mọi byte raw bằng
byte logic. Dùng text `local`, payload và frame là:

```text
payload: 01 00 00 00 05 6C 6F 63 61 6C
frame:   E5 00 0A 01 00 00 00 05 6C 6F 63 61 6C
```

Đây là lựa chọn triển khai local, không phải key quan sát từ server gốc.
`N = 1` đi qua nhánh cấp phát hợp lệ và prefix-XOR của seed zero vẫn là zero.

Client tạo `0xE5` với payload rỗng. Serializer luôn ghi length zero, nên server
phải chấp nhận tối thiểu `E5 00 00`. Sau response trên, request rỗng bình
thường cũng có hai byte length zero; với transform identity, ví dụ `0x07` là
`07 00 00` và `0xDB` là `DB 00 00`.

## Bootstrap collection rỗng hợp lệ

Dùng cùng một version byte cấu hình cho cả ba byte `0xE2`. Prototype hiện dùng
`V = 02` để khác cache `01` đã tồn tại và buộc client request đủ ba nhánh:

```text
frame: E2 00 03 02 02 02
```

Ba byte lần lượt là version của `0xE1`, `0xE0`, `0xDA`. Nếu client yêu cầu dữ
liệu mới, các response tối thiểu sau đi hết parser mà tạo collection rỗng.

### `0xDA`

Schema đã chốt:

```text
[version:u8]
[blobLength:u32 BE] [blob]

blob := [recordCount:u8] records...
```

`recordCount = 0` làm parser cấp phát collection rỗng rồi return. Fixture:

```text
payload: 02 00 00 00 01 00
frame:   DA 00 06 02 00 00 00 01 00
```

### `0xE1`

`0xE1` là một trong năm command dùng outer length 4 byte. Ba blob có count
đầu khác nhau:

```text
[version:u8]
[len1:u32 BE] [blob1]   blob1 := [count:u16 BE] ...
[len2:u32 BE] [blob2]   blob2 := [count:u16 BE] ...
[len3:u32 BE] [blob3]   blob3 := [count:u8] ...
```

Fixture collection rỗng:

```text
payload:
02
00 00 00 02  00 00
00 00 00 02  00 00
00 00 00 01  00

frame:
E1 00 00 00 12
02 00 00 00 02 00 00 00 00 00 02 00 00 00 00 00 01 00
```

Command `0xE1` vẫn tiêu thụ một key byte, nhưng outer length bốn byte và
payload không đi qua XOR trong parser đã thấy. Với transform identity sự khác
biệt này không làm đổi byte, nhưng codec vẫn phải giữ hai nhánh framing riêng.

### `0xE0`

Parser `FUN_1802649A0` đọc version, một count byte và một count 16-bit. Khi
hai count bằng zero, hai vòng record đều bỏ qua:

```text
payload: 02 00 00 00
frame:   E0 00 04 02 00 00 00
```

Phân tích tĩnh cho thấy handler tương ứng đặt readiness flag ngay sau khi
parser/cache path hoàn tất. Khi đủ ba flag, `FUN_18043D800` đặt `appReady = 1`,
gửi `0xDB` rỗng rồi xóa ba flag. Nhận `0xDB` vẫn là tiêu chí server-side tốt
nhất cho việc hoàn tất bootstrap, nhưng runtime hiện chưa đạt tiêu chí này.

### Đối chiếu runtime 2026-09-28

- `Confirmed`: khi server quảng bá version `2`, client gửi đủ `0xDA`, `0xE1`,
  `0xE0`; server lần lượt trả payload rỗng hợp lệ và socket tiếp tục sống với
  heartbeat `0x9A`.
- `Confirmed`: các file `vcData`, `vcItem`, `vcMap` đổi thành byte `02`; các
  file cache dữ liệu tương ứng được ghi với collection rỗng.
- `Confirmed`: client sau đó còn gửi `0xFD` và retry `0xBB`; server replay
  response `0xBB` cùng `0xE2`, nhưng client vẫn không gửi `0xDB`.
- `Confirmed`: kết nối loopback phụ cổng `443` mang TLS ClientHello với SNI
  `config.uca.cloud.unity3d.com`; đây là Unity Analytics config, không phải
  endpoint tài nguyên Army3 và không nên được giả lập như một phần protocol.
- `Unknown`: giá trị thực tế của ba readiness flag và việc singleton UI chứa
  `FUN_18043D800` có đang active. Công cụ read-only
  `tools/inspect_runtime_state.py` đã được thêm để phân biệt hai khả năng này
  ở lần chạy cô lập kế tiếp.

## Chuyển endpoint về loopback

`Confirmed`: endpoint được dùng bởi `TcpClient.Connect` có port mặc định
`19150`; đường UI chọn server chép `hosts[index]` và `ports[index]` vào endpoint
rồi gọi connect. Static constructor tạo host source từ một byte array dài 13
và giải bằng `Encoding.UTF8.GetString`.

`Inferred` mạnh: byte array dài 13 là `14.225.206.44`. Đây là chuỗi ASCII dài
13 duy nhất trong `global-metadata.dat` và xuất hiện một lần ở byte offset
`6469992`; nó khớp đúng field host dài 13 mà static constructor sử dụng.

Không sửa client gốc. Ở M6, tạo một bản sao làm việc ngoài thư mục reference
và thay đúng 13 byte bằng `127.000.000.1`. Chuỗi này cũng dài 13 và
`System.Net.IPAddress.Parse` trên môi trường hiện tại chuẩn hóa thành
`127.0.0.1`, nên không cần thay immediate độ dài trong `GameAssembly.dll`.
Đây là chiến lược patch ít điểm chạm, nhưng chỉ được nâng thành `Confirmed`
sau khi kiểm tra hash trước/sau, đúng một occurrence, và chạy client bản sao
trong môi trường outbound-blocked với sự cho phép rõ ràng của người dùng.

Server phải bind mặc định `127.0.0.1:19150`, không bind `0.0.0.0`.

## State machine nên triển khai

Server tối thiểu cần các state riêng cho mỗi kết nối:

1. `AwaitClientE5`: chỉ chấp nhận `0xE5`, trả handshake identity.
2. `AwaitInitialBB`: parse hai string + mode; trả bốn string `0xBB`.
3. `Bootstrap`: gửi `0xE2`, trả lời `0xDA/0xE1/0xE0` theo bất kỳ thứ tự nào,
   bỏ qua `0x07`, và đánh dấu hoàn tất khi nhận `0xDB`.
4. `AccountPanelReady`: chấp nhận thêm `0xBB` mode `0/1`, không kiểm tra nội
   dung hai field ở prototype, trả cùng schema bốn string.

Framing bất đối xứng cần được giữ rõ trong codec: mọi request client gửi qua
serializer đã thấy dùng outer length hai byte; tập command length-bốn-byte
(`0x88/0xA4/0xC4/0xD7/0xE1`) là quy tắc của parser **server → client**.
Vì vậy client request `0xE1` rỗng vẫn đến server dưới dạng `E1 00 00`, còn
server response `0xE1` phải dùng length 32-bit.

Không phát `0xA9/0`: client sẽ đóng/reset socket. Không cần phát `0x9A`; chưa
có watchdog phía client được xác nhận. Không đưa `0x2B` vào login path; đó là
form chín field thuộc onboarding/profile candidate.

## Tiêu chí hoàn thành cho lần chạy cô lập

- server chỉ listen trên `127.0.0.1:19150`;
- nhận đúng thứ tự đầu phiên `0xE5 -> 0xBB -> 0x07`;
- client gửi `0xDB` sau bootstrap;
- menu row account/session có bốn mục;
- mở được cả mode `0` và `1`, nhập hai field, submit mà không disconnect;
- server nhận `0xBB(fieldB, fieldA, mode)` và client rời form sau response;
- không có kết nối outbound khác trong capture của sandbox.

Đi vào world/spatial scene qua `0x9E/0` không nằm trong tiêu chí “qua đăng
nhập” này. Fixture bootstrap rỗng chưa cung cấp map/grid/entity data đủ để
cam kết scene đó hoạt động.

## Phần còn `Unknown`

- plaintext label và ngữ nghĩa chính xác của hai mode/hai field;
- UI nào được coi là màn hình “đã đăng nhập” trong bản chạy thật;
- thứ tự inbound gốc giữa response `0xBB` và server push `0xE2`;
- byte version/cache đang lưu trên một máy cụ thể;
- mapping field-RVA cuối cùng chứng minh tuyệt đối chuỗi IP dài 13 là host;
- mọi điều kiện runtime chỉ có thể xác nhận khi được phép chạy bản client sao
  chép trong môi trường cô lập.

## Chứng cứ tái lập

- `scripts/ghidra/DumpDecompile.java`: decompile read-only nhiều target.
- `analysis/generated/ghidra/auth-full-decompile.log`: panel submit và sender
  `0xBB`.
- `analysis/generated/ghidra/auth-menu-decompile.log`: menu row bốn mục và hai
  mode.
- `analysis/generated/ghidra/casee2-bootstrap-cfg-script.log`: ba version,
  ba request và barrier.
- `FUN_18029C670`, `FUN_1804F5C70`, `FUN_180451670`, `FUN_180450FA0` và
  `FUN_1802649A0`: parser collection cho `0xDA/0xE1/0xE0`, decompile read-only
  trong phiên phân tích này.
- `analysis/generated/ghidra/endpoint-init.log` và
  `analysis/generated/ghidra/endpoint-overrides.log`: port, byte-array host và
  đường chọn endpoint.

