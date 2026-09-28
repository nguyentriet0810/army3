# Army3 Offline Roadmap

## Mục tiêu

Xây dựng một môi trường tương thích client-server chạy hoàn toàn trên máy cá
nhân, cho phép client Army3 hiện có hoạt động mà không phụ thuộc vào máy chủ bên
thứ ba.

Đây là dự án học tập về kiến trúc client-server và khả năng tương thích phần
mềm. Dự án không nhằm vận hành dịch vụ game công cộng hoặc phân phối lại tài
sản độc quyền của trò chơi.

## Cách sử dụng roadmap

Trạng thái milestone:

- `Planned`: chưa bắt đầu.
- `In progress`: đang thực hiện.
- `Blocked`: cần thêm dữ liệu hoặc quyết định.
- `Complete`: đã đạt toàn bộ tiêu chí hoàn thành.

Mức độ chắc chắn của phát hiện kỹ thuật:

- `Confirmed`: được chứng minh bằng mã, dữ liệu hoặc kiểm thử tái lập được.
- `Inferred`: suy luận có cơ sở nhưng chưa được kiểm chứng đầy đủ.
- `Unknown`: chưa đủ dữ liệu để kết luận.

Mỗi milestone nên được tách thành các GitHub Issue nhỏ. Issue phải có phạm vi,
đầu ra và tiêu chí hoàn thành rõ ràng.

## Nguyên tắc xuyên suốt

- Giữ nguyên thư mục client gốc và không đưa tài sản game vào Git.
- Ưu tiên phân tích tĩnh trước khi chạy bất kỳ file thực thi nào.
- Chỉ thực hiện phân tích động khi có sự đồng ý của người dùng và trong môi
  trường cô lập, chặn kết nối ra Internet theo mặc định.
- Server tương thích phải chỉ lắng nghe trên `127.0.0.1` theo mặc định.
- Không liên hệ, thăm dò hoặc gây ảnh hưởng đến máy chủ của bên thứ ba.
- Không đưa thông tin đăng nhập, token, dữ liệu cá nhân hoặc dữ liệu máy cục bộ
  vào repository.

---

## M0 — Nền tảng dự án

**Trạng thái:** In progress

### Mục tiêu

Thiết lập repository và quy tắc làm việc an toàn, tái lập được.

### Công việc

- [x] Khởi tạo Git repository với nhánh `main`.
- [x] Tạo repository GitHub công khai.
- [x] Loại client gốc và đầu ra sinh tự động khỏi Git.
- [x] Viết `README.md` và `AGENTS.md`.
- [x] Viết roadmap ban đầu.
- [ ] Thống nhất quy ước commit, branch và GitHub Issue.
- [ ] Tạo cấu trúc thư mục khi có nội dung thực tế đầu tiên.

### Tiêu chí hoàn thành

- Repository không chứa client, asset gốc, secret hoặc file sinh tự động.
- Quy tắc an toàn và workflow đủ rõ để một tác vụ mới có thể tiếp tục dự án.

---

## M1 — Kiểm kê client tĩnh

**Trạng thái:** Complete

### Mục tiêu

Tạo hồ sơ kỹ thuật có thể kiểm chứng cho bản client đầu vào mà không chạy nó.

### Công việc

- [x] Ghi lại cây thư mục, kích thước và loại file quan trọng.
- [x] Ghi SHA-256 cho executable, DLL, metadata và các gói tài nguyên.
- [x] Xác định phiên bản Unity, kiến trúc CPU và kiểu build IL2CPP.
- [x] Kiểm tra chữ ký số và thông tin phiên bản của các binary.
- [x] Lập danh mục `StreamingAssets`, asset archive và dữ liệu bản đồ.
- [x] Tìm cấu hình, hostname, địa chỉ IP, port và chuỗi liên quan đến mạng.
- [x] Ghi lại các dấu hiệu làm rối, mã hóa hoặc chống phân tích.

### Đầu ra

- `analysis/client-inventory.md`
- `analysis/hashes.sha256`
- Danh sách câu hỏi kỹ thuật còn `Unknown`.

### Tiêu chí hoàn thành

