# M3: Các nhánh message đặc biệt trong worker nhận

Phân tích tĩnh trên bản client đã hash ở M1. Không có capture và không chạy
client/server bên thứ ba. Các byte dưới đây là byte lệnh **sau** phép biến
đổi tùy trạng thái, không nhất thiết là byte thô trên TCP.

Worker `FUN_1804E3D60` phân nhánh trước khi chuyển message cho đường xử lý
chung:

| Byte lệnh | Handler | Hành vi đã thấy trong native | Ý nghĩa nghiệp vụ |
| --- | --- | --- | --- |
| `0xE5` | `FUN_1804E2E00` | Đọc dữ liệu message để dựng mảng khóa, byte dịch lệnh và bật cờ biến đổi | Inferred: thiết lập biến đổi; xem [báo cáo riêng](m3-byte-transform-state.md) |
| `0xA9` | `FUN_1804E2920` | Đọc byte đầu làm nhánh con `0`, `1` hoặc `2` | Unknown |
| `0x83` | `FUN_1804E31B0` | Đọc các byte đầu, dùng byte thứ ba làm độ dài cho mảng dữ liệu tiếp theo; lưu mảng vào một field tĩnh khác | Unknown |

`Confirmed` chi tiết cho `0xA9`: nhánh con `0` đặt cờ `+0xB1` của transport
về `0`, rồi gọi đường đóng/reset `FUN_1804E09B0`; nhánh `1` đặt cờ này thành
`1`, đọc một giá trị 4 byte theo thứ tự byte cao trước và bỏ qua thêm bốn
byte, sau đó có thể gọi `FUN_1804DFDD0`; nhánh `2` đặt cờ `+0x61`, xóa hai
bộ đếm `+0x90/+0x94` và thao tác trên một collection. Không đặt tên
heartbeat/reconnect cho các nhánh này khi chưa xác định caller và ý nghĩa
field.

`Confirmed` cho `0x83`: handler đọc ít nhất ba byte điều khiển, dùng byte
thứ ba để cấp phát và chép dữ liệu tiếp theo, lưu mảng vào class pointer
`DAT_181455F48`; tùy byte điều khiển thứ hai có thể tạo một message gửi
qua `FUN_1804DFFE0`. Cấu trúc payload và mục đích chưa xác định.

`0x9A` được loại khỏi một bộ đếm trong parser nhưng worker không có nhánh
riêng cho nó trong đoạn decompile đã thấy; không suy ra nó tương đương ba
byte lệnh trên.

Chứng cứ: `analysis/generated/ghidra/native-workers.log` và
`analysis/generated/ghidra/transport-special-messages.log`, tạo bằng
`scripts/ghidra/InspectNativeTargets.java` ở chế độ read-only.
