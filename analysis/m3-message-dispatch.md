# M3: Bảng điều phối message cấp ứng dụng

Phân tích tĩnh trên client đã hash ở M1. Không chạy client hoặc liên hệ
server bên thứ ba. Các địa chỉ chỉ đúng với bản `GameAssembly.dll` này.
`Confirmed` ở đây là cấu trúc mã native/metadata, không phải hành vi
đã quan sát trong phiên chơi.

## Handler và byte điều phối

Interface ở field transport `+0x20` có một method nhận object message;
class triển khai tìm thấy trong `Assembly-CSharp` có method token
`0x060006DC`. ISIL của method chỉ khôi phục được phần lớn bước
khởi tạo metadata rồi dừng; Ghidra ánh xạ nó tới `FUN_1801fcab0`.
Decompile toàn hàm timeout sau 45 giây trong project đang phân tích từng
phần, nên không dùng decompile đó làm bảng command.

Disassembly ở `0x1801fe6f9..0x1801fe780` cho thấy:

1. Load một byte từ object message tại offset instance `+0x10`.
2. `MOVSX` chuyển byte đó thành signed 8-bit.
3. Gọi `FUN_180002ab0` với tham số thứ hai `-126`; helper chỉ tính
   `param_1 - param_2`, nên chỉ số bảng là `signedByte + 126`.
4. Nếu chỉ số unsigned lớn hơn `0xFD` thì nhảy nhánh mặc định.
   Nếu không, đọc RVA 32-bit từ bảng `0x180256c88[index]` rồi nhảy.

Như vậy byte `0x80` và `0x81` không vào bảng; byte `0x82` ứng với entry
`0`, `0x00` ứng với entry `126`, `0x7F` ứng với entry `253`. Đây là
ánh xạ **cấu trúc**, không cho biết ý nghĩa command hay trạng thái hợp lệ.

## Bảng nhảy và giới hạn

Script chỉ đọc giải 254 RVA trong bảng. Tất cả 254 entry trỏ tới stub
`JMP rel32` năm byte, đều nằm trong vùng nhớ được ánh xạ. Sau khi theo
stub, có **140 đích khác nhau**: **113 entry** về chung đích mặc định
`0x180256c55`; **141 entry** còn lại phân bố trên các đích khác.
Các stub chưa được project Ghidra phân tích từng phần nhận diện thành
instruction (`0/254`), do đó chưa có call graph hay decompile đáng tin
cho từng case.

Ví dụ để kiểm tra cách đọc bảng, **không phải tên message**:

| Byte sau biến đổi | Entry | Đích sau stub |
| --- | ---: | --- |
| `0x82` | 0 | `0x180248d84` |
| `0x83` | 1 | mặc định |
| `0x9E` | 28 | `0x180249714` |
| `0xA9` | 39 | mặc định |
| `0xDA` | 88 | `0x18021415C` |
| `0xDB` | 89 | mặc định |
| `0xE0` | 94 | `0x18021482F` |
| `0xE1` | 95 | `0x1802143EA` |
| `0xE2` | 96 | `0x1802135A8` |
| `0xE5` | 99 | mặc định |
| `0x00` | 126 | `0x180228159` |
| `0x01` | 127 | mặc định |
| `0x02` | 128 | `0x180203b91` |
| `0x2B` | 169 | `0x1801fec7d` |
| `0x7F` | 253 | `0x180204031` |

Việc `0x83`, `0xA9`, `0xE5` về mặc định ở handler này phù hợp với
worker nhận xử lý riêng ba byte đó trước khi bàn giao message thường;
không kết luận rằng chúng không thể xuất hiện trong tình huống khác.
Các byte trong bảng là byte lệnh logic **sau** biến đổi tùy trạng thái. Khi
cờ biến đổi tắt, byte này bằng byte thô. Khi cờ bật, quan hệ chính xác là:

```text
logical = (raw XOR key[recvIndex]) - shift    (mod 256)
raw     = (logical + shift) XOR key[recvIndex]
```

Do `recvIndex` thay đổi theo mọi byte đã biến đổi trước đó, entry `0x16` hay
`0x54` không ánh xạ tới một raw byte cố định. Xem
[khung packet](m3-packet-framing.md) và
[vòng đời biến đổi byte](m3-byte-transform-state.md).

## Một case đã lần được: `0x02`

Target của entry `128` (`0x02`) là `0x180203b91`. Pseudo-disassembly
chỉ đọc tới lệnh nhảy kết thúc case ở `0x180203c2d` cho thấy lời gọi
`FUN_1804e09b0` (đường đóng/reset transport đã thấy ở M3), tiếp đó
`FUN_1804e14f0` và `FUN_18043bea0`. Hàm cuối chính là caller dùng
host/port endpoint để yêu cầu kết nối; xem
[m3-endpoint-state.md](m3-endpoint-state.md).
Decompile của `FUN_1804e14f0` cho thấy nó xóa field `+0x30` của object
được truyền vào và đặt cờ tĩnh transport `+0xB0` về `0`; chưa biết ý
nghĩa hai field đó.

`Confirmed`: nếu luồng xử lý đi vào case `0x02`, mã native có đường gọi
đến hàm yêu cầu kết nối. `Inferred`: đây có thể là một cơ chế mở lại
kết nối sau thông điệp từ server. Chưa biết điều kiện runtime để case
này nhận message, hoặc liệu kết nối kế tiếp
thành công. Không dùng suy luận này để giả lập message `0x02` ở M4.

## Một case đã lần được: `0x2B`

