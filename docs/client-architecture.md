# Kiến trúc client — M3 (đang khảo sát)

Tài liệu này chỉ dựa trên file client và IL do Cpp2IL khôi phục. Không chạy
client, không kết nối server bên thứ ba. `Confirmed` nghĩa là có thể kiểm tra
trực tiếp trong metadata hoặc output IL; nó không khẳng định nhánh mã đó đã chạy
trong một phiên game thực tế.

## Bằng chứng và cách tái lập

- Metadata và type: [báo cáo M2](../analysis/il2cpp-tooling.md).
- Cpp2IL `dll_il_recovery` được chạy bằng
  `./scripts/run-cpp2il.ps1 -OutputAs dll_il_recovery`.
- Truy vết lời gọi/chuỗi bằng
  [inspect-il-calls.ps1](../scripts/inspect-il-calls.ps1); các TSV sinh ra nằm ở
  `analysis/generated/m3/` và bị Git bỏ qua.
- Các token method dưới đây là token của `Assembly-CSharp.dll` **đã khôi phục**,
  không phải địa chỉ trong `GameAssembly.dll`.

## Đường kết nối tìm được

Type ứng viên transport là type duy nhất của `Assembly-CSharp` có đồng thời
field tĩnh `TcpClient`, `NetworkStream`, `BinaryReader` và `BinaryWriter`.
Tên type bị làm rối; xem đường dẫn và dòng 63–67 trong báo cáo M2.

| Bước | Bằng chứng trong IL khôi phục | Mức chắc chắn |
| --- | --- | --- |
| Gọi phương thức tạo thread kết nối | Method `0x060001C1` thuộc type khác gọi `0x0600028A`; hai method khác trong type transport cũng gọi `0x0600028A` | Confirmed trong IL khôi phục; hoàn cảnh gọi chưa rõ |
| Tạo thread | `0x0600028A` nhận `(string, int)` và lấy function pointer (`ldftn`) tới `0x0600028C` | Confirmed trong IL khôi phục |
| Wrapper gọi kết nối | `0x0600028C` gọi `0x0600028D` tại IL offset `0x02AC` | Confirmed trong IL khôi phục |
| Mở socket | `0x0600028D` nhận `(string, int)`; `newobj TcpClient::.ctor` ở `0x0043`, `TcpClient::Connect` ở `0x00C4` | Confirmed trong IL và ISIL; Connect nhận hai tham số `(string, int)` |
| Chuẩn bị I/O | Cùng method gọi `GetStream` ở `0x012D`, tạo `BinaryReader` ở `0x01CD` và `BinaryWriter` ở `0x0273` | Confirmed trong IL khôi phục |
| Khởi động worker | Cùng method gọi `Thread::Start` hai lần, tại `0x036F` và `0x0467` | Confirmed trong IL; native xác nhận hai worker gửi/nhận |

Chuỗi tóm tắt (không biểu diễn mọi nhánh điều kiện):

```text
caller 0x060001C1 hoặc caller nội bộ
  → tạo thread 0x0600028A
  → wrapper 0x0600028C
  → kết nối 0x0600028D
  → TcpClient.Connect → GetStream → BinaryReader/BinaryWriter
  → hai worker thread (đường gửi và đường nhận, theo native)
```

`0x0600028D` là điểm vào mạng quan trọng đầu tiên. Việc hai caller nội bộ gọi
`0x0600028A` **có thể** liên quan đến thử lại kết nối, nhưng không đủ bằng
chứng để gọi đó là reconnect. Handler message có thêm case byte `0x02`
gọi đường đóng/reset rồi gọi caller yêu cầu kết nối `FUN_18043bea0`;
đây là đường reconnect trực tiếp đã xác nhận về control flow. Worker nhận khi
kết thúc chỉ gọi callback trạng thái và reset, không tự mở socket mới. `0x9A`
là ứng viên keepalive/no-op một chiều nhưng chưa có sender client hay watchdog;
chi tiết ở [vòng đời kết nối](../analysis/m3-connection-lifecycle.md) và
[báo cáo dispatch](../analysis/m3-message-dispatch.md). Điều kiện runtime để
server phát `0x02` vẫn chưa biết. Chưa thấy bằng chứng xác nhận heartbeat hai
chiều hoặc chu kỳ keepalive bắt buộc.

