# Chuyển hướng bản sao client về localhost

M6 dùng patch cùng độ dài trong metadata của **bản sao làm việc**. Không file
nào trong `Mobiarmy3HA_3.0.0_GOC/` được sửa, đổi tên hoặc xóa.

## Trạng thái chứng cứ

- `Confirmed`: client khởi tạo port `19150`; UI chọn server chép host/port
  vào endpoint trước lời gọi connect.
- `Confirmed` bằng runtime cô lập ngày 2026-09-28: chuỗi ASCII dài 13 byte
  `14.225.206.44` tại offset `6469992` là endpoint được client dùng; bản sao
  sau patch kết nối tới `127.0.0.1:19150`.
- `Confirmed`: thay bằng `127.000.000.1` giữ nguyên kích thước 13 byte và
  `System.Net.IPAddress.Parse` chuẩn hóa nó thành `127.0.0.1` trên máy này.
- `Confirmed`: launcher đã tạo rule chặn mọi IPv4/IPv6 ngoài loopback cho tất
  cả executable của bản sao, client thật chỉ xuất hiện tại listener loopback,
  và rule tạm được kiểm tra là đã gỡ sạch sau mỗi lần chạy kết thúc.

## Hash cố định

```text
metadata gốc:
0debeea2cb8aa5013709f7845d1bba21800d6974b1461be8482d3558d43775c9

metadata sau patch:
b4890d59779968d8a544f3dfb3a75778da948e61d590ae9d1631b7a132b85cf4
```

Phép patch thay 13 byte tại offset `6469992`. Do dấu chấm và một số ký tự
trùng nhau, có 11 vị trí byte thực tế thay đổi.

## Công cụ tái lập

Xác minh đủ 148 file client gốc theo manifest M1:

```powershell
python -m tools.redirect_client verify-source
```

Tạo bản sao dưới thư mục Git-ignored `build/`:

```powershell
python -m tools.redirect_client create
```

Output mặc định:

```text
build/army3-local-client/
```

Công cụ từ chối ghi đè output đã tồn tại. Nó thực hiện theo thứ tự:

1. xác minh đủ manifest và metadata hash gốc;
2. yêu cầu đúng một occurrence của endpoint tại đúng offset;
3. copy vào thư mục tạm dưới `build/`;
4. patch đúng 13 byte;
5. xác minh toàn bộ file của bản sao, cho phép khác hash chỉ ở metadata;
6. ghi marker `.army3-local-copy.json` và publish bằng rename;
7. xác minh lại client gốc.

Kiểm tra lại bản sao bất kỳ lúc nào:

```powershell
python -m tools.redirect_client verify-copy
```

Để tạo lại mà không xóa dữ liệu, chọn output mới:

```powershell
python -m tools.redirect_client create --output build/army3-local-client-rebuilt
```

Client gốc chính là bản khôi phục chuẩn; không áp dụng reverse patch lên bản
gốc hoặc dùng bản patched làm nguồn cho lần tạo tiếp theo.

## Chạy cô lập

Quy trình này đã được kiểm chứng sau khi người dùng cấp phép chạy bản sao và
tạo/gỡ firewall rule tạm:

Terminal thường:

```powershell
python -m server --log-level DEBUG
```

Terminal PowerShell 7 chạy **Administrator**:

```powershell
./scripts/run-local-client-isolated.ps1
```

Nếu một hoặc nhiều firewall profile vốn đang tắt, launcher mặc định sẽ từ
chối chạy. Chỉ sau khi có chấp thuận rõ ràng cho lần kiểm thử đó mới dùng:

```powershell
./scripts/run-local-client-isolated.ps1 -TemporarilyEnableFirewallProfiles
```

Switch này ghi nhớ đúng các profile ban đầu đang tắt, bật chúng trước khi tạo
rule cô lập, rồi đặt lại chúng thành tắt trong `finally`, kể cả khi server chưa
listen, client lỗi khởi động hoặc phiên kiểm thử thất bại.

Launcher:

- xác minh marker và mọi hash của bản sao trước khi chạy;
- yêu cầu tất cả Windows Firewall profile đang bật, hoặc cần switch opt-in để
  bật tạm và khôi phục đúng trạng thái ban đầu;
