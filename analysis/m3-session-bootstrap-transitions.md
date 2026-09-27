# M3: Từ session bootstrap tới world state

Phân tích tĩnh trên client đã hash ở M1. Không chạy client và không liên hệ
server bên thứ ba. Tên hàm/địa chỉ native chỉ đúng cho bản client này.

## Kết luận ngắn

Không có lời gọi trực tiếp `0xE5/A9 -> 0xE2`. Ranh giới đã xác nhận là ranh
giới **protocol**: handler đặc biệt của transport xử lý `0xE5` hoặc `0xA9`,
trả về receive-loop, rồi một packet server mới có logical command `0xE2` được
bàn giao qua dispatcher chung. Vì `0xE2` là input từ socket, call graph tĩnh
không thể có một producer nội bộ tương đương lời gọi handler `0xE2`.

Chuỗi chắc chắn nhất hiện tại là:

```text
đường connect enqueue client 0xBB
  -> khởi động thread kết nối
  -> enqueue client 0x07 sau 0xBB
socket ready
  -> client 0xE5 được gửi trực tiếp, bỏ qua FIFO
  -> server 0xE5: cài key/shift, bật transform và mở send-gate
  -> send worker drain FIFO: client 0xBB rồi client 0x07
  -> inbound sau đó không có thứ tự cục bộ đã xác nhận:
       - response 0xBB: reset state UI/session + nạp config/menu phiên
       - 0xA9/1 hoặc /2, nếu có: đồng bộ queue rồi trở lại receive-loop
       - server 0xE2: ba version/cache byte
  -> 0xDA / 0xE1 / 0xE0 hoặc cache cục bộ
  -> đủ ba readiness flag: appReady=1, client gửi 0xDB
  -> UI event case 1: client gửi 0x9E/0
  -> hydrate entity + placement/camera -> world/spatial scene
```

`0xA9/0` là ngoại lệ quan trọng: nhánh này gọi callback lỗi/trạng thái rồi
đóng/reset transport. Vì vậy cùng socket không thể đi tiếp từ `0xA9/0` sang
`0xE2`; nếu sau đó có `0xE2` thì phải qua một kết nối mới và một lần `0xE5`
mới.

## Execution edge thực của `0xE5/A9 -> 0xE2`

`Confirmed` từ `FUN_1804E3D60`, `FUN_1804E05E0`, `FUN_1804E0740` và app
dispatcher `FUN_1801FCAB0`:

1. Receive worker xử lý riêng command `0xE5`, `0xA9`, `0x83` rồi quay lại
   vòng đọc packet.
2. Message thường kế tiếp, gồm logical `0xE2`, đi vào `FUN_1804E05E0`.
3. Hàm này hoặc gọi listener transport trực tiếp qua `FUN_180004250`, hoặc
   thêm message vào collection transport `+0xA8`.
4. `FixedUpdate -> FUN_1804E0740` lấy phần tử đầu collection `+0xA8`, gọi
   cùng listener rồi xóa phần tử.
5. Listener ứng dụng là method `0x060006DC`, native `FUN_1801FCAB0`; entry
   jump-table của command `0xE2` đi tới `0x1802135A8`.

Điều kiện chọn dispatch trực tiếp hay qua Unity queue vẫn `Unknown`, nhưng hai
đường cùng hội tụ tại một listener. Do đó việc triển khai server localhost
sau này phải coi `0xE2` là packet server chủ động gửi sau khi transport đã
sẵn sàng, không phải response được client tự tạo từ handler `0xE5`.

## `0xBB`: định danh/config phiên, chưa phải login đã xác nhận

`Confirmed` về request:

- `FUN_1803151B0` tạo command `0xBB` với payload
  `[string][string][byte]`.
- Đường connect `FUN_18043BEA0` đọc hoặc tạo một UUID 16 byte trong
  `UnityEngine.PlayerPrefs`, chỉnh các bit version/variant, format và lưu nó;
  sau đó gọi sender `0xBB` với UUID, một chuỗi cấu hình/localized khác và byte
  `1`.
- Cùng sender còn có caller UI `FUN_180459240`, lấy hai text từ control và
  một byte state. Ý nghĩa đường UI này vẫn chưa rõ.
- Sau khi yêu cầu mở kết nối, `FUN_18043BEA0` còn tạo command rỗng `0x07`.
  Response `0x07` về nhánh default của app dispatcher, nên đây là message một
  chiều trong phạm vi handler đã khảo sát.