Đối chiếu native cho thấy callback thứ nhất xử lý hàng đợi gửi qua `BinaryWriter`, callback thứ hai đọc message qua `BinaryReader`. Cả hai có lời gọi sleep `5`, nhưng chưa thể gọi đó là heartbeat. Chi tiết xem báo cáo transport native.

## Điểm khởi tạo và vòng đời Unity

`Assembly-CSharp` có bốn type trực tiếp kế thừa `MonoBehaviour` trong output
`diffable-cs`. Trong số đó có các tên method Unity còn nguyên như `Awake`,
`Start`, `Update`, `FixedUpdate`, `OnApplicationQuit`. Đây là **Confirmed** về
chữ ký type/method, không chứng minh thứ tự thực thi hoặc scene chứa chúng.
Đã nối `FixedUpdate` `0x06000373` của một component ứng viên main loop tới
method transport `0x06000297`, và đối chiếu native call tương ứng. Method
transport này thao tác trên một collection tại field tĩnh `+0xA8`. Worker
nhận cũng có nhánh bàn giao message vào cùng collection; xem
[báo cáo Unity loop](../analysis/m3-unity-loop.md). Chưa nối được callback
Unity tới caller kết nối `0x060001C1`, hoặc xác định scene và thời điểm
component được tạo. Field transport `+0x20` có type interface nhận message;
method triển khai `0x060006DC` là ứng viên handler cấp ứng dụng, nhưng chưa
giải được ý nghĩa các nhánh của nó. Đã xác định bảng nhảy theo byte lệnh
trong [báo cáo dispatch](../analysis/m3-message-dispatch.md). Hook
`BeforeSceneLoad` hiện thấy thuộc
`AndroidBridge`, không nên coi là bootstrap của game logic.

## Tài nguyên, mô phỏng và ranh giới server

- **Confirmed:** M1 đã tìm thấy một số tệp và ảnh liên quan bản đồ trong các
  archive `res_x*.zip`; xem [m1-findings.md](../analysis/m1-findings.md).
- **Unknown:** tài nguyên nào được load ở từng scene và dữ liệu nào do server
  gửi sau kết nối.
- **Confirmed:** client có một phép tính khoảng cách giữa hai cặp tọa độ
  nguyên và một đường cập nhật tọa độ cục bộ. Hai entry message
  `0x16/0x54` chia sẻ nhánh đọc các giá trị 16-bit từ buffer để điền
  mảng `short[][]` được đường cấu hình object tọa độ sử dụng; xem
  [khảo sát hai entry](../analysis/m3-case16-54-arrays.md) và
  [ranh giới mô phỏng](../analysis/m3-simulation-boundary.md). Một
  consumer lấy từng cặp mảng con theo chỉ số, tạo object hình học và
  thêm vào `ArrayList`; chưa xác định nó được gọi theo frame hay sự
  kiện nào. Hai virtual call tiếp theo đã được nối tới một sibling
  override có hai nhánh duyệt collection, nhưng chưa thấy đường gọi
  trực tiếp tới transport gửi. Cả 11 computed call của consumer hiện
  đã được phân loại thành sibling override hoặc thao tác collection;
  xem
  [khảo sát virtual dispatch](../analysis/m3-virtual-dispatch.md).
- **Confirmed:** hai mảng sau C/D được ghép thành danh sách point có thứ tự
  và được consumer khác duyệt tuần tự. Client còn có một vòng update
  projectile dùng số học riêng; nó kiểm tra vùng projectile/player, trừ
  damage tại field projectile `+0x68` khỏi HP hiện tại của player
  (`+0x17C`) và xử lý nhánh HP về 0. HP tối đa nằm ở `+0x180`.
  Xem [đường projectile, damage và địa hình](../analysis/m3-projectile-damage-terrain.md).