- Có thể xác định chính xác bản client nào đang được phân tích.
- Kiểm kê và hash có thể được tạo lại bằng script trong repository.

---

## M2 — Bộ công cụ phân tích IL2CPP

**Trạng thái:** Hoàn thành

### Mục tiêu

Tạo quy trình tái lập để trích xuất metadata cần thiết từ `GameAssembly.dll` và
`global-metadata.dat`.

### Công việc

- [x] Chọn và ghi phiên bản công cụ IL2CPP phù hợp.
- [x] Kiểm tra khả năng tương thích với Unity 6000.5.10f1.
- [x] Viết script chạy công cụ với đường dẫn cấu hình được, không hard-code máy.
- [x] Giữ toàn bộ output lớn trong thư mục đã ignore.
- [x] Trích xuất danh sách assembly, type, method, field và string hữu ích.
- [x] Đánh giá mức độ ảnh hưởng của obfuscation.
- [x] Ghi lại giới hạn và sai số của từng công cụ.

### Đầu ra

- Script tái lập trong `tools/` hoặc `scripts/`.
- `analysis/il2cpp-tooling.md`
- Báo cáo về metadata khôi phục được.

### Tiêu chí hoàn thành

- Một lần chạy sạch có thể tạo lại kết quả phân tích mà không sửa client gốc.
- Xác định được các type hoặc method có khả năng phụ trách kết nối mạng.

---

## M3 — Lập bản đồ kiến trúc client

**Trạng thái:** In Progress