`Confirmed` về response `0xBB` tại branch `0x1802430B8`:

- đọc đúng bốn string length-prefixed;
- ghi dword `0` tại `+0x188` của static owner session/UI
  `DAT_181454620`;
- tách string 1 và 3 qua cùng delimiter lấy từ localization ID `0xC9`, rồi
  lưu kết quả vào `+0x198` và `+0x190`;
- lưu nguyên string 2 và 4 vào `+0x1A8` và `+0x1A0`;
- đặt byte state chung `+0x18D = 1`;
- thay hàng selector `1` của một bảng `string[][]` tĩnh bằng `string[4]`:
  hai phần tử đầu lấy từ hai bảng text có sẵn, hai phần tử sau lấy từ
  localization ID `0x263` và `0x8A1`.

Không có callback, virtual call hay routine chuyển màn hình ở cuối branch
`0xBB`: sau phép gán hàng `string[4]`, control flow nhảy thẳng về epilogue của
dispatcher. Bảng trên được khởi tạo sẵn bởi `FUN_1801A7070`; trước response,
hàng selector `1` chỉ có hai phần tử. Vì vậy tác động UI trực tiếp của `0xBB`
là **mở rộng một hàng menu từ 2 lên 4 lựa chọn**, không phải tự chuyển scene.

Phép ghi trên **không** xóa ba readiness flag của cache barrier. Ba flag
`+0x188/+0x189/+0x18A` mà `0xE2` và `0xDA/0xE1/0xE0` dùng thuộc static owner
khác, `DAT_1814545E8`. Trùng offset giữa hai type từng tạo ra một liên hệ giả;
native code cho thấy chúng có hai type-info slot và hai vùng static fields
riêng. Response không có status success/failure đã thấy và không có lời gọi
thẳng sang handler `0xE2` hoặc callback UI.

`Inferred`: `0xBB` là bootstrap định danh client/installation và cấu hình
phiên hoặc menu trước khi tải dữ liệu ứng dụng. Không gọi nó là username/
password login. `Unknown`: string thứ hai, bốn string response, delimiter
thực tế và plaintext của bốn lựa chọn menu.

## Consumer UI sau response `0xBB`

`Confirmed`:

- `FUN_1801A2FE0` và `FUN_180419AF0` đều đọc bảng `string[][] +0x48`, chọn
  đúng hàng selector `1` và kiểm tra `row.Length == 4`;
- khi điều kiện này đúng, các nhánh UI tương ứng mới gọi
  `FUN_1801A4360(mode)` với mode `0` hoặc `1`;
- wrapper trên gọi `FUN_180458420(mode)`; routine đích lại reset dword
  `+0x188`, lưu mode vào `+0x18C`, dựng tiêu đề từ localization và tạo một
  panel có ba action/widget;
- không routine nào trong chuỗi này gửi `0xE2`; việc mở panel là hậu quả của
  một event UI về sau, không phải callback đồng bộ từ response `0xBB`.

Do các nhãn localization chưa được giải ra plaintext, tên màn hình chính xác
vẫn `Unknown`. Cấu trúc và vị trí trước data bootstrap cho phép gọi nó là
**panel lựa chọn account/session hai-mode, ba action** ở mức `Inferred`.
Không có đủ bằng chứng để gọi nó là lobby, danh sách phòng hay màn hình vào
trận. Kết luận quan trọng cho server localhost là: response `0xBB` chỉ làm
đủ dữ liệu để event UI mở panel này; server không cần và không nên chờ một
"UI callback 0xBB" riêng trên wire.

## Thứ tự outbound đầu phiên

`Confirmed` cho một transport mới hoặc vừa reset:

1. `FUN_18043BEA0` gọi sender `0xBB` trước khi yêu cầu mở kết nối, nên message
   được thêm vào collection outbound `+0x38`.
2. Hàm này khởi động đường kết nối bất đồng bộ rồi gọi sender `0x07`; `0x07`
   được thêm sau `0xBB` vào cùng collection.
3. `FUN_1804E1620` tạo singleton transport và các collection, đồng thời đặt
   gate `+0x61 = 1`. Gate `+0x60` của object mới vẫn bằng `0`.