- **Inferred:** C/D là waypoint/path cho chuyển động hoặc trình diễn.
- **Confirmed (cấu trúc):** `0x06000A62 -> 0x0600080B -> 0x060005B8`
  đọc một stamp ảnh rồi ghi `0`/màu thay thế vào `int[]` mask quanh tọa độ
  va chạm. Đây là bằng chứng client biến đổi mask cục bộ; ngữ nghĩa tạo hố/
  thay đổi địa hình được xếp **Strongly inferred**. Các helper ghi `Texture2D`
  đã kiểm tra riêng vẫn chỉ là đường recolor/crop tài nguyên.
- **Confirmed (native):** đường update
  `0x060007C0 -> 0x06000B67 -> 0x06000A62` duyệt collection object rồi đi
  tiếp vào phép sửa mask trên. Cạnh thứ hai bị thiếu trong IL khôi phục nhưng
  có direct call tại `0x180409CD6`.
- **Confirmed (cấu trúc):** một đường batch setup
  `0x060007AF -> 0x060007EC -> 0x060001F6 -> 0x06000407` đặt HP hiện tại
  và HP tối đa từ dữ liệu mảng. Chưa nối được entry này với command mạng.
- **Confirmed (cấu trúc):** HP còn có state nội suy gồm target `+0x184`, cờ
  `+0x37C` và bước `+0x3A8`. Setter công khai `0x0600044A` thiết lập target;
  `0x0600044B` chạy trong update entity và kéo current HP về target. Chưa thấy
  direct call/`ldftn` tới setter này, và message dispatcher không truy cập trực
  tiếp các field HP. Hai data reference của setter chỉ thuộc `.pdata` và một
  dãy code pointer trong `.data`, chưa phải bằng chứng callback; hiện chưa có
  execution edge chứng minh setter chạy, nên nguồn cập nhật gián tiếp vẫn
  chưa biết.
- **Unknown:** server có xác nhận hoặc ghi đè hit/HP/địa hình hay không.
  Không thấy Unity Physics API vẫn không đủ để xác định thẩm quyền.
- **Confirmed (codec command):** khi transform bật, client giải
  `logical = (raw XOR key[recvIndex]) - shift` theo modulo 256; chiều nghịch
  là `raw = (logical + shift) XOR key[recvIndex]`. Vì vậy `0x16/0x54` không
  có raw byte cố định nếu chưa biết state khóa của phiên.
- **Confirmed:** port khởi tạo là `19150`, nhưng có nhiều đường ghi đè host/port trước kết nối; xem [báo cáo endpoint](../analysis/m3-endpoint-state.md).
- **Confirmed (một phần handshake/framing):** `0xE5` cài prefix-XOR key,
  shift và bật transform, sau đó đọc một giá trị length-prefixed; `0xA9`
  thao tác cờ/bộ đếm/collection transport. Năm command
  `0x88/0xA4/0xC4/0xD7/0xE1` dùng outer length 4 byte. Handler `0xE2` so
  sánh ba cặp version/cache: cache mismatch gửi request rỗng
  `0xDA/0xE1/0xE0`, cache match tải dữ liệu cục bộ; cả hai đường đều đặt một
  trong ba cờ `+0x18A/+0x188/+0x189`. Barrier đủ ba cờ đặt `appReady`, gửi
  `0xDB` rồi xóa cờ. Xem
  [m3-length4-commands.md](../analysis/m3-length4-commands.md).
- **Confirmed (handoff sau handshake):** handler đặc biệt `0xE5/A9` quay lại
  receive-loop. Packet thường kế tiếp, gồm server `0xE2`, được bàn giao thẳng
  hoặc qua queue `+0xA8`; `FixedUpdate` drain queue và gọi cùng app listener.
  `0xA9/0` đóng/reset transport nên không thể đi tiếp tới `0xE2` trên cùng
  socket; `/1` và `/2` có thể. Xem
  [m3-session-bootstrap-transitions.md](../analysis/m3-session-bootstrap-transitions.md).