Đã đối chiếu transport, hai worker gửi/nhận, đường chọn host/port và một
đường `FixedUpdate` → collection transport; xem
`analysis/m3-native-transport.md`, `analysis/m3-endpoint-state.md` và
`analysis/m3-unity-loop.md`. Đã xác định cấu trúc bảng điều phối message và
schema từng phần cho một số command; ý nghĩa nghiệp vụ của phần lớn command
vẫn chưa biết. Xem `analysis/m3-message-dispatch.md`.
Khảo sát tĩnh đã nối hai entry byte điều phối `0x16/0x54` tới nhánh đọc
mảng 16-bit từ buffer message, phân biệt hai chế độ điền mảng con
(đọc trực tiếp hoặc tích lũy từ bước tăng), và xác nhận phép tính khoảng
cách cục bộ. Cặp mảng đầu được tiêu thụ để tạo object hình học; cặp sau
C/D được ghép thành danh sách point có thứ tự rồi được consumer khác duyệt
tuần tự. Cấu trúc này tương thích với waypoint/path, nhưng lịch chạy và
ngữ nghĩa gameplay chính xác vẫn chưa xác định.
Trong hai method tiêu thụ trực tiếp `0x06000B66/0x06000B67`, khảo sát
một tầng callee và đồ thị lời gọi IL khôi phục sâu tối đa 12 cạnh chưa
thấy đường tới hàm enqueue message gửi `0x0600028F`. Đây là kết quả âm
có giới hạn: cùng đồ thị đó bỏ sót một cạnh đã được xác nhận ở native,
nên không chứng minh client không gửi kết quả mô phỏng qua đường khác.
Hai virtual call đã nhận diện từ consumer đi tới sibling override
`0x06000A67`; hai nhánh của override tiếp tục duyệt collection cục bộ
và chưa lộ đường gửi. Cả 11 computed call native của consumer đã được
phân loại thành hai sibling override và chín thao tác collection; không
call nào trực tiếp là enqueue/worker/serializer. Xem
`analysis/m3-virtual-dispatch.md`.
Quét toàn bộ writer của sáu field tọa độ entity đã hoàn tất ở mức direct
dispatcher: không có inline write; 13 direct call-site hợp lệ đi qua tám
helper và được nối tới command `0x15`, `0xC0`, `0x35`, `0x16/0x54`, `0x18`,
`0x59`, `0xC1`, cùng selector `0/2/10` của `0x9E`. `0x16/0x54` vừa cấu hình
mảng A–D vừa đặt current/target từ payload; selector `10` dựng derived entity
với current `x/y`. Kết quả nghiêng về mô hình lai server hydrate/correction và
client movement/collision, nhưng policy thẩm quyền chính xác vẫn chưa biết.
Xem `analysis/m3-coordinate-writers.md`.
Đã xác định một đường update projectile kiểm tra vùng chồng lấn với player,
trừ damage khỏi HP hiện tại và xử lý nhánh HP về 0. Đường
`0x06000A62 -> 0x0600080B -> 0x060005B8` còn áp stamp ảnh vào `int[]` mask
quanh tọa độ va chạm; đây là phép biến đổi mask cục bộ và được suy luận mạnh
là thay đổi địa hình/tạo hố. Đối chiếu native còn xác nhận đường update
`0x060007C0 -> 0x06000B67 -> 0x06000A62`, trong đó `0x06000B67` duyệt
collection object. Một đường batch khác đặt HP hiện tại/tối đa từ dữ liệu
mảng. Đã tách thêm state HP đích (`+0x184`), cờ (`+0x37C`) và bước nội suy
(`+0x3A8`): một setter công khai thiết lập state này và vòng update entity kéo
HP hiện tại về đích. Message dispatcher không truy cập trực tiếp các field đó,
và hai data reference của setter chỉ nằm trong `.pdata`/dãy code pointer,
không phải code xref; nguồn gọi gián tiếp vẫn chưa xác định. Hai entry `0x16/0x54`
đã nối bằng state chung tới object có đường sửa mask. Công thức raw/logical
command đã xác định là XOR key cộng/trừ shift theo index có state, nên không
có raw byte cố định; key thực tế, điều kiện runtime và nghĩa gameplay vẫn chưa
rõ. Payload thiết lập `0xE5` bắt đầu bằng độ dài, seed key và shift; client
biến seed thành prefix-XOR key, rồi đọc một giá trị text-like length-prefixed.
Tùy state phiên, client lưu giá trị đó hoặc gửi `0xA9` subcommand `0` kèm hai
bộ đếm; các nhánh nhận `0xA9` thao tác cờ, bộ đếm và collection transport.
Năm logical command `0x88/0xA4/0xC4/0xD7/0xE1` dùng length 4 byte và không
biến đổi length/payload trong đường đã thấy. Đã xác nhận `0x88` đọc sáu số
64-bit, `0xE1` đọc ba blob length-prefixed vào các bảng state và đặt cờ hoàn
tất. Đã lần caller `0xE1` về handler `0xE2`: handler này điều phối ba nhánh
cache/request `0xDA/0xE1/0xE0`, mỗi nhánh hội tụ về một readiness flag. Khi
đủ ba cờ, client đặt `appReady`, gửi `0xDB` và xóa cờ. UI event case `1` sau đó
có thể gửi `0x9E` selector `0`; response hydrate entity/game state và có nhánh
chuyển UI. Schema selector `0` đã xác nhận là một record keyed gồm 19 giá trị,
có string, cụm sáu word và một record con tùy chọn gate bởi sentinel `-1`;
hai số cuối là tọa độ `x/y`. Client quét grid theo `y` rồi có thể gửi request
`0x9E/2`; event selector `2` mang `entityKey + x/y`, so current coordinate và
đặt correction khi khác. Consumer đã xác nhận correction là hybrid: bước ngang
theo tick có collision check, có thể snap `y` sau hội tụ và micro-reconcile sai
số mirror nhỏ; không phải teleport thuần. Cả sáu direct sender đã tìm được đều
lấy tọa độ từ selected/current entity phía client; event chiều về bỏ qua chính
entity này trước khi đọc `x/y` và chỉ reconcile entity khác. Do đó vai trò
transport được suy luận mạnh là client publication rồi server relay/state
replication, không phải authoritative self-correction. Server có validate,
clamp hoặc thay tọa độ hay không vẫn `Unknown`. Nhánh nhận không gửi lại, nên
đây không phải vòng đệ quy. Logic placement làm suy yếu tên main menu/lobby;
scene đích vẫn chưa biết. Đã nối ranh giới `0xE5/A9 -> 0xE2`: handler đặc
biệt quay lại receive-loop, packet server `0xE2` kế tiếp đi qua direct/queued
app dispatch; `0xA9/0` đóng socket nên không thể đi tiếp cùng phiên. Đường
connect còn gửi `0xBB` gồm UUID/config/byte; response đọc bốn string, reset
dword UI/session `DAT_181454620+0x188`, ghi config state và bật `+0x18D`.
Lần đầu là bước client/session identity/config được suy luận. Đã lần tiếp
panel hai-mode: action submit yêu cầu hai text khác rỗng, đóng form rồi gửi
chính `0xBB(textControl38, textControl30, mode)`. Đây là đường submit account/
session đã xác nhận về control flow, dù plaintext label và auth semantic vẫn
`Unknown`. Đã chốt thứ tự outbound của kết nối mới/reset: connect path
enqueue `0xBB`, khởi động thread rồi enqueue `0x07`; `0xE5` được gửi trực tiếp
và response của nó mở gate để FIFO drain, nên wire order phía client là
`0xE5 -> 0xBB -> 0x07`. Thứ tự server response `0xBB` so với server `0xE2`
vẫn `Unknown`: không có gate, direct call hay shared flag đã thấy; readiness
của `0xE2` thuộc static owner khác `DAT_1814545E8`. Local server có thể thử
`0xBB -> 0xE2` để lifecycle tuần tự nhưng phải giữ nhãn `Inferred`. Response
`0xBB` cũng không gọi callback UI; nó thay menu row selector `1` từ hai thành bốn mục.
Event UI về sau mới mở panel hai-mode, ba action, được phân loại là
account/session `Inferred`. Ba parser bootstrap đã được thu hẹp tới fixture
collection rỗng hợp lệ: `0xDA` có blob count `u8=0`; hai blob đầu `0xE1` có
count `u16=0`, blob ba có count `u8=0`; `0xE0` có count `u8=0` và `u16=0`.
Handshake có thể dùng seed/shift zero để tạo transform identity cho prototype.
Toàn bộ vector và state machine local-login nằm ở
`analysis/m3-local-login-path.md`. `0xC4` thuộc UI event case `2` có gate one-shot
riêng, không có bằng chứng thuộc chuỗi bootstrap tự động. Xem
`analysis/m3-length4-commands.md` và
`analysis/m3-command-9e-selector0.md` cùng
`analysis/m3-command-9e-selector2.md` và
`analysis/m3-session-bootstrap-transitions.md`.
Đã lần thêm command `0x2B`: caller UI yêu cầu đủ chín text input, sender ghi
chín string length-prefixed và response chỉ đọc một byte trước khi tạo/tái
dùng object UI rồi gọi virtual slot `7`. Đã ánh xạ đủ chín control sang
localization ID và wire order; plaintext label vẫn chưa giải được vì bảng
chuỗi đi qua metadata handle và decoder riêng. Cấu trúc phù hợp một form
onboarding/account/profile nhưng chưa đủ bằng chứng gọi là login; xem
`analysis/m3-command-2b.md`.
Chưa nối được đường hit/HP tới command
message hoặc xác định server có xác nhận/ghi đè kết quả; xem
`analysis/m3-projectile-damage-terrain.md` và
`analysis/m3-simulation-boundary.md`.
Đã tách vòng đời mất kết nối khỏi reconnect: worker nhận khi dừng chỉ gọi
callback `1/2` theo ngưỡng 501 ms rồi reset state, không tự mở socket; case
ứng dụng `0x02` mới đóng/reset rồi gọi lại đường kết nối. Quét 128 direct
sender không thấy client tạo `0x9A`; byte này đi vào nhánh mặc định nên hiện
chỉ là ứng viên keepalive/no-op server → client, chưa có chu kỳ hay watchdog
được xác nhận. Xem `analysis/m3-connection-lifecycle.md`.
State machine, ngữ nghĩa packet
và ranh giới thẩm quyền mô phỏng vẫn chưa xác định; xem
`docs/client-architecture.md` và `docs/client-state-machine.md`.

