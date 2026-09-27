# M3: Các nhánh message đặc biệt trong worker nhận

Phân tích tĩnh trên bản client đã hash ở M1. Không có capture và không chạy
client/server bên thứ ba. Các byte dưới đây là byte lệnh **sau** phép biến
đổi tùy trạng thái, không nhất thiết là byte thô trên TCP.

Worker `FUN_1804E3D60` phân nhánh trước khi chuyển message cho đường xử lý
chung:

| Byte lệnh | Handler | Hành vi đã thấy trong native | Ý nghĩa nghiệp vụ |
| --- | --- | --- | --- |
| `0xE5` | `FUN_1804E2E00` | Đọc dữ liệu message để dựng mảng khóa, byte dịch lệnh và bật cờ biến đổi | Inferred: thiết lập biến đổi; xem [báo cáo riêng](m3-byte-transform-state.md) |
| `0xA9` | `FUN_1804E2920` | Đọc byte đầu làm nhánh con `0`, `1` hoặc `2` | Inferred: đồng bộ trạng thái transport/queue |
| `0x83` | `FUN_1804E31B0` | Đọc các byte đầu, dùng byte thứ ba làm độ dài cho mảng dữ liệu tiếp theo; lưu mảng vào một field tĩnh khác | Unknown |

`Confirmed` chi tiết cho `0xA9`:

- Client có thể tạo `0xA9` ở `FUN_1804E00C0`. Payload luôn bắt đầu bằng
  subcommand; subcommand `0` còn ghi một giá trị length-prefixed từ field
  phiên `+0x30`, rồi hai số 32-bit big-endian ở transport `+0x94/+0x90`.
- Nhánh nhận `0` đặt cờ `+0xB1` về `0`, so chênh lệch thời gian với `501 ms`
  để gọi callback với giá trị `1` hoặc `2`, rồi gọi đường đóng/reset
  `FUN_1804E09B0`.
- Nhánh nhận `1` đặt `+0xB1` thành `1`, xóa/duyệt collection, đọc một số
  4-byte big-endian và bỏ qua thêm bốn byte. Nếu số đầu khác `+0x94`, nó
  hiệu chỉnh theo số phần tử collection rồi có thể gọi `FUN_1804DFDD0`.
- Nhánh nhận `2` đặt cờ `+0x61`, xóa hai bộ đếm `+0x90/+0x94` và gọi một
  virtual method trên collection.

`Inferred`: `0xA9` đồng bộ trạng thái hàng đợi/phiên của transport. Chưa đủ
bằng chứng để đặt tên heartbeat, reconnect hoặc login cho từng nhánh.

`Confirmed` cho `0x83`: handler đọc ít nhất ba byte điều khiển, dùng byte
thứ ba để cấp phát và chép dữ liệu tiếp theo, lưu mảng vào class pointer
`DAT_181455F48`; tùy byte điều khiển thứ hai có thể tạo một message gửi
qua `FUN_1804DFFE0`. Cấu trúc payload và mục đích chưa xác định.

`0x9A` được loại khỏi một bộ đếm trong parser nhưng worker không có nhánh
riêng; entry ứng dụng của nó còn đi thẳng về nhánh mặc định. Quét đủ 128
direct call-site của constructor message chuẩn không tìm thấy sender `0x9A`.
Đây là ứng viên no-op/keepalive một chiều từ server, nhưng vẫn chỉ `Inferred`:
chưa có chu kỳ, watchdog hay phản hồi client để xác nhận heartbeat. Xem
[vòng đời kết nối](m3-connection-lifecycle.md).

Chứng cứ: `analysis/generated/ghidra/native-workers.log` và
`analysis/generated/ghidra/transport-special-messages.log`, tạo bằng
`scripts/ghidra/InspectNativeTargets.java` ở chế độ read-only.