Entry `169` đi tới `0x1801FEC7D`. Handler chỉ đọc một byte, tạo hoặc tái dùng
một object UI/state rồi gọi virtual slot `7`. Phía gửi nhận chín string từ
một form chín input bắt buộc và ghi chín giá trị length-prefixed. Cấu trúc này
được ghi riêng ở [m3-command-2b.md](m3-command-2b.md); ý nghĩa đăng ký, hồ sơ
hay xác thực vẫn `Unknown`, nên chưa gọi nó là login.

## Cụm bootstrap `0xE2`, `0xDA/0xE1/0xE0`, `0xDB` và `0x9E`

`Confirmed`: case `0xE2` so sánh ba cặp version/cache. Mỗi mismatch gửi một
trong ba request `0xDA`, `0xE1`, `0xE0`; cache match đi đường tải cục bộ. Các
response và đường cache cùng hội tụ về ba readiness flag. Một consumer khác
đợi đủ ba cờ, đặt `appReady`, gửi `0xDB` rồi xóa chúng. `0xDB` không có case
xử lý riêng trong jump table này.

`Confirmed`: UI event case `1` kiểm tra `appReady` rồi gửi `0x9E` selector `0`.
Response `0x9E` selector `0` hydrate một record keyed bằng byte đầu, có schema
cố định cộng một record con tùy chọn, rồi có nhánh placement và chuyển scene.
Hai field cuối là tọa độ `x/y`; client có thể gửi selector `2`, còn event
selector `2` trả `entityKey + x/y` và đặt correction khi khác current state.
Xem [schema selector 0](m3-command-9e-selector0.md) và
[đồng bộ selector 2](m3-command-9e-selector2.md).

Quét writer tọa độ đầy đủ còn nối selector `10` tới constructor của một
derived entity, với hai word payload được ghi vào current `+0x84/+0x88`.
Ngoài `0x9E`, các command `0x15`, `0xC0`, `0x35`, `0x16/0x54`, `0x18`,
`0x59` và `0xC1` cũng có đường direct-call tới writer current/target/mirror.
Xem [inventory writer tọa độ](m3-coordinate-writers.md); tên nghiệp vụ của
phần lớn command này vẫn `Unknown`.

Tên scene đích vẫn `Unknown`; suy luận main menu/lobby trước đây không còn đủ
mạnh sau khi thấy logic grid/tọa độ.
Control flow và các khoảng trống còn lại được ghi tại
[m3-length4-commands.md](m3-length4-commands.md).

## Session/config `0xBB` và đường tới `0xE2`

`Confirmed`: sender `0xBB` ghi hai string và một byte. Một caller trong đường
connect dùng UUID lưu ở PlayerPrefs làm string đầu. Response branch
`0x1802430B8` đọc bốn string, ghi dword zero tại
`DAT_181454620+0x188`, ghi hai kết quả split và hai string nguyên vào cùng
state session/UI, đặt `+0x18D=1`, rồi thay row selector `1` của bảng
`string[][]` từ hai thành bốn mục. Branch không gọi callback UI; event UI về
sau mới kiểm tra `row.Length == 4` và có thể mở panel hai-mode/ba action.
Ba readiness byte cùng offset mà cụm `0xE2` sử dụng thuộc static owner khác,
`DAT_1814545E8`; do đó không có shared-state dependency đã xác nhận giữa hai
handler. Ngữ nghĩa account authentication và thứ tự inbound `0xBB`/`0xE2`
vẫn `Unknown`.

`Confirmed`: `0xE5/A9` không gọi handler `0xE2`. Receive worker xử lý chúng
riêng rồi tiếp tục đọc; packet server `0xE2` kế tiếp đi qua
`FUN_1804E05E0`, trực tiếp hoặc queue `+0xA8`, tới listener/app dispatcher.
`0xA9/0` đóng socket; `/1` và `/2` trở lại vòng đọc. Xem
[m3-session-bootstrap-transitions.md](m3-session-bootstrap-transitions.md).

## Chứng cứ và bước tiếp theo

- ISIL: method `0x060006DC` trong
  `analysis/generated/cpp2il/isil/IsilDump/Assembly-CSharp/`.
- Log Ghidra (Git-ignored):
  `analysis/generated/ghidra/message-handler-entry.log`,
  `message-handler-branches.log`, `handler-command-source.log`,
  `handler-switch-window.log`, `handler-index-helper.log` và
  `handler-jumptable-stubs.log`, `handler-case02.log`,
  `handler-case02-helper.log`.
- Script tái lập trong `scripts/ghidra/`:
  `InspectFunctionBranchMap.java`, `InspectInstructionWindow.java`,
  `InspectJumpTable.java`, `InspectPseudoInstructions.java` và
  `InspectNativeTargets.java`; dùng
  `-process GameAssembly.dll -noanalysis -readOnly`.

Entry byte `0x16` và `0x54` cùng đi vào `0x18022ADB0`; từ đó
có đường CFG tĩnh tới call site `0x18022D28F`, nơi handler gọi method
cấu hình nhận các mảng `short[][]`. Nhánh này đọc byte và số 16-bit
từ buffer message để cấp phát/điền mảng. Đây chưa phải schema packet
hay tên nghiệp vụ; xem
[m3-case16-54-arrays.md](m3-case16-54-arrays.md) và
[m3-simulation-boundary.md](m3-simulation-boundary.md).

Để nâng từ cấu trúc sang schema message, cần phân tích một số case
cụ thể trong môi trường tĩnh, nối call site với dữ liệu được đọc/ghi
và transition màn hình. Chưa có bằng chứng để đặt tên login/lobby/room
hay kết luận client/server bên nào tính sát thương và vật lý.