4. Send worker `FUN_1804E2520` chỉ lấy phần tử index `0`, xóa index `0` và gửi
   khi cả `+0x60` lẫn `+0x61` đều khác `0`; collection vì vậy được tiêu thụ
   theo FIFO.
5. Sau khi socket và hai worker sẵn sàng, `FUN_1804DF5A0` gọi thẳng
   `FUN_1804E02F0` để phát `0xE5`, không đi qua FIFO.
6. Handler response `0xE5`, `FUN_1804E2E00`, cài transform rồi đặt
   `+0x60 = 1`. Khi đó worker mới được phép drain `0xBB`, rồi `0x07`.

Do đó wire order phía client là **`0xE5 -> 0xBB -> 0x07`**, dù thứ tự tạo
object là `0xBB`, bắt đầu connect, rồi `0x07`. Kết luận này không phụ thuộc
việc thread kết nối chạy trước hay sau lúc enqueue `0x07`: `0xBB` luôn đứng
trước trong FIFO và FIFO chưa mở trước response `0xE5`.

Không tìm thấy local gate, shared flag hay direct call buộc `0xE2` phải chờ
response `0xBB`. Hai handler ghi vào hai static owner khác nhau:

```text
response 0xBB -> DAT_181454620 +0x188/+0x18D/...  (session/UI)
server 0xE2   -> DAT_1814545E8 +0x188/+0x189/+0x18A (cache barrier)
```

Vì vậy phân tích tĩnh **không xác định được thứ tự inbound thực tế** giữa hai
packet; kết quả đúng hiện tại là `Unknown`, không phải partial order bắt buộc.
Local server có thể chọn trả `0xBB` trước rồi mới push `0xE2` để có lifecycle
tuần tự, dễ kiểm thử, nhưng đó là quyết định triển khai `Inferred`, không phải
yêu cầu đã chứng minh từ client. Capture cô lập hoặc test server localhost mới
có thể nâng thứ tự này lên `Confirmed`.

## Ranh giới account/session, lobby, phòng và trận

| Giai đoạn | Bằng chứng hiện có | Kết luận |
| --- | --- | --- |
| Transport session | client gửi `0xE5`; server `0xE5` cài transform; `0xA9` đồng bộ queue hoặc đóng phiên | `Confirmed` |
| Client/session identity | `0xBB` mang UUID/config/byte; response reset dword session/UI `DAT_181454620+0x188`, nạp bốn string, bật `+0x18D` và thay menu row `1` từ 2 thành 4 mục | Cấu trúc `Confirmed`; tên nghiệp vụ `Inferred` |
| Panel account/session | Event UI về sau kiểm tra row `1` có 4 mục rồi mở panel hai-mode, ba action; response `0xBB` không tự gọi callback | Cấu trúc `Confirmed`; tên màn hình `Inferred` |
| Data bootstrap | server `0xE2` điều phối cache hoặc `0xDA/0xE1/0xE0`; barrier gửi `0xDB` | `Confirmed` |
| Account authentication | Chưa có command với schema credentials + response success/failure được nối chắc chắn | `Unknown` |
| Lobby | Chưa có transition hoặc model danh sách phòng đã định danh | `Unknown` |
| Room | Chưa có create/join/leave và room-state command đã định danh | `Unknown` |
| Spatial world/gameplay | `0x9E/0` hydrate entity/tọa độ, chạy grid placement, tính camera theo entity và đặt global mode `10` | Control flow `Confirmed`; world/gameplay `Inferred` |
| Active simulation candidate | `0x16/0x54` hydrate tọa độ và bốn mảng hình học được consumer projectile/damage/terrain dùng; sau đó có thể bật `dispatchPause` | Cấu trúc `Confirmed`; không phải bằng chứng match-start |
| Match start | Chưa có condition/message bắt đầu trận, map ID, turn seed hoặc spawn roster được nối thành chuỗi | `Unknown` |

Routine cuối của `0x9E/0`, `FUN_180419570`, dùng current entity `x/y` để tính
camera/offset, đặt global mode byte thành `10` rồi dựng UI/world state. Điều
này mạnh hơn một transition menu thuần và được phân loại `Inferred` là đi vào
một scene không gian/gameplay. Nó vẫn chưa đủ để phân biệt **lobby dạng world**,
**phòng chờ có avatar**, hay **trận đang chạy**. Số `10` không được dùng làm
tên state nếu chưa tìm được enum/consumer có ngữ nghĩa.

