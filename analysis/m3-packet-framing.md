# M3: Khung packet ở đường gửi/nhận

Phân tích tĩnh trên client đã hash ở M1. Không chạy client, không liên hệ
server bên thứ ba. Log Ghidra bên dưới là output sinh ra và bị Git bỏ qua.

## Đường nhận

`Confirmed` trong decompile `FUN_1804E35E0` (worker nhận gọi hàm này):

- Đọc byte đầu từ `BinaryReader` tại field tĩnh `+0x10` của type transport.
  Khi cờ `+0x60` bật, byte đầu đi qua `FUN_1804E0400` rồi trừ field `+0x70`.
- Predicate trên byte lệnh dẫn đến `FUN_1804E3390`. Hàm này đọc **bốn byte**
  tiếp theo, ghép thành độ dài 32-bit theo thứ tự byte cao trước, cấp phát
  buffer và đọc đúng số byte đó. Theo biểu thức decompile, các giá trị đầu
  vào của predicate là `0x88`, `0xA4`, `0xC4`, `0xD7`, `0xE1`. Helper này
  không gọi hàm XOR trên bốn byte độ dài hoặc payload trong đường được thấy.
- Nhánh còn lại đọc **hai byte** độ dài rồi đọc payload. Khi cờ `+0x60` bật,
  mỗi byte độ dài và payload đi qua `FUN_1804E0400` trước khi được dùng.
  Disassembly của nhánh không biến đổi dùng `movsx ebx, al` rồi
  `and ebx, 0xFF00`, sau đó OR với byte thứ hai. Vì vậy mã máy tính
  `(sign_extend(first) & 0xFF00) | second`, **không phải** phép ghép
  16-bit thông thường. Chưa biết nhánh này được dùng với tập giá trị nào
  trong phiên thực tế; không suy ra codec chung chỉ từ nhánh đó.
- Cuối cả hai nhánh, client tạo object message từ byte lệnh và payload.
  Bốn giá trị `0xE5`, `0xA9`, `0x9A`, `0x83` được loại khỏi một bộ đếm;
  điều đó không xác định ý nghĩa của chúng.

`Confirmed` trong `FUN_1804E0400`: lấy byte ở mảng field `+0x68`, XOR với
byte đầu vào, rồi tăng/chuyển vòng chỉ số nhận tại `+0x71`. Đây là phép biến
đổi byte có trạng thái, không đủ để suy ra khóa khởi tạo hay handshake.

### Công thức command thô và command logic

Gọi `K[i]` là byte khóa hiệu dụng tại chỉ số nhận hiện tại, `S` là byte ở
field `+0x70`, và mọi phép cộng/trừ đều lấy modulo 256. Native code thực hiện:

```text
logicalCommand = (rawCommand XOR K[recvIndex]) - S
recvIndex       = (recvIndex + 1) mod keyLength
```

Do XOR tự nghịch đảo, chiều server cần tạo command thô là:

```text
rawCommand = (logicalCommand + S) XOR K[recvIndex]
```

Vì vậy entry logic `0x16` và `0x54` chỉ trùng raw byte khi cờ biến đổi
`+0x60` tắt. Khi cờ bật, raw byte tương ứng phụ thuộc cả `K[recvIndex]` và
`S`; không tồn tại một raw command cố định cho mỗi entry nếu chưa biết state
của phiên.

Với frame hai-byte-length khi biến đổi bật, thứ tự tiêu thụ key là:

```text
command -> lengthHigh -> lengthLow -> payload[0] -> ... -> payload[n-1]
```

Năm logical command `0x88`, `0xA4`, `0xC4`, `0xD7`, `0xE1` đi vào helper
length 4 byte. Command của chúng vẫn đi qua công thức trên và tiêu thụ một
key byte, nhưng bốn byte length cùng payload trong helper đã thấy **không**
gọi `FUN_1804E0400`; do đó chúng không tiến chỉ số key nhận. Đây là khác biệt
có ý nghĩa khi tái tạo state machine, dù tên nghiệp vụ của năm command vẫn
chưa được xác định hoàn toàn. Cấu trúc handler đã lần riêng ở
[m3-length4-commands.md](m3-length4-commands.md): `0x88` đọc sáu `u64`;
`0xE1` đọc một byte rồi ba blob length-prefixed; `0xA4/0xC4/0xD7` vẫn còn
nhiều nhánh chưa đủ tên nghiệp vụ.