Phần phân tích tĩnh **cần trực tiếp cho mục tiêu qua form đăng nhập local** đã
đủ để chuyển sang M4/M5: framing, handshake, hai loại `0xBB`, bootstrap rỗng
và mốc `0xDB` đều có schema triển khai được. M3 tổng thể vẫn `In Progress` vì
lobby/phòng/trận, asset-vs-server data và quyền quyết định mô phỏng chưa đủ để
đóng toàn milestone.

### Mục tiêu

Hiểu vòng đời client và ranh giới giữa giao diện, trạng thái game, mô phỏng và
kết nối server.

### Công việc

- [ ] Xác định điểm khởi tạo ứng dụng và các manager chính.
- [ ] Lập sơ đồ trạng thái: khởi động, đăng nhập, chọn server, lobby, phòng, trận.
- [x] Xác định lớp socket/transport và cơ chế reconnect hoặc heartbeat.
- [x] Xác định lớp encode/decode packet và bảng command/message ID.
- [ ] Xác định dữ liệu nào được tải từ asset cục bộ và dữ liệu nào do server gửi.
- [x] Xác định vị trí tính vật lý, quỹ đạo, sát thương và thay đổi địa hình.
- [x] Phân loại từng kết luận thành `Confirmed`, `Inferred` hoặc `Unknown`.

