# Trạng thái client — bản nháp M3

Chưa đủ bằng chứng để vẽ state machine đăng nhập/lobby/phòng/trận. Sơ đồ dưới
đây chỉ mô tả phần chọn endpoint và kết nối trong IL/native, **không phải**
chuỗi màn hình hay message đã được xác nhận.

```text
Khởi tạo host/port mặc định hoặc chọn cặp từ danh sách
    ↓ (đường chọn endpoint gọi caller 0x060001C1)
Yêu cầu mở kết nối
    ↓ (0x0600028A tạo thread; 0x0600028C gọi 0x0600028D)
Thử kết nối TCP
    ↓ (TcpClient.Connect, rồi GetStream)
Khởi tạo BinaryReader/BinaryWriter
    ↓ (hai worker Thread.Start)
Trạng thái trao đổi dữ liệu: chưa rõ
```

Các mũi tên trên là trình tự lời gọi **trong IL/ISIL và native**. Điều kiện đi vào,
đường lỗi, timeout và thứ tự thực thi thực tế vẫn chưa rõ. Bằng chứng chi tiết
ở [client-architecture.md](client-architecture.md) và [m3-endpoint-state.md](../analysis/m3-endpoint-state.md).

Một đường gọi khác đã được xác nhận: worker nhận có nhánh bàn giao message
vào collection transport tại `+0xA8`; `FixedUpdate` của component Unity gọi
hàm thao tác trên cùng collection. Chưa xác định điều kiện chọn nhánh này
hay message nào tạo transition đăng nhập/lobby/phòng/trận. Xem
[m3-unity-loop.md](../analysis/m3-unity-loop.md).

| Trạng thái cần khảo sát | Bằng chứng hiện có | Kết luận |
| --- | --- | --- |
| Khởi động và chọn server | Danh sách nhãn tạo các mục callback `6`; handler dùng chỉ số đã chọn để lấy host/port rồi yêu cầu kết nối. Chưa nối với scene hoặc callback Unity | Confirmed về đường callback/kết nối; Inferred về tên màn hình |
| Đăng nhập | Chưa định vị message và phản hồi | Unknown |
| Lobby | Chưa định vị transition hoặc model state | Unknown |
| Phòng | Chưa định vị transition hoặc model state | Unknown |
| Trận | Có tài nguyên map cục bộ từ M1; chưa định vị vòng lặp mô phỏng | Unknown |
| Mất kết nối/thử lại | Ngoài nhiều caller của hàm tạo thread kết nối, case message `0x02` có đường gọi đóng/reset rồi yêu cầu kết nối | Confirmed về đường gọi trong mã; Inferred về ngữ nghĩa reconnect và điều kiện runtime |

Không được dùng bảng này làm đặc tả server. Mỗi transition chỉ được nâng lên
`Confirmed` khi tìm thấy điều kiện chuyển trạng thái, message tương ứng và
chứng cứ đọc được từ mã hoặc kiểm thử hợp lệ, không phụ thuộc server bên thứ ba.