- yêu cầu server đang listen trên `127.0.0.1:19150`;
- thêm rule outbound tạm thời cho mọi `.exe` trong bản sao, chặn mọi IPv4 và
  IPv6 ngoài loopback;
- nhờ desktop shell mở game ở quyền người dùng thường; launcher giữ quyền
  admin chỉ để sở hữu firewall rule;
- theo dõi TCP của tiến trình chính, dừng ngay nếu destination khác
  `127.0.0.1:19150` xuất hiện;
- luôn gỡ rule trong `finally` khi client thoát hoặc có lỗi.
- dừng client nếu quan sát thấy TCP tới địa chỉ không phải loopback; kết nối
  loopback phụ (ví dụ cổng tài nguyên) chỉ được ghi cảnh báo vì vẫn nằm trong
  phạm vi cô lập localhost.

Không chạy script nếu chưa có sự cho phép rõ ràng, vì nó thực thi binary chưa
tin cậy và thay đổi Windows Firewall tạm thời.

## Tiêu chí runtime còn lại

- [x] server log nhận kết nối từ client thật trên `127.0.0.1:19150`;
- [x] runtime đi qua `0xE5 -> 0xFD -> 0xBB -> 0xE2 -> 0xB2 -> 0x07`;
- [x] client chấp nhận bootstrap cache rỗng và heartbeat `0x9A`; một socket
  sống ổn định quá 40 giây thay vì timeout khoảng 20 giây;
- [x] server-push `0xC4/selector 0` làm current screen đổi từ splash `+0x58`
  sang target `+0x70`; nhánh cache-hit không yêu cầu tải resource;
- [x] sau thao tác UI, singleton login thành current screen, splash bằng `0`,
  `appReady=1`, và client phát `0xC6` rồi `0xDB` qua reconnect;
- [x] xác nhận runtime server mới giữ socket sau `0xC6`/`0xDB`;
- UI mở được panel hai mode và submit `0xBB` mà không disconnect;
- [x] firewall chặn TCP/UDP ngoài loopback;
- [x] sau khi thoát, firewall rule tạm đã được gỡ; source/copy qua verify.

Baseline trước `0xC4` đứng ở `Chuẩn bị tài nguyên... 100%`. Revision mismatch
`127` mở flow "Đang tải dữ liệu" và phát request `0xC4`; không dùng nhánh này
vì resource hợp lệ chưa được khôi phục. Cache hiện tại có
`vcBig=3`, nên server dùng revision `3`; revision là giá trị theo cache chứ
không phải hằng protocol. Barrier đã hội tụ, client phát `0xC6` payload
`00 00 01`, rồi `0xDB` rỗng sau reconnect. Server giữ nguyên kết nối và
tiếp tục heartbeat qua hai packet này; M6 vì vậy đã hoàn tất.
Một kết nối TLS phụ tới loopback `443` có SNI
`config.uca.cloud.unity3d.com`, nên được xác định là Unity Analytics config và
không phải dependency Army3 cần giả lập. Inspector đã xác nhận
`appReady=1`, các readiness flag đã reset và socket chỉ có destination
`127.0.0.1:19150` trong lần chạy cô lập cuối.

Trong khi client còn ở màn hình 100%, lấy PID của đúng executable trong bản
sao rồi chạy read-only inspector:

```powershell
python -m tools.inspect_runtime_state --pid <PID>
```

Diễn giải kết quả:

- một trong `e1_0x188/e0_0x189/da_0x18a` bằng `0`: nhánh parser/cache tương
  ứng chưa hội tụ;
- cả ba bằng `1`, `bootstrap_ui_instance_0x20` bằng `0x0`: singleton UI chứa
  barrier chưa được tạo;
- cả ba bằng `1`, singleton khác `0x0`, nhưng `app_ready_0x40` bằng `0`: UI
  instance tồn tại nhưng override barrier không được tick/active;
- `app_ready_0x40` bằng `1` mà server không thấy `0xDB`: cần khảo sát send
  queue/dispatcher sau barrier.
