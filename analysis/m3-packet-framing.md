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

## Đường gửi

`Confirmed` trong decompile `FUN_1804E1B60`:

- Có `BinaryWriter` ở field tĩnh `+0x18`; byte lệnh được ghi trước độ dài và
  payload. Khi cờ `+0x60` bật, byte lệnh được cộng field `+0x70` rồi qua
  `FUN_1804E04F0` trước khi ghi.
- Nếu payload không rỗng, nhánh biến đổi ghi hai byte độ dài từ `length >> 8`
  và `length & 0xff`, sau đó biến đổi từng byte payload trước khi ghi. Nhánh
  không biến đổi gọi virtual write với `length & 0xffff`; chưa xác nhận
  endianness của overload đó từ mã native đã trích.
- `FUN_1804E04F0` cũng XOR với mảng khóa field `+0x68`, nhưng dùng chỉ số
  gửi riêng tại `+0x72`. Hai chỉ số gửi/nhận không được dùng lẫn nhau.

## Giới hạn trước khi viết codec

Đây **chưa phải đặc tả giao thức**. Đường nhận `0xE5` có logic thiết lập
khóa và bật cờ; xem [trạng thái biến đổi byte](m3-byte-transform-state.md).
Chưa xác nhận: giá trị khóa thực tế; endianness đầy đủ ở mọi nhánh; giới hạn
độ dài; trường hợp payload rỗng; ý nghĩa byte lệnh; quan hệ giữa frame
4-byte nhận và frame phía gửi;
các nhánh lỗi/truncated stream. Không có test vector hợp lệ, nên chưa nên
triển khai codec như một hành vi đã xác nhận với client.

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