- **Confirmed (client/session bootstrap):** sender `0xBB` ghi hai string và
  một byte. Đường connect dùng UUID lưu trong PlayerPrefs làm string đầu;
  response đọc bốn string, reset dword session/UI
  `DAT_181454620+0x188`, ghi state `+0x198/+0x1A8/+0x190/+0x1A0`, đặt
  `+0x18D=1` và thay row selector `1` của bảng `string[][]` từ hai thành bốn
  mục. Branch không gọi callback UI.
  Event UI sau đó mới kiểm tra `row.Length == 4` và có thể mở một panel
  hai-mode, ba action. Action submit yêu cầu hai text khác rỗng, đóng panel
  rồi gửi lại `0xBB(text38, text30, mode)`. Control flow account/session này
  là `Confirmed`; plaintext label và việc hai field có đúng là username/
  password vẫn `Unknown`.
- **Confirmed (outbound đầu phiên):** đường connect enqueue `0xBB`, khởi động
  thread kết nối rồi enqueue `0x07`; cả hai nằm trong FIFO outbound. Sau khi
  socket sẵn sàng, `0xE5` được gọi thẳng xuống serializer, bỏ qua FIFO.
  Response `0xE5` bật gate còn thiếu để send worker drain index `0`, nên wire
  order client trên transport mới/reset là `0xE5 -> 0xBB -> 0x07`.
- **Confirmed (bootstrap/UI):** UI event case `1` chỉ gửi `0x9E` selector `0`
  khi `appReady` đã bật. Response selector `0` đọc một record keyed gồm 19
  giá trị và một field tùy chọn gate bởi sentinel `-1`, hydrate nhiều object
  rồi có nhánh gọi routine chuyển UI. Hai số cuối là tọa độ `x/y`; client quét
  grid theo `y`, có thể gửi tiếp `0x9E` selector `2`. Cả sáu direct sender
  selector `2` đã tìm được đều lấy tọa độ từ selected/current entity phía
  client; event chiều về thêm `entityKey` và bị bỏ qua nếu key trỏ lại chính
  selected/current entity. Chỉ entity khác mới đặt state correction khi tọa
  độ nhận được khác current coordinate. Consumer update xử lý correction theo
  kiểu hybrid: di chuyển ngang từng tick qua
  collision map, có đường căn `y` sau hội tụ và một bước micro-reconcile cho
  sai số mirror tối đa hai đơn vị; không phải teleport thuần. Xem
  [schema selector 0](../analysis/m3-command-9e-selector0.md) và
  [đồng bộ selector 2](../analysis/m3-command-9e-selector2.md). Vai trò
  transport được suy luận mạnh là client publication rồi server relay/state
  replication; việc server có validate hoặc thay tọa độ hay không vẫn
  `Unknown`. Logic placement làm
  suy yếu tên main menu/lobby. Routine cuối tính camera theo current entity,
  nên world/spatial gameplay là `Inferred`; lobby dạng world, phòng chờ hay
  trận vẫn `Unknown`.
  Sender `0xC4` thuộc UI event case `2` với gate one-shot riêng, không có bằng
  chứng là bước tự động trong bootstrap.
- **Coordinate writer boundary:** toàn dispatcher không có inline write vào
  sáu field current/target/mirror; 13 direct call-site hợp lệ đi qua tám
  helper. Các đường này bao phủ command `0x15`, `0xC0`, `0x35`, `0x16/0x54`,
  `0x18`, `0x59`, `0xC1` và `0x9E` selector `0/2/10`. `0x16/0x54` đặt
  current + target trong cùng routine cấu hình mảng A–D; selector `10` dựng
  một derived entity với current `x/y`. Kết quả cho thấy kiến trúc lai giữa
  hydrate/correction từ response và movement/collision cục bộ. Xem
  [inventory writer tọa độ](../analysis/m3-coordinate-writers.md).