Đối chiếu thêm cho thấy global mode `10` cũng được ghi trong routine cập nhật
entity/movement, nên nó là mode world/camera/render dùng lại chứ không phải
marker duy nhất của “trận bắt đầu”. Tương tự, `0x16/0x54` có thể bật byte
`dispatchPause` làm `FixedUpdate` tạm ngừng drain queue `+0xA8`, nhưng byte
này có nhiều writer bật/tắt ở UI/game. Hai dấu hiệu đều xác nhận ranh giới
world/simulation, không đủ để đặt nhãn lobby, room hay match-start.

## Hệ quả cho local compatibility server

Chưa nên đặc tả một chuỗi duy nhất `login -> lobby -> room -> match`. Phần có
thể đưa sang M4 trước là partial order:

1. nhận client `0xE5` và trả response `0xE5` để mở send-gate;
2. sau response đó, chờ client `0xBB` rồi client `0x07` theo FIFO;
3. không gửi tiếp trên socket sau `0xA9/0`;
4. nên trả response `0xBB` trước khi chủ động gửi `0xE2` để lifecycle local
   tuần tự và dễ kiểm thử; đây là lựa chọn `Inferred`, không phải gate hay
   shared-state dependency đã xác nhận;
5. server chủ động gửi `0xE2` để bắt đầu kiểm tra ba cache;
6. chờ client tải cache/request và gửi `0xDB` trước khi xem bootstrap hoàn
   tất;
7. `0x9E/0` là request do UI phát sinh sau `appReady`, không phải bước tự động
   của transport.

## Chứng cứ tái lập

- `analysis/generated/ghidra/m3-bootstrap-transition-targets.log`: receive
  handoff, queue `+0xA8`, `FixedUpdate` drain và listener.
- `analysis/generated/ghidra/m3-login-candidates.log`: sender `0xBB`.
- `analysis/generated/ghidra/m3-login-candidate-callers.log`: UUID/
  `PlayerPrefs`, connect path và caller UI.
- `analysis/generated/ghidra/m3-casebb-cfg.log`, `m3-casebb-windows.log` và
  `m3-casebb-missing-window.log`: bốn reader và field writes của response
  `0xBB`.
- `analysis/generated/ghidra/m3-bb-ui-state-accesses.log`,
  `m3-bb-ui-consumers.log` và `m3-bb-string-table-consumers.log`: kiểu
  `string[][]`, phép thay row selector `1`, các consumer `row.Length == 4`
  và đường event UI tới panel hai-mode/ba action.
- `scripts/ghidra/InspectNativeTargets.java` với target
  `1801A4360/180458420`: wrapper mode và routine dựng panel; chạy read-only
  trên project Ghidra đã có.
- `analysis/generated/ghidra/e1-ready-consumers.log`: barrier đọc đủ ba byte
  readiness từ static owner `DAT_1814545E8`, gửi `0xDB` rồi xóa chúng; đối
  chiếu với owner `DAT_181454620` của response `0xBB` để loại liên hệ giả do
  trùng offset.
- `analysis/generated/ghidra/m3-connect-followup-sender.log`: sender rỗng
  `0x07` sau yêu cầu kết nối.
- `analysis/generated/ghidra/m3-outgoing-order.log`: interface sender, FIFO
  outbound, direct send `0xE5` và đường connect tạo `0xBB/0x07`.
- `analysis/generated/ghidra/m3-send-gate-handlers.log` và
  `m3-send-gate61-writers.log`: hai gate của worker và writer response
  `0xE5`/đồng bộ phiên.
- `analysis/generated/ghidra/m3-transport-init.log`: khởi tạo singleton,
  collection outbound `+0x38`, inbound `+0xA8` và gate `+0x61 = 1`.
- `analysis/generated/ghidra/m3-ui-transition-targets.log`: camera/world
  transition của `FUN_180419570`.
- `analysis/generated/ghidra/m3-case16-post-config.log` và
  `m3-case16-ready-flag.log`: điều kiện bật `dispatchPause` sau `0x16/0x54`.
- `analysis/generated/ghidra/m3-world-mode-writers.log`: mode `10` còn được
  dùng trong routine cập nhật entity/movement.

Các log là output sinh tự động và bị Git ignore. Script Ghidra chạy với
`-process GameAssembly.dll -noanalysis -readOnly`.
