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
| `0xA9` | 39 | mặc định |
| `0xE5` | 99 | mặc định |
| `0x00` | 126 | `0x180228159` |
| `0x01` | 127 | mặc định |
| `0x02` | 128 | `0x180203b91` |
| `0x7F` | 253 | `0x180204031` |

Việc `0x83`, `0xA9`, `0xE5` về mặc định ở handler này phù hợp với
worker nhận xử lý riêng ba byte đó trước khi bàn giao message thường;
không kết luận rằng chúng không thể xuất hiện trong tình huống khác.
Các byte trong bảng là byte lệnh **sau** biến đổi tùy trạng thái, không
nhất thiết là byte thô trên TCP.

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

Một call site khác trong runtime-function của handler, `0x18022D28F`,
gọi method cấu hình nhận các mảng `short[][]`. Đây là đường từ message
handler tới dữ liệu tọa độ cục bộ, nhưng chưa xác định byte lệnh hoặc
nguồn/ý nghĩa các mảng; xem [m3-simulation-boundary.md](m3-simulation-boundary.md).

Để nâng từ cấu trúc sang schema message, cần phân tích một số case
cụ thể trong môi trường tĩnh, nối call site với dữ liệu được đọc/ghi
và transition màn hình. Chưa có bằng chứng để đặt tên login/lobby/room
hay kết luận client/server bên nào tính sát thương và vật lý.
