# M3: Đối chiếu transport ở IL2CPP native

Phân tích tĩnh, không chạy client và không liên hệ server bên thứ ba. `Confirmed`
ở đây là bằng chứng trong binary/output công cụ, không phải hành vi đã quan sát
trong phiên chơi. Log và ISIL đầy đủ nằm dưới `analysis/generated/` (Git-ignored).

## Tái lập

```powershell
./scripts/run-cpp2il.ps1 -OutputAs isil
```

Output `isil` chứa disassembly và ISIL cho từng method. Trên project Ghidra
`analysis/generated/ghidra/army3-native` đã import từ client gốc, dùng script
`scripts/ghidra/InspectNativeTargets.java` với `-process GameAssembly.dll
-noanalysis -readOnly -postScript InspectNativeTargets.java <hex-address>`.
Project Ghidra mới phân tích một phần do lần auto-analysis trước hết hạn 600s.
Script chỉ đọc, in function chứa địa chỉ, xref, call trực tiếp và bản decompile
giới hạn 12.000 ký tự/function; không sửa database.

## Ánh xạ kết nối

| Method trong `Assembly-CSharp.dll` khôi phục | Native trong Ghidra | Chứng cứ |
| --- | --- | --- |
| `0x0600028D`, nhận `(string, int)` | `FUN_1804DF5A0` | ISIL disassembly có nhánh tới `0x1804DF68F`; Ghidra xác định function chứa địa chỉ đó bắt đầu tại `0x1804DF5A0`, với xref call từ `0x1804DF3E6` của wrapper |
| Callback worker dùng hàng đợi | `FUN_1804E2520` | ISIL của nested type có nhánh `0x1804E2586`; Ghidra ánh xạ tới function này |
| Callback worker lấy message | `FUN_1804E3D60` | ISIL của nested type có nhánh `0x1804E3DBA`; Ghidra ánh xạ tới function này |

`Confirmed`: trong ISIL, lời gọi `TcpClient.Connect` ở method đầu dùng chính
tham số `string` và `int`; trước đó tạo `TcpClient`, sau đó lấy stream, tạo
`BinaryReader` và `BinaryWriter`, rồi khởi động hai worker. Wrapper `0x0600028C`
lấy host và port từ hai field của instance; caller ngoài transport lấy cặp
giá trị từ field tĩnh của type endpoint. Port khởi tạo là `19150`, nhưng
có đường ghi đè trước kết nối; xem [báo cáo endpoint](m3-endpoint-state.md). Địa chỉ native và token chỉ đúng với bản client có hash ở M1.

## Hai worker và ranh giới packet

`Confirmed` từ bản decompile native đối chiếu với ISIL:

- `FUN_1804E2520` lặp khi cờ kết nối còn bật, kiểm tra danh sách/hàng đợi,
  lấy phần tử rồi gọi `FUN_1804E02F0`; hàm này gọi tiếp `FUN_1804E1B60`.
  `FUN_1804E1B60` truy cập field tại offset tĩnh `+0x18` (field
  `BinaryWriter` theo metadata) và có nhiều virtual call ghi byte/dữ liệu.
  Do đó callback thứ nhất là đường **gửi** ở mức cấu trúc.
- `FUN_1804E3D60` gọi `FUN_1804E35E0` để lấy message. Hàm này truy cập field
  `+0x10` (`BinaryReader` theo metadata), đọc một byte đầu và dữ liệu tiếp
  theo, rồi tạo object message. Do đó callback thứ hai là đường **nhận** ở mức
  cấu trúc.
- Worker nhận có nhánh riêng cho `0xE5`, `0xA9`, `0x83`; `0x9A` chỉ được
  loại khỏi một bộ đếm trong parser đã thấy. Xem
  [các nhánh message đặc biệt](m3-special-messages.md); không đặt tên
  heartbeat khi chưa có chứng cứ.
- Đường nhận có một nhánh đọc bốn byte độ dài và nhánh thường đọc hai byte.
  Mã máy của nhánh thường khi chưa bật biến đổi **không** ghép độ dài 16-bit
  theo cách thông thường; chi tiết và giới hạn ở báo cáo khung packet.
- Cả hai worker có lời gọi sleep `5` trong nhánh lặp. Chưa chứng minh đây là
  chu kỳ heartbeat; chỉ là chờ khi không có việc hoặc sau xử lý.

Chi tiết nhánh độ dài 2/4 byte và phép XOR có chỉ số riêng mỗi chiều được ghi
trong [báo cáo khung packet](m3-packet-framing.md); chưa có test vector để
xác nhận codec với client. Đã lần message `0xE5` tới việc dựng khóa/bật cờ và
đường reset; xem [trạng thái biến đổi byte](m3-byte-transform-state.md).

`Unknown`: giá trị endpoint thực tế ở mọi phiên, thời điểm nhận `0xE5`, khóa thực tế, thứ tự chính xác
mọi nhánh framing, giới hạn payload, bảng command ID, ngữ nghĩa message,
reconnect, state chuyển màn hình và quyền mô phỏng trận. Chưa có test vector
vì không có capture hợp lệ và chưa kiểm chứng codec với client cô lập.

## Bước tiếp theo của M3

1. Đã lần endpoint tới callback của mục chọn trong client; tiếp tục nối với
   scene/callback Unity và kiểm tra đầu vào người dùng thực tế.
2. Kiểm tra chéo endian và các nhánh lỗi của parser; tìm message lifecycle
   sau `0xE5` trước khi viết codec.
3. Lần type trạng thái phòng/trận và hàm tính toán để kết luận ranh giới
   mô phỏng trước khi chốt M3 hoặc triển khai server.
