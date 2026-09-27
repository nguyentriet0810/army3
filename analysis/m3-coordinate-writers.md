# M3: writer tọa độ entity và đường nối về handler mạng

**Phạm vi:** phân tích tĩnh `GameAssembly.dll` và metadata/field layout do
Cpp2IL khôi phục. Không chạy client và không kết nối server bên thứ ba.

## Layout được theo dõi

`Confirmed (cấu trúc)`: base entity có ba cặp tọa độ 32-bit:

| Offset | Tên làm việc | Vai trò đã thấy |
| --- | --- | --- |
| `+0x84/+0x88` | `currentX/currentY` | tọa độ hiện tại dùng bởi update, collision và sender |
| `+0x1D0/+0x1D4` | `targetX/targetY` | đích di chuyển/correction |
| `+0x298/+0x29C` | `mirrorX/mirrorY` | mirror/anchor dùng bởi placement và reconcile |

Tên trên là tên làm việc, không phải tên gốc. Các field `+0x1B2/+0x1B4` là
snapshot 16-bit liên quan nhưng không thuộc sáu field của phép quét.

## Cách quét và giới hạn

`FindProgramFieldWrites.java` quét toàn listing Ghidra, bỏ write lên stack và
tìm destination operand có sáu displacement trên. Kết quả là **748 write-site
syntactic trong 391 function**, cộng một nhóm instruction chưa thuộc function
Ghidra. Con số này cố ý bao gồm nhiễu: offset `0x84`
hoặc `0x88` xuất hiện trong rất nhiều type của runtime và game, nên một match
đơn lẻ không chứng minh đó là entity.

Phép lọc tiếp theo dùng đồng thời:

1. độ rộng field phải phù hợp với `int32` của layout entity;
2. object phải đến từ entity collection, là instance base/derived đã xác nhận,
   hoặc writer phải chạm một tổ hợp mirror/target đặc trưng;
3. control flow từ entry function phải thực sự tới write-site;
4. với handler mạng, call-site phải nằm trên CFG của command/selector tương
   ứng, không chỉ nằm gần nhau theo địa chỉ.

`ScanRangeForFieldWrites.java` còn quét từng byte trong toàn dispatcher
`0x1801FCAB0..0x1802570DC`. Kết quả **0 inline write**, nên mọi write tọa độ
entity từ dispatcher đều qua helper. Sau đó toàn bộ 391 function ứng viên được
đưa vào `ScanRangeForDirectCalls.java`: có 29 direct call-site; 16 call-site bị
loại vì write byte/qword, pointer field hoặc object layout khác. Còn lại đúng
13 direct call-site tới tám writer entity bên dưới.

Giới hạn: kết quả này bao phủ direct call và inline write trong dispatcher.
Computed/virtual call có thể tồn tại ở nơi khác; kết quả âm không chứng minh
toàn binary không có một đường gián tiếp chưa khôi phục.

## Tám writer có đường từ mạng

| Writer | Field được ghi | Diễn giải cấu trúc |
| --- | --- | --- |
| `FUN_180449540` | target | tra entity theo key/index rồi đặt `targetX/Y` |
| `FUN_180449C50` | current + target | đặt tức thời current và target, kèm snapshot 16-bit |
| `FUN_180448090` | current | tra entity theo key/index rồi đặt `currentX/Y` |
| `FUN_180449900` | target | đặt target, bật pending correction `+0x1D8`, reset `+0x294` |
| `FUN_180519480` | cả sáu | routine khởi tạo/reset; current, target và mirror hội tụ về cùng vị trí |
| `FUN_180519910` | cả sáu | routine placement; chép `x/y` vào current, target, mirror và snapshot |
| `FUN_180525DF0` | current + target | routine cấu hình lớn; lấy hai `i16`, đặt current/target rồi cấu hình mảng A–D |
| `FUN_18041D840` | current | constructor của derived entity; class metadata kế thừa base entity |

`FUN_180519480` có một điều chỉnh `y + 10` ở vài mode trước khi đồng bộ các
mirror. `FUN_180525DF0` còn ghi nhiều state gameplay khác; việc nó cấu hình bốn
mảng A–D không làm mất vai trò đặt tọa độ ban đầu.

## Writer entity cục bộ không được dispatcher gọi trực tiếp

Đối chiếu layout, object source và control flow còn xác nhận các writer entity
sau. Phép quét 391 target không thấy dispatcher direct-call chúng:

| Nhóm | Function | Field chính |
| --- | --- | --- |
| chuẩn bị publication/placement | `FUN_180414150` | mirror |
| update tổng hợp | `FUN_180423620` | cả sáu, theo nhiều nhánh |
| movement/correction | `FUN_180519E30`, `FUN_18051A370`, `FUN_18051A8D0`, `FUN_18051D960` | current, target và/hoặc mirror tùy nhánh |
| movement/reconcile | `FUN_18051F120`, `FUN_18051F650`, `FUN_180524070`, `FUN_180524E70`, `FUN_180532A40` | current/mirror, có nhánh target |
| reset/placement | `FUN_18053C590` | cả sáu |

`Không direct-call` không có nghĩa là độc lập với mạng: một handler có thể gọi
writer khởi tạo rồi update loop tiếp tục qua các routine này, hoặc một helper
khác có thể gọi chúng gián tiếp. Kết quả chỉ xác định ranh giới direct của
dispatcher.

## Ánh xạ command/selector

