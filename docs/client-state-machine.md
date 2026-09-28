# Trạng thái client — bản nháp M3

Chưa đủ bằng chứng để vẽ toàn bộ state machine đăng nhập/lobby/phòng/trận.
Phân tích tĩnh hiện đã nối được transport `0xE5/A9` với dispatcher nhận
`0xE2`, xác định một bước định danh/config phiên `0xBB`, và lần từ `0xE2` tới
một transition world/spatial sau khi tải state. Tên lobby/phòng/trận cụ thể
vẫn chưa xác định.

```text
Khởi tạo host/port mặc định hoặc chọn cặp từ danh sách
    ↓ (đường chọn endpoint gọi caller 0x060001C1)
Yêu cầu mở kết nối
    ↓ enqueue 0xBB; tạo thread kết nối; enqueue 0x07 sau 0xBB
Thử kết nối TCP
    ↓ (TcpClient.Connect, rồi GetStream)
Khởi tạo BinaryReader/BinaryWriter
    ↓ (hai worker Thread.Start; FIFO bị gate; gửi trực tiếp client 0xE5)
Nhận server 0xE5: cài prefix-XOR key, shift và mở send-gate
    ↓ send worker drain FIFO: client 0xBB rồi client 0x07
    ├─ server response 0xBB → nạp config + mở rộng menu row 1
    │    ↓ event UI mở panel mode 0/1; submit hai field → client 0xBB lần nữa
    ├─ 0xA9/1 hoặc /2 → reconcile/reset queue → quay lại receive-loop
    └─ 0xA9/0 → callback + đóng/reset socket (không đi tiếp cùng phiên)
    ↓ (packet server thường kế tiếp: direct dispatch hoặc queue +0xA8)
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
                 gửi 0x9E selector 2 từ state client
                         ↓ event entityKey + x/y
                 bỏ qua self; peer lệch vị trí thì đặt correction
                         ↓ (nếu state +0x2DD khác zero)
                 đặt camera theo entity; chuyển world/spatial scene
                         ↓
                 lobby dạng world / phòng chờ / trận: Unknown
```

Các mũi tên trên là trình tự lời gọi **trong IL/ISIL và native**. Điều kiện đi vào,
đường lỗi, timeout và thứ tự thực thi thực tế vẫn chưa rõ. Bằng chứng chi tiết
ở [client-architecture.md](client-architecture.md) và [m3-endpoint-state.md](../analysis/m3-endpoint-state.md).

Worker nhận có hai nhánh bàn giao message thường: gọi listener trực tiếp hoặc
thêm vào collection transport `+0xA8`; `FixedUpdate` của component Unity lấy
phần tử đầu cùng collection và gọi cùng listener. Vì vậy `0xE2` sau handshake
đã có execution edge hoàn chỉnh tới app dispatcher. Chưa xác định điều kiện
chọn direct/queued hoặc message nào định danh lobby/phòng/trận. Xem
[m3-unity-loop.md](../analysis/m3-unity-loop.md).

`0xE5` không trực tiếp chứng minh client đã đăng nhập. Giá trị text-like ở
cuối payload được lưu vào state phiên hoặc dẫn tới message `0xA9`; các nhánh
`0xA9` thao tác cờ, bộ đếm và collection transport. `0xE2` là packet mới từ
server sau khi receive-loop tiếp tục, không phải lời gọi do handler `0xE5`
tự phát sinh. Ba nhánh cache có thể hoàn tất theo thứ tự khác nhau; không được
giả định thứ tự cố định `0xDA → 0xE1 → 0xE0`.