### Đầu ra

- `docs/client-architecture.md`
- `docs/client-state-machine.md`
- Danh mục các điểm vào mạng và game loop quan trọng.

### Tiêu chí hoàn thành

- Có sơ đồ đủ rõ để mô tả client mong đợi server làm gì ở mỗi trạng thái.
- Biết mô phỏng trận đấu chủ yếu nằm ở client hay server.

---

## M4 — Đặc tả giao thức

**Trạng thái:** Completed cho phạm vi local-login; chờ kiểm chứng runtime ở M6

### Mục tiêu

Mô tả giao thức client-server dưới dạng độc lập với implementation.

### Công việc

- [x] Xác định transport, framing, byte order và giới hạn kích thước packet.
- [x] Xác định handshake, phiên bản client và cơ chế tạo session tối thiểu.
- [x] Xác định biến đổi byte có trạng thái; chưa thấy nén/checksum ở đường này.
- [x] Lập bảng message ID, hướng truyền và trạng thái hợp lệ cho local-login.
- [x] Mô tả schema cho các message đã xác nhận.
- [x] Tạo test vector nhỏ, không chứa thông tin tài khoản hay dữ liệu nhạy cảm.
- [x] Viết parser/serializer có kiểm tra độ dài và lỗi đầu vào.

### Đầu ra

- `docs/protocol.md`
- `docs/messages/login-bootstrap.md` cho schema chi tiết.
- Codec Python trong `server/army3_protocol/` và unit test trong `tests/`.

### Tiêu chí hoàn thành

- Encode rồi decode lại các test vector cho kết quả giống ban đầu.
- Có đủ message đã xác nhận để thực hiện kết nối và đăng nhập cục bộ.

Đã kiểm tra bằng `python -m unittest discover -s tests -v`. Kết quả runtime
với client thật vẫn là `Inferred` cho tới M6; M4 không chạy client và không
mở listener mạng.

---

## M5 — Server localhost tối thiểu

**Trạng thái:** Completed với client mô phỏng; chờ client thật ở M6

### Mục tiêu

Cho client kết nối an toàn đến một server cục bộ và hoàn thành handshake cơ bản.

### Công việc

- [x] Chọn Python 3 và thư viện chuẩn sau khi chốt yêu cầu giao thức M4.
- [x] Tạo cấu trúc server tách transport, protocol và session state machine.
- [x] Bind mặc định vào `127.0.0.1`, port cấu hình được; từ chối non-loopback.
- [x] Thêm logging có cấu trúc, không ghi nội dung hai field `0xBB`.
- [x] Thực hiện handshake, lifecycle `0x07` đã xác nhận và đóng kết nối sạch.
- [x] Xử lý packet sai mà không làm server hoặc listener crash.
- [x] Viết test tích hợp bằng client mô phỏng nhỏ.

### Đầu ra

- Source trong `server/`.
- Cấu hình CLI và hướng dẫn tại `docs/local-server.md`.
- Unit test và integration test trong `tests/`.

### Tiêu chí hoàn thành

- Client hoặc client mô phỏng kết nối, handshake và duy trì session ổn định.
- Server không lắng nghe trên interface công cộng theo cấu hình mặc định.