| Command | Call-site | Writer | Hiệu ứng tọa độ |
| --- | --- | --- | --- |
| `0x15` | `0x18022A3E2` | `FUN_180449540` | đặt target của entity keyed từ hai `u16` |
| `0xC0` | `0x18022AB46` | `FUN_180449540` | cùng dạng target update |
| `0x35` | `0x18022ADA5` | `FUN_180449C50` | đặt current + target từ key và hai `i16` |
| `0x16` / `0x54` | `0x18022D28F` | `FUN_180525DF0` | hydrate/config; đặt current + target từ hai `i16` |
| `0x18` | `0x18022E2B3` | `FUN_180448090` | đặt current từ key và hai `i32` |
| `0x59` | `0x180232A2B` | `FUN_180519480` | khởi tạo/reset cả sáu field |
| `0xC1` | `0x18024479B` | `FUN_180519480` | khởi tạo/reset cả sáu field |
| `0xC1` | `0x180244ED4` | `FUN_180519910` | placement lại cả sáu field |
| `0x9E/0` | `0x18024BCD2`, `0x18024BF95`, `0x18024C079` | `FUN_180519910` | placement cả sáu field trong hydrate selector `0` |
| `0x9E/2` | `0x18024CD93` | `FUN_180449900` | target correction cho peer; self bị lọc trước đó |
| `0x9E/10` | `0x180250E89` | `FUN_18041D840` | dựng derived entity với current `x/y` |

Hai entry `0x16/0x54` dùng chung code nên chỉ có một call-site. Ba call-site
của selector `0` là các đường điều kiện khác nhau trong cùng một hydrate.

`Confirmed`: jump table con `0x9E` nằm tại `0x18025709C`, có 16 selector.
Selector `10` đi qua stub tới `0x1802506BD`; CFG 330 instruction tới call
`0x180250E89`. Constructor nhận hai signed word từ payload làm tham số ghi
`+0x84/+0x88`, rồi object được đưa vào collection riêng. Metadata xác nhận
class được dựng kế thừa chính base entity chứa sáu field, nên đây không phải
trùng displacement của type không liên quan.

## Các match trực tiếp bị loại

16 direct call-site còn lại không phải writer của sáu field entity:

- `FUN_1801961E0`, `FUN_180419AF0`, `FUN_180556070`, `FUN_180557F60` ghi
  byte tại offset trùng;
- `FUN_18027D8D0`, `FUN_18029E340`, `FUN_1804169B0`, `FUN_1804ED2A0`,
  `FUN_180504A20` ghi qword/pointer tại offset trùng;
- `FUN_18040EEA0` dùng `+0x84` là int nhưng `+0x88` là byte trên layout khác;
- `FUN_1802EE860` có một cặp write 32-bit `+0x84/+0x88`, nhưng object đến từ
  static field `+0xE8` của manager, trong khi chính owning object dùng `+0x88`
  làm pointer. Không có target/mirror hoặc bằng chứng kế thừa entity, nên đây
  được phân loại là object tọa độ khác, không phải sáu field đang theo dõi.

Việc ghi rõ các match bị loại là cần thiết: chỉ quét chuỗi `+0x84/+0x88` sẽ
gán nhầm nhiều UI/container/runtime object thành player/entity.

## Kết luận cho ranh giới client-server

- `Confirmed`: server response có nhiều đường đặt vị trí ban đầu hoặc cập nhật
  trực tiếp (`0x16/0x54`, `0x18`, `0x35`, `0x59`, `0xC1`, `0x9E/0`,
  `0x9E/10`). Vì vậy local server phải duy trì ít nhất key/index entity và vị
  trí spawn/hydrate; chỉ mô phỏng relay `0x9E/2` là chưa đủ.
- `Confirmed`: `0x15/0xC0` chỉ đổi target; client giữ trách nhiệm tiến current
  về target trong update loop.
- `Confirmed`: `0x9E/2` vẫn là trường hợp riêng: client phát tọa độ của
  selected/current entity, response lọc self và chỉ correction peer.
- `Inferred`: protocol dùng mô hình lai: server cung cấp/hydrate state và có
  các command sửa vị trí, còn client thực hiện nội suy/collision/movement cục
  bộ và publish một phần state.
- `Unknown`: command `0x18/0x35` có được server dùng để correction chính người
  chơi hay chỉ cho spawn/teleport/event; phân tích tĩnh chưa cho biết điều kiện
  runtime hoặc chính sách validation phía server.

## Tái lập

Các script read-only được lưu trong `scripts/ghidra/`:

- `FindProgramFieldWrites.java`: inventory write-site toàn listing;
- `ScanRangeForFieldWrites.java`: kiểm tra inline write trong dispatcher;
- `ScanRangeForDirectCalls.java`: đối chiếu writer với direct call-site;
- `MapTargetsToJumpTableCases.java`: nối call-site tới outer command và báo
  các computed jump chưa giải;
- `TracePseudoReachability.java`: chứng minh đường CFG từng command/selector;
- `InspectJumpTable.java`: giải bảng selector con `0xC1` và `0x9E`.

Log sinh tự động nằm trong `analysis/generated/ghidra/` và bị Git ignore. Các
log chính là `coordinate-field-writes.log`,
`coordinate-all-writers-callscan.log`, `coordinate-handler-inline-writes.log`,
`coordinate-command-paths.log`, `case9e-jump-table.log` và
`case9e-selector10-coordinate.log`.