Đường connect còn tạo request `0xBB` gồm UUID/config/byte. Request này được
enqueue trước lúc thread mở socket; command rỗng `0x07` được enqueue sau nó.
`0xE5` bỏ qua FIFO và response của nó mở send-gate, nên thứ tự client trên wire
cho kết nối mới/reset là `0xE5 -> 0xBB -> 0x07`. Response `0xBB` đọc bốn
string, reset dword session/UI `DAT_181454620+0x188`, ghi bốn field cấu hình,
bật `+0x18D`, đồng thời thay row selector `1` của một bảng
`string[][]` từ hai thành bốn mục. Branch `0xBB` không gọi callback hay tự
chuyển màn hình. Event UI về sau mới kiểm tra row có bốn mục và có thể mở một
panel hai-mode, ba action; cấu trúc này phù hợp với account/session ở mức
`Inferred`, còn plaintext label vẫn chưa biết. Action `0x232B` của panel yêu
cầu cả hai text khác rỗng, đóng form rồi gửi `0xBB(text38, text30, mode)`.
Đây là đường submit account/session `Confirmed` về control flow, dù chưa đủ
bằng chứng đặt hai field là username/password hay gọi response là xác thực.
Lần `0xBB` đầu vẫn là bước client/session identity/config trước data
bootstrap. Readiness
`+0x188/+0x189/+0x18A` của `0xE2` thuộc static owner khác
`DAT_1814545E8`; trùng offset không tạo shared state. Client không có gate đã
thấy để ép thứ tự response `0xBB` và server push `0xE2`, nên thứ tự inbound
vẫn `Unknown`. Local server có thể chọn `0xBB -> 0xE2` để lifecycle tuần tự,
nhưng phải giữ nhãn `Inferred`. Xem
[m3-session-bootstrap-transitions.md](../analysis/m3-session-bootstrap-transitions.md).

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
`entityKey + x/y`. Cả sáu direct sender đã tìm được đều phát tọa độ từ
selected/current entity phía client. Handler bỏ qua event nếu key trỏ về chính
entity đó trước khi đọc `x/y`; với entity khác, nếu tọa độ lệch current thì
handler đặt state correction. Vai trò transport vì vậy được suy luận mạnh là
client publication rồi server relay/state replication, không phải
authoritative self-correction; khả năng server validate/clamp vẫn `Unknown`.
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
| Account/session | `0xBB` đầu mang UUID/config/byte và mở menu row `1`; panel hai-mode yêu cầu hai text rồi submit lại `0xBB(text38, text30, mode)`. Response không có status byte. `0x2B` là form chín text riêng | Control flow `Confirmed`; tên field và auth semantic `Unknown` |
| Bootstrap dữ liệu | Packet server `0xE2` đi qua dispatcher chung, điều phối cache hoặc `0xDA/0xE1/0xE0`; barrier ba cờ đặt `appReady` và gửi `0xDB` | Confirmed |
| Hydrate entity / chuyển scene | UI event case `1` khi `appReady` gửi `0x9E/0`; response hydrate entity, chạy placement/grid, có thể đồng bộ `0x9E/2`, tính camera và chuyển world state | Control flow `Confirmed`; world/gameplay `Inferred` |
| Phòng | Chưa định vị transition hoặc model state | Unknown |
| Trận | Có mô phỏng projectile/damage/terrain cục bộ; `0x16/0x54` hydrate hình học rồi có thể pause queue, nhưng chưa có match-start/map/turn transition | Unknown |
| Mất kết nối/thử lại | Ngoài nhiều caller của hàm tạo thread kết nối, case message `0x02` có đường gọi đóng/reset rồi yêu cầu kết nối | Confirmed về đường gọi trong mã; Inferred về ngữ nghĩa reconnect và điều kiện runtime |

### Nhánh mất kết nối đã xác định

Worker nhận khi dừng sẽ phân loại thời lượng kết nối theo ngưỡng 501 ms, gọi
callback trạng thái `1/2`, xóa state và reset transform/stream. Nó không tự gọi
đường mở socket. Ngược lại, case ứng dụng `0x02` đóng/reset rồi gọi thẳng đường
kết nối tới endpoint đang chọn. Do đó reconnect do `0x02` là transition đã
`Confirmed` về control flow; reconnect tự động sau lỗi socket vẫn `Unknown`.

`0x9A` là ứng viên keepalive/no-op server → client: parser chấp nhận nhưng bỏ
khỏi accounting, dispatcher bỏ qua, và không có direct sender phía client trong
128 call-site đã quét. Chưa có bằng chứng về chu kỳ hay timeout khi thiếu nó.
Xem [m3-connection-lifecycle.md](../analysis/m3-connection-lifecycle.md).

Đường server tối thiểu, handshake identity và fixture bootstrap collection
rỗng được tổng hợp tại
[m3-local-login-path.md](../analysis/m3-local-login-path.md). `0xDB` là mốc
server-side để xác nhận client đã hoàn tất bootstrap; vào world qua `0x9E/0`
cần dữ liệu map/entity thật và là phạm vi tiếp theo.

Không được dùng bảng này làm đặc tả server. Mỗi transition chỉ được nâng lên
`Confirmed` khi tìm thấy điều kiện chuyển trạng thái, message tương ứng và
chứng cứ đọc được từ mã hoặc kiểm thử hợp lệ, không phụ thuộc server bên thứ ba.