## Đường gửi

`Confirmed` trong decompile `FUN_1804E1B60`:

- Có `BinaryWriter` ở field tĩnh `+0x18`; byte lệnh được ghi trước độ dài và
  payload. Khi cờ `+0x60` bật, byte lệnh được cộng field `+0x70` rồi qua
  `FUN_1804E04F0` trước khi ghi.
- Nếu payload không rỗng, nhánh biến đổi ghi hai byte độ dài từ `length >> 8`
  và `length & 0xff`, sau đó biến đổi từng byte payload trước khi ghi. Nhánh
  không biến đổi gọi virtual write với `length & 0xffff`; chưa xác nhận
  endianness của overload đó từ mã native đã trích.
- Nếu writer payload có length `0`, `FUN_1802FFCD0` trả null và serializer vẫn
  ghi length zero. Khi transform tắt nó gọi overload ghi giá trị `0`; khi
  transform bật nó ghi hai byte zero qua helper XOR. Vì vậy request rỗng vẫn
  là một frame có command và length, không phải command đơn lẻ.
- `FUN_1804E04F0` cũng XOR với mảng khóa field `+0x68`, nhưng dùng chỉ số
  gửi riêng tại `+0x72`. Hai chỉ số gửi/nhận không được dùng lẫn nhau.

Đường gửi xác nhận phép nghịch đảo tương ứng: client cộng `S` vào logical
command rồi XOR qua `FUN_1804E04F0`. Khi payload có dữ liệu và biến đổi bật,
thứ tự key gửi cũng là command, hai byte length cao/thấp, rồi từng byte
payload. Chỉ số gửi bắt đầu từ field `+0x72`, độc lập với chỉ số nhận.

Fixture local có thể chọn response `0xE5` với `N=1`, seed `00`, shift `00`.
Prefix-XOR key khi đó là `00`, nên transform là identity nhưng gate/state vẫn
được bật đúng đường. Vector đầy đủ và giới hạn của lựa chọn này ở
[m3-local-login-path.md](m3-local-login-path.md).

## Giới hạn trước khi viết codec

Đây **chưa phải đặc tả giao thức**. Đường nhận `0xE5` có logic thiết lập
khóa và bật cờ; xem [trạng thái biến đổi byte](m3-byte-transform-state.md).
Chưa xác nhận: giá trị khóa/shift thực tế của một phiên; endianness đầy đủ ở mọi nhánh; giới hạn
độ dài; ý nghĩa byte lệnh; quan hệ giữa frame
4-byte nhận và frame phía gửi; các nhánh lỗi/truncated stream. Chưa có capture
runtime hợp lệ; fixture tối thiểu hiện tại được suy ra từ mã tĩnh, nên cần giữ
nhãn `Inferred` cho tới khi kiểm chứng với client cô lập.

## Chứng cứ tái lập

- `analysis/generated/ghidra/native-io.log`: decompile `FUN_1804E35E0`.
- `analysis/generated/ghidra/native-send2.log`: decompile `FUN_1804E1B60`.
- `analysis/generated/ghidra/packet-special.log`: decompile
  `FUN_1804E3390` và `FUN_1804E0400`.
- `analysis/generated/ghidra/packet-transform-send.log`: decompile
  `FUN_1804E04F0`.

Các hàm được truy bằng script chỉ đọc
`scripts/ghidra/InspectNativeTargets.java`, trong project Ghidra phân tích
từng phần, với `-process GameAssembly.dll -noanalysis -readOnly`.

Phép nghịch đảo command có thể kiểm tra độc lập bằng:

```powershell
./scripts/verify-command-transform.ps1
./scripts/verify-command-transform.ps1 -Seed 0x10,0x20,0x30 -Shift 0x07 -LogicalCommand 0x54 -ReceiveIndex 1
```

Script tính prefix-XOR key theo payload `0xE5`, encode/decode một command và
kiểm tra nghịch đảo trên 262.144 tổ hợp command/shift/key mẫu. Đây là kiểm
tra công thức, không thay thế test vector lấy từ một phiên client hợp lệ.