Client mô phỏng đã hoàn tất `0xE5 -> 0xBB -> 0xE2 -> 0xE1/0xE0/0xDA ->
0xDB -> 0xBB` qua TCP loopback. Client thật M6 xác nhận thêm pre-login
`0xFD/0x3A/0x72`, message một chiều `0xB2` và heartbeat server `0x9A`.
Heartbeat 10 giây giữ nguyên socket quá 40 giây; thiếu heartbeat client đóng
sau khoảng 18–20 giây.

---

## M6 — Chuyển hướng client về localhost

**Trạng thái:** Runtime loopback/isolation đã xác nhận; chờ xác nhận UI và `0xDB`

### Mục tiêu

Đưa client đến server tương thích cục bộ mà không làm thay đổi bản gốc.

### Công việc

- [x] Xác định nguồn endpoint, offset và cơ chế chọn server bằng phân tích tĩnh;
      mapping cuối vẫn `Inferred` cho tới runtime.
- [x] Chọn patch metadata cùng độ dài trên bản sao làm phương pháp ít điểm chạm.
- [x] Lưu patch trong `tools/redirect_client.py`; binary sửa nằm dưới `build/`.
- [x] Kiểm tra đủ manifest 148 file và hai hash metadata cố định.
- [x] Kiểm chứng runtime với firewall chặn non-loopback; client thật kết nối
      `127.0.0.1:19150` và không có destination TCP ngoài dự kiến.
- [x] Viết quy trình xác minh, tạo lại và dùng client gốc làm bản khôi phục.

### Đầu ra

- `tools/redirect_client.py` và `scripts/run-local-client-isolated.ps1`.
- `docs/client-redirection.md`.

### Tiêu chí hoàn thành

- Client làm việc kết nối đến `127.0.0.1` một cách tái lập được.
- Client gốc vẫn nguyên vẹn và có thể xác minh bằng hash.

Bản sao `build/army3-local-client/` đã được tạo và qua `verify-copy`; source
gốc qua `verify-source` trước và sau patch. Runtime đã đi tới hai lần trao đổi
`0xBB`, đủ ba request cache và heartbeat ổn định. Client ghi cache version `2`
nhưng vẫn đứng ở `Chuẩn bị tài nguyên... 100%` và không gửi `0xDB`. M6 vì vậy
đã hoàn tất chuyển hướng/cô lập, còn ranh giới bootstrap → UI phải được chốt
trước khi bắt đầu phần hồ sơ offline của M7.

---

## M7 — Đăng nhập và dữ liệu người chơi offline

**Trạng thái:** Planned

### Mục tiêu

Cho phép vào game bằng hồ sơ cục bộ không cần tài khoản bên ngoài.

### Công việc

- [ ] Mô phỏng đăng nhập hoặc tạo session offline.
- [ ] Tạo hồ sơ nhân vật mặc định.
- [ ] Gửi dữ liệu phiên bản, tiền tệ, chỉ số và inventory tối thiểu.
- [ ] Xác định trường bắt buộc và giá trị mặc định hợp lệ.
- [ ] Lưu dữ liệu cục bộ theo schema có version và migration.
- [ ] Thêm lệnh reset hoặc tạo lại dữ liệu người chơi.

### Tiêu chí hoàn thành

- Có thể mở client, đăng nhập offline và vào màn hình chính ổn định.
- Khởi động lại không làm mất hoặc hỏng dữ liệu người chơi cục bộ.

---

## M8 — Lobby, phòng và tải bản đồ

**Trạng thái:** Planned

### Mục tiêu

Đi từ màn hình chính đến một phòng cục bộ và tải được bản đồ chơi.

### Công việc

- [ ] Mô phỏng danh sách khu vực/kênh nếu client yêu cầu.
- [ ] Tạo, vào và rời phòng một người chơi.
- [ ] Đồng bộ lựa chọn nhân vật, trang bị và map.
- [ ] Xác định dữ liệu map nằm cục bộ và metadata server cần cung cấp.
- [ ] Thực hiện chuỗi message bắt đầu trận.
- [ ] Xử lý quay lại lobby sau khi trận kết thúc hoặc bị hủy.

### Tiêu chí hoàn thành

- Người chơi có thể tạo phòng, chọn map và đi đến màn hình trận đấu.
- Luồng vào/rời phòng không cần kết nối Internet.

