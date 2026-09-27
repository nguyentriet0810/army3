# M3: Vòng đời kết nối, mất kết nối và ứng viên keepalive

Phân tích tĩnh trên bản client đã hash ở M1. Không chạy client và không liên
hệ server bên thứ ba. Các địa chỉ native chỉ đúng với bản client này.

## Mở kết nối

`Confirmed` từ `FUN_18043BEA0`, `FUN_1804DF5A0`, `FUN_1804E2520` và
`FUN_1804E2E00`:

1. Đường gọi connect enqueue `0xBB`, bắt đầu thread kết nối rồi enqueue `0x07`;
   hai message nằm trong FIFO outbound `+0x38` theo đúng thứ tự đó.
2. Client tạo `TcpClient`, gọi kết nối với host/port, lấy stream và tạo
   reader/writer.
3. Client tạo và khởi động hai worker gửi/nhận. Send worker bị chặn cho tới
   khi hai gate `+0x60/+0x61` cùng bật; initializer đã đặt `+0x61 = 1`, còn
   `+0x60` vẫn tắt ở transport mới/reset.
4. Sau khi hai worker đã được khởi động, client lưu tick hiện tại vào field
   transport `+0x80`, xóa byte `+0x31`, tạo command logic `0xE5` và gọi trực
   tiếp serializer/send, bỏ qua FIFO.
5. Response `0xE5` cài key/shift và đặt `+0x60 = 1`; send worker sau đó lấy
   index `0` rồi xóa index `0`, nên phát `0xBB` trước `0x07`.

Vì vậy `0xE5` đầu tiên là message do **client gửi sau khi socket sẵn sàng**.
Response `0xE5` cùng command được worker nhận xử lý riêng để cài key/shift;
đây là hai chiều của bước thiết lập transport, không phải bằng chứng đăng nhập.
Wire order phía client trên kết nối mới/reset là `0xE5 -> 0xBB -> 0x07`.
Server quyết định thời điểm inbound. Response `0xBB` và cache barrier `0xE2`
ghi hai static owner khác nhau, và chưa thấy gate hay direct call giữa chúng;
vì vậy thứ tự inbound vẫn `Unknown`. Local server có thể thử tuần tự
`0xBB -> 0xE2`, nhưng đây là lựa chọn triển khai chứ chưa phải protocol fact.

## Kết thúc worker nhận

`Confirmed` từ `FUN_1804E3D60`:

- Worker lặp khi cờ kết nối `+0x30` còn bật và parser trả về một message.
- Khi vòng lặp kết thúc nhưng cờ kết nối vẫn còn bật, client gọi callback trạng
  thái với giá trị `1` hoặc `2`. Phân nhánh dùng chênh lệch giữa tick hiện tại
  và tick `+0x80`, với ngưỡng `0x1F5` = **501 ms**, đồng thời kiểm tra cờ
  `+0xB1`.
- Client đặt `+0xB0 = 0` và gọi reset transform/stream khi object tương ứng tồn
  tại.
- Worker này **không** gọi `FUN_18043BEA0`, tức đường yêu cầu kết nối mới.

`Inferred`: callback `1/2` phân biệt lỗi rất sớm và lỗi sau khi kết nối đã tồn
tại đủ lâu. Tên callback và phản ứng UI vẫn chưa xác định.

`Confirmed`: không có reconnect tự động ngay trong worker nhận. Một tầng caller
khác hoặc thao tác UI vẫn có thể quyết định kết nối lại sau callback.

## Reconnect do message `0x02`

Case ứng dụng `0x02` không đọc payload trong đoạn đã khảo sát. Nó lần lượt:

1. gọi `FUN_1804E09B0` để đóng object transport hiện tại và reset key/index;
2. gọi `FUN_1804E14F0` để xóa field phiên `+0x30` và đặt `+0xB0 = 0`;
3. gọi `FUN_18043BEA0`, đường lấy endpoint hiện tại rồi yêu cầu mở kết nối.

`Confirmed`: nếu dispatcher nhận command logic `0x02`, client thực hiện một
chu kỳ đóng/reset rồi mở kết nối mới tới endpoint đang chọn.

`Inferred`: `0x02` là tín hiệu reconnect/chuyển phiên do server gửi. Chưa biết
server gửi nó trong tình huống nào, endpoint có bị thay trước đó hay không, và
reconnect thành công sẽ quay lại state UI nào.

