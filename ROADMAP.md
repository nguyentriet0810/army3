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
`analysis/m3-unity-loop.md`. Đã xác định cấu trúc bảng điều phối message,
nhưng chưa có schema hay ý nghĩa command; xem
`analysis/m3-message-dispatch.md`.
Khảo sát tĩnh đã nối hai entry byte điều phối `0x16/0x54` tới nhánh đọc
mảng 16-bit từ buffer message, phân biệt hai chế độ điền mảng con
(đọc trực tiếp hoặc tích lũy từ bước tăng), và xác nhận phép tính khoảng
cách cục bộ. Đã thấy cặp mảng đầu được tiêu thụ tuần tự để tạo các
object hình học; chưa xác định lịch chạy của consumer hoặc nơi dùng cặp
mảng sau.
Trong hai method tiêu thụ trực tiếp `0x06000B66/0x06000B67`, khảo sát
một tầng callee và đồ thị lời gọi IL khôi phục sâu tối đa 12 cạnh chưa
thấy đường tới hàm enqueue message gửi `0x0600028F`. Đây là kết quả âm
có giới hạn: cùng đồ thị đó bỏ sót một cạnh đã được xác nhận ở native,
nên không chứng minh client không gửi kết quả mô phỏng qua đường khác.
Chưa xác định nơi quyết định va chạm/sát thương; xem
`analysis/m3-case16-54-arrays.md` và `analysis/m3-simulation-boundary.md`.
State machine, ngữ nghĩa packet
và ranh giới thẩm quyền mô phỏng vẫn chưa xác định; xem
`docs/client-architecture.md` và `docs/client-state-machine.md`.

### Mục tiêu

Hiểu vòng đời client và ranh giới giữa giao diện, trạng thái game, mô phỏng và
kết nối server.

### Công việc

- [ ] Xác định điểm khởi tạo ứng dụng và các manager chính.
- [ ] Lập sơ đồ trạng thái: khởi động, đăng nhập, chọn server, lobby, phòng, trận.
- [ ] Xác định lớp socket/transport và cơ chế reconnect hoặc heartbeat.
- [ ] Xác định lớp encode/decode packet và bảng command/message ID.
- [ ] Xác định dữ liệu nào được tải từ asset cục bộ và dữ liệu nào do server gửi.
- [ ] Xác định vị trí tính vật lý, quỹ đạo, sát thương và thay đổi địa hình.
- [ ] Phân loại từng kết luận thành `Confirmed`, `Inferred` hoặc `Unknown`.

### Đầu ra

- `docs/client-architecture.md`
- `docs/client-state-machine.md`
- Danh mục các điểm vào mạng và game loop quan trọng.

### Tiêu chí hoàn thành

- Có sơ đồ đủ rõ để mô tả client mong đợi server làm gì ở mỗi trạng thái.
- Biết mô phỏng trận đấu chủ yếu nằm ở client hay server.

---

## M4 — Đặc tả giao thức

**Trạng thái:** Planned

### Mục tiêu

Mô tả giao thức client-server dưới dạng độc lập với implementation.

### Công việc

- [ ] Xác định transport, framing, byte order và giới hạn kích thước packet.
- [ ] Xác định handshake, phiên bản client và cơ chế tạo session.
- [ ] Xác định nén, mã hóa, checksum hoặc biến đổi byte nếu có.
- [ ] Lập bảng message ID, hướng truyền và trạng thái hợp lệ.
- [ ] Mô tả schema cho các message đã xác nhận.
- [ ] Tạo test vector nhỏ, không chứa thông tin tài khoản hay dữ liệu nhạy cảm.
- [ ] Viết parser/serializer có kiểm tra độ dài và lỗi đầu vào.

### Đầu ra

- `docs/protocol.md`
- `docs/messages/` cho schema chi tiết nếu cần.
- Bộ codec và unit test trong source tree tương ứng.

### Tiêu chí hoàn thành

- Encode rồi decode lại các test vector cho kết quả giống ban đầu.
- Có đủ message đã xác nhận để thực hiện kết nối và đăng nhập cục bộ.

---

## M5 — Server localhost tối thiểu

**Trạng thái:** Planned

### Mục tiêu

Cho client kết nối an toàn đến một server cục bộ và hoàn thành handshake cơ bản.

### Công việc

- [ ] Chọn ngôn ngữ/runtime sau khi hiểu yêu cầu giao thức.
- [ ] Tạo cấu trúc server tách transport, protocol và domain logic.
- [ ] Bind mặc định vào `127.0.0.1` và port cấu hình được.
- [ ] Thêm logging có cấu trúc, không ghi credential hoặc secret.
- [ ] Thực hiện handshake, heartbeat và đóng kết nối đúng giao thức.
- [ ] Xử lý packet sai mà không làm server crash.
- [ ] Viết test tích hợp bằng client mô phỏng nhỏ.

### Đầu ra

- Source trong `server/`.
- Cấu hình mẫu và hướng dẫn chạy.
- Unit test và integration test tối thiểu.

### Tiêu chí hoàn thành

- Client hoặc client mô phỏng kết nối, handshake và duy trì session ổn định.
- Server không lắng nghe trên interface công cộng theo cấu hình mặc định.

---

## M6 — Chuyển hướng client về localhost

**Trạng thái:** Planned

### Mục tiêu

Đưa client đến server tương thích cục bộ mà không làm thay đổi bản gốc.

### Công việc

- [ ] Xác định chính xác nguồn endpoint và cơ chế chọn server.
- [ ] Chọn phương pháp ít xâm lấn nhất: config, launcher, DNS cục bộ hoặc patch.
- [ ] Lưu mọi patch dưới dạng script tái lập, không commit binary đã sửa.
- [ ] Thêm kiểm tra hash để patch chỉ áp dụng cho đúng bản client.
- [ ] Đảm bảo không còn kết nối ngoài dự kiến trong chế độ offline.
- [ ] Viết quy trình khôi phục và tạo lại bản làm việc từ client gốc.

### Đầu ra

- Công cụ hoặc script chuyển hướng trong `tools/`.
- `docs/client-redirection.md`

### Tiêu chí hoàn thành

- Client làm việc kết nối đến `127.0.0.1` một cách tái lập được.
- Client gốc vẫn nguyên vẹn và có thể xác minh bằng hash.

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