---

## M9 — Vòng lặp trận đấu cơ bản

**Trạng thái:** Planned

### Mục tiêu

Hoàn thành một trận đấu offline có bắt đầu, lượt chơi và kết thúc rõ ràng.

### Công việc

- [ ] Xác định dữ liệu khởi tạo trận và thứ tự lượt.
- [ ] Hỗ trợ di chuyển, ngắm, bắn và kết thúc lượt ở mức tối thiểu.
- [ ] Đồng bộ hoặc mô phỏng quỹ đạo, sát thương và thay đổi địa hình.
- [ ] Xử lý chết, thắng/thua và kết quả trận.
- [ ] Thêm timeout và phục hồi trạng thái lỗi.
- [ ] Tạo kịch bản kiểm thử trận đấu xác định trước.

### Tiêu chí hoàn thành

- Có thể chơi và kết thúc ít nhất một trận offline tái lập được.
- Kết quả không phụ thuộc vào server hoặc dịch vụ Internet.

---

## M10 — Bot và nội dung chơi đơn

**Trạng thái:** Planned

### Mục tiêu

Biến vòng lặp kỹ thuật thành trải nghiệm chơi cá nhân có đối thủ và tiến trình.

### Công việc

- [ ] Chọn phạm vi bot tối thiểu và hành vi có thể kiểm thử.
- [ ] Tách quyết định bot khỏi protocol transport.
- [ ] Thêm mức độ khó hoặc cấu hình hành vi.
- [ ] Thêm phần thưởng và tiến trình offline hợp lý.
- [ ] Bổ sung map, vật phẩm và luật chơi theo dữ liệu đã xác nhận.
- [ ] Không mô phỏng hệ thống kinh tế trực tuyến không cần thiết.

### Tiêu chí hoàn thành

- Có thể chơi nhiều trận với bot mà không cần thao tác kỹ thuật thủ công.
- Trạng thái và tiến trình offline được lưu ổn định.

---

## M11 — Đóng gói và phát hành cục bộ

**Trạng thái:** Planned

### Mục tiêu

Tạo quy trình cài đặt và chạy offline đơn giản, có thể khôi phục từ client gốc.

### Công việc

- [ ] Tạo launcher hoặc script khởi động server rồi mở client làm việc.
- [ ] Kiểm tra port, file bắt buộc và phiên bản client trước khi chạy.
- [ ] Thêm backup/reset dữ liệu người chơi.
- [ ] Tạo bản build server tái lập được.
- [ ] Viết hướng dẫn cài đặt, nâng cấp và xử lý lỗi.
- [ ] Xác minh không đóng gói tài sản độc quyền vào repository hoặc release.

### Tiêu chí hoàn thành

- Một máy sạch có thể dựng server từ source và kết nối client gốc theo tài liệu.
- Chế độ offline hoạt động khi Internet bị ngắt.

---

## Cổng quyết định quan trọng

Các quyết định sau chỉ được đưa ra sau khi có đủ bằng chứng:

1. **Ngôn ngữ server:** chọn sau M3-M4 dựa trên giao thức và yêu cầu tooling.
2. **Cách chuyển hướng client:** ưu tiên config/launcher; chỉ patch binary khi không
   có phương án ít xâm lấn hơn.
3. **Phạm vi mô phỏng trận đấu:** phụ thuộc vào kết luận client-authoritative hay
   server-authoritative ở M3.
4. **Phân tích động:** chỉ bắt đầu khi phân tích tĩnh không đủ và có kế hoạch cô
   lập, chặn mạng rõ ràng.

## Định nghĩa phiên bản đầu tiên chơi được

Phiên bản `0.1.0` được xem là đạt khi:

- Client kết nối duy nhất đến server trên localhost.
- Có thể đăng nhập bằng hồ sơ offline.
- Có thể tạo phòng một người, tải một map và bắt đầu trận.
- Có thể hoàn thành một trận đấu cơ bản và quay lại lobby.
- Dữ liệu người chơi được lưu cục bộ.
- Toàn bộ quy trình được dựng lại từ source và tài liệu trong repository, không
  commit client hoặc tài sản game gốc.
