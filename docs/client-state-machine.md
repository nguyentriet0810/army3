# Trạng thái client — bản nháp M3

Chưa đủ bằng chứng để vẽ toàn bộ state machine đăng nhập/lobby/phòng/trận.
Tuy nhiên, phân tích tĩnh đã xác nhận được một chuỗi bootstrap từ handler
`0xE2` tới một transition UI sau khi tải state. Tên nghiệp vụ của màn hình
cuối vẫn chưa xác định.

```text
Khởi tạo host/port mặc định hoặc chọn cặp từ danh sách
    ↓ (đường chọn endpoint gọi caller 0x060001C1)
Yêu cầu mở kết nối
    ↓ (0x0600028A tạo thread; 0x0600028C gọi 0x0600028D)
Thử kết nối TCP
    ↓ (TcpClient.Connect, rồi GetStream)
Khởi tạo BinaryReader/BinaryWriter
    ↓ (hai worker Thread.Start)
Nhận 0xE5: cài prefix-XOR key, shift và bật transform
    ↓ (có thể tiếp tục bằng 0xA9 subcommand 0)
Transport transformed / đồng bộ đang chờ hoặc đã sẵn sàng
    ↓ (execution edge tới nguồn 0xE2 vẫn chưa biết)
Nhận 0xE2: so sánh ba cặp version/cache
    ├─ cache mismatch → gửi 0xDA / 0xE1 / 0xE0
    │                    ↓ response tương ứng
    └─ cache match ────→ tải cache cục bộ
                         ↓
                 đặt cờ +0x18A / +0x188 / +0x189
                         ↓ (đủ cả ba)
                 appReady = 1; gửi 0xDB; xóa ba cờ
                         ↓ (UI event case 1, không tự động)
                 gửi 0x9E selector 0
                         ↓
                 hydrate entity keyed + scan placement trên grid
                         ↓ (một đường gửi x/y ứng viên)
                 gửi 0x9E selector 2
                         ↓ event entityKey + x/y
                 so current position, đặt correction nếu khác
                         ↓ (nếu state +0x2DD khác zero)
                 chuyển scene; đích nghiệp vụ còn Unknown
```

Các mũi tên trên là trình tự lời gọi **trong IL/ISIL và native**. Điều kiện đi vào,
đường lỗi, timeout và thứ tự thực thi thực tế vẫn chưa rõ. Bằng chứng chi tiết
ở [client-architecture.md](client-architecture.md) và [m3-endpoint-state.md](../analysis/m3-endpoint-state.md).

Một đường gọi khác đã được xác nhận: worker nhận có nhánh bàn giao message
vào collection transport tại `+0xA8`; `FixedUpdate` của component Unity gọi
hàm thao tác trên cùng collection. Chưa xác định điều kiện chọn nhánh này
hay message nào tạo transition đăng nhập/lobby/phòng/trận. Xem
[m3-unity-loop.md](../analysis/m3-unity-loop.md).

`0xE5` không trực tiếp chứng minh client đã đăng nhập. Giá trị text-like ở
cuối payload được lưu vào state phiên hoặc dẫn tới message `0xA9`; các nhánh
`0xA9` thao tác cờ, bộ đếm và collection transport. Chuỗi từ `0xE2` trở đi
được xác nhận về control flow, nhưng chưa nối ngược được nguồn `0xE2` tới
`0xE5/0xA9`. Ba nhánh cache có thể hoàn tất theo thứ tự khác nhau; không được
giả định thứ tự cố định `0xDA → 0xE1 → 0xE0`.

`0xC4` không nằm trong chuỗi tự động trên: sender của nó chỉ được gọi từ UI
event case `2`, qua một gate one-shot. Hai nhánh response gọi virtual slot
`7`, nhưng target và ý nghĩa vẫn chưa rõ. Chi tiết ở
[m3-length4-commands.md](../analysis/m3-length4-commands.md).

Schema response `0x9E/0` đã được tách theo đúng 19 reader call. Đây là một
record keyed bằng byte đầu chứ không phải danh sách có count; field `i32 == -1`
quyết định có thêm một `i16` cho record con hay không. Xem
[m3-command-9e-selector0.md](../analysis/m3-command-9e-selector0.md).

Hai field cuối của record là tọa độ `x/y`. Client kiểm tra cell grid kích thước
`24`, có thể điều chỉnh `y`, rồi gửi selector `2`. Event selector `2` mang
`entityKey + x/y`; nếu khác current coordinate, handler đặt state correction.
Consumer entity xử lý correction theo kiểu hybrid: bước ngang theo tick có
collision check, có thể căn `y` sau khi hội tụ và sửa sai số mirror nhỏ; đây
không phải teleport thuần. Nhánh nhận không gửi ngược lại, nên vòng mạng kết
thúc tại đây. Xem
[m3-command-9e-selector2.md](../analysis/m3-command-9e-selector2.md).

Command `0x2B` là submit của một form gồm chín text bắt buộc và response chỉ
đọc một byte trước khi gọi callback hiển thị/state. Đã ánh xạ control sang
localization ID, nhưng chưa giải được plaintext label. Đây là ứng viên thuộc
luồng onboarding/account/profile, chưa đủ bằng chứng để gọi là login. Xem
[m3-command-2b.md](../analysis/m3-command-2b.md).

| Trạng thái cần khảo sát | Bằng chứng hiện có | Kết luận |
| --- | --- | --- |
| Khởi động và chọn server | Danh sách nhãn tạo các mục callback `6`; handler dùng chỉ số đã chọn để lấy host/port rồi yêu cầu kết nối. Chưa nối với scene hoặc callback Unity | Confirmed về đường callback/kết nối; Inferred về tên màn hình |
| Đăng nhập | Đã tách transport setup `0xE5/0xA9`; `0x2B` là form chín text; chưa xác nhận command account/session | Unknown |
| Bootstrap dữ liệu | `0xE2` điều phối cache hoặc `0xDA/0xE1/0xE0`; barrier ba cờ đặt `appReady` và gửi `0xDB` | Confirmed từ `0xE2`; nguồn `0xE2` vẫn Unknown |
| Hydrate entity / chuyển scene | UI event case `1` khi `appReady` gửi `0x9E/0`; response hydrate entity, chạy placement/grid, có thể đồng bộ `0x9E/2` rồi chuyển scene | Confirmed về control flow và tọa độ; scene đích Unknown |
| Phòng | Chưa định vị transition hoặc model state | Unknown |
| Trận | Có tài nguyên map cục bộ từ M1; chưa định vị vòng lặp mô phỏng | Unknown |
| Mất kết nối/thử lại | Ngoài nhiều caller của hàm tạo thread kết nối, case message `0x02` có đường gọi đóng/reset rồi yêu cầu kết nối | Confirmed về đường gọi trong mã; Inferred về ngữ nghĩa reconnect và điều kiện runtime |

Không được dùng bảng này làm đặc tả server. Mỗi transition chỉ được nâng lên
`Confirmed` khi tìm thấy điều kiện chuyển trạng thái, message tương ứng và
chứng cứ đọc được từ mã hoặc kiểm thử hợp lệ, không phụ thuộc server bên thứ ba.