## `0xA9` là đồng bộ phiên/queue, không phải timer heartbeat đã thấy

Handler nhận `0xA9` có ba subcommand:

- `0`: xóa `+0xB1`, gọi callback `1/2` theo cùng ngưỡng 501 ms rồi đóng/reset
  transport;
- `1`: đối chiếu bộ đếm với collection message và có thể phát lại phần còn
  thiếu;
- `2`: đặt cờ `+0x61`, xóa hai bộ đếm và clear collection.

Toàn bộ direct xref của helper tạo `0xA9` chỉ cho hai đường gọi:

- handler response `0xE5` tạo subcommand `0` khi cờ phiên `+0xB0` đã bật;
- helper phục hồi collection tạo subcommand `2` khi chỉ số yêu cầu đã tới cuối
  queue.

Không có caller định kỳ/timer trực tiếp tới helper này trong project Ghidra
hiện tại. Vì vậy `0xA9` được phân loại `Confirmed` là đồng bộ transport/queue;
tên heartbeat vẫn không có đủ bằng chứng.

## Bàn giao từ `0xE5/A9` sang `0xE2`

`Confirmed`: đây không phải một direct call giữa hai handler. Sau khi xử lý
riêng `0xE5` hoặc `0xA9`, receive worker quay lại vòng đọc. Packet thường kế
tiếp được `FUN_1804E05E0` bàn giao trực tiếp cho listener hoặc thêm vào queue
`+0xA8`; `FixedUpdate -> FUN_1804E0740` tiêu thụ cùng queue và gọi listener.
Command server `0xE2` sau đó vào branch `0x1802135A8` của app dispatcher.

Nhánh `0xA9/1` và `/2` có thể quay lại receive-loop trên cùng socket. Nhánh
`0xA9/0` đóng/reset transport, nên `0xE2` chỉ có thể đến sau một lần reconnect
và handshake `0xE5` mới. Xem
[m3-session-bootstrap-transitions.md](m3-session-bootstrap-transitions.md).

## Ứng viên `0x9A`

Parser không tăng một bộ đếm cho bốn command `0xE5`, `0xA9`, `0x9A`, `0x83`.
Khác ba command còn lại, worker nhận không có handler riêng cho `0x9A`, và
entry `0x9A` trong dispatcher ứng dụng nhảy về nhánh mặc định.

Script decompile toàn bộ direct xref của constructor message
`FUN_180297C50` thu được **128 call-site trong 127 function**, decompile thành
công cả 127 function. Không call-site nào tạo command `0x9A`.

Kết luận:

- `Confirmed`: không có direct sender `0x9A` qua constructor message chuẩn;
  client không có handler hay response riêng cho `0x9A` trong các đường đã
  khảo sát.
- `Inferred`: `0x9A` phù hợp với một no-op/keepalive một chiều từ server vì nó
  được parser chấp nhận nhưng bỏ khỏi accounting và không bàn giao hành vi ứng
  dụng.
- `Unknown`: server có bắt buộc gửi định kỳ hay không; khoảng thời gian; absence
  có làm server đóng socket hay không. Chưa tìm thấy watchdog phía client tự
  đóng kết nối chỉ vì không nhận `0x9A`.

Do đó server localhost ở M5 chưa nên phát `0x9A` theo suy đoán. Chỉ bổ sung khi
test cô lập hoặc bằng chứng tĩnh khác cho thấy nó cần thiết.

## Bằng chứng tái lập

- `analysis/generated/ghidra/native-targets.log`: mở socket và gửi `0xE5`.
- `analysis/generated/ghidra/m3-outgoing-order.log`: enqueue FIFO, direct send
  `0xE5` và thứ tự caller `0xBB/0x07`.
- `analysis/generated/ghidra/m3-transport-init.log`: collection và gate ban
  đầu của singleton transport.
- `analysis/generated/ghidra/m3-reconnect-targets.log`: worker nhận, `0xA9`,
  đóng/reset và đường kết nối.
- `analysis/generated/ghidra/m3-a9-callers.log`: hai caller của helper `0xA9`.
- `analysis/generated/ghidra/m3-message-constructor-decompile.log`: inventory
  128 direct call-site của constructor message.
- `analysis/generated/ghidra/m3-bootstrap-transition-targets.log`: hai đường
  direct/queued từ receive worker tới app dispatcher.
- `scripts/ghidra/DecompileMessageConstructorCalls.java`: script chỉ đọc dùng
  để tái lập inventory sender.