- **Unknown (ordering inbound):** response `0xBB` ghi static owner
  `DAT_181454620`, còn readiness của `0xE2` nằm ở `DAT_1814545E8`. Không có
  gate, direct call hay shared flag đã thấy để ép thứ tự. Local server có thể
  chọn `0xBB -> 0xE2` để tuần tự hóa bootstrap, nhưng đó là lựa chọn
  `Inferred` cần kiểm chứng.
- **Unknown:** port thực tế ở mọi phiên, plaintext/tên chính xác của panel
  account/session, ý nghĩa đầy đủ của command ID, heartbeat và auth semantic
  của response `0xBB`.
- **Confirmed (form `0x2B`):** một caller UI kiểm tra chín text input bắt buộc,
  gửi chúng dưới dạng chín string length-prefixed; response chỉ đọc một byte,
  tạo/tái dùng object UI rồi gọi virtual slot `7`. Đã ánh xạ đủ chín control
  sang localization ID và wire order, nhưng plaintext label chưa giải được.
  `Inferred`: thuộc luồng onboarding/account/profile. Không coi là login cho
  tới khi xác định màn hình trước đó và ý nghĩa label; xem
  [m3-command-2b.md](../analysis/m3-command-2b.md).
- **Inferred mạnh:** host source của đường chọn server là byte array UTF-8 dài
  13; metadata chỉ có một chuỗi ASCII dài 13 phù hợp là `14.225.206.44` tại
  byte offset `6469992`. Chưa có mapping field-RVA cuối cùng để nâng thành
  `Confirmed`. Một patch cùng độ dài thành `127.000.000.1` trên bản sao là
  chiến lược M6; xem [báo cáo endpoint](../analysis/m3-endpoint-state.md).

Fixture handshake identity, response `0xBB` và bootstrap collection rỗng đến
mốc `0xDB` được tổng hợp ở
[đường local login](../analysis/m3-local-login-path.md).

## Giới hạn của IL recovery

Cpp2IL báo bỏ qua hai method rất lớn. Trong trace của riêng type transport,
344/938 event là ghi chú `Cpp2ILInjected...NoteDecompilerIssue`; còn có nhiều
`Method not found`, `Indirect call` và unmanaged-memory placeholder. Bởi vậy
IL khôi phục có ích để định vị call site, nhưng chưa đủ để suy ra byte-level
packet hoặc chứng minh mọi nhánh runtime. Cần kiểm tra chéo bằng phân tích mã
máy khi cần, trước khi chuyển nhận định sang `Confirmed` về hành vi client.

## Đối chiếu native và việc tiếp theo

Đã đối chiếu method kết nối `0x0600028D` với native `0x1804DF5A0` và hai callback với `0x1804E2520` (đường gửi) / `0x1804E3D60` (đường nhận). Xem [báo cáo transport native](../analysis/m3-native-transport.md). Kết quả này xác nhận ranh giới transport ở mức cấu trúc, chưa xác nhận message ngữ nghĩa hay luồng màn hình.

1. Đã lần caller `0x060001C1` tới mảng chọn host/port và nối worker nhận với collection được `FixedUpdate` xử lý; tiếp tục nối thao tác UI chọn endpoint với callback Unity và xác định điều kiện bàn giao trực tiếp/qua collection.
2. Xác minh các nhánh framing, biến đổi byte và xử lý lỗi ở native.
3. Xác nhận bằng capture thứ tự server response `0xBB`/`0xE2`, byte `+0x2DD`, và consumer
   của global mode `10` để phân biệt lobby dạng world, phòng chờ và trận.
4. Tìm đường gián tiếp gọi setter HP đích `0x0600044A`, xác định state khóa
   và điều kiện runtime của entry `0x16/0x54`, rồi xác định server xác nhận,
   phát lại hay ghi đè hit/HP/địa hình nào trước khi chốt M3.
