# M3 — Hai entry message chia sẻ nhánh đọc mảng

Phân tích tĩnh trên bản `GameAssembly.dll` đã hash ở M1. Không chạy
client, không liên hệ server. Các byte dưới đây là byte điều phối
**sau biến đổi trạng thái**, không chắc là byte thô trên TCP.

## Liên kết từ bảng điều phối

- **Confirmed (cấu trúc):** entry `148` (byte `0x16`) và entry `210`
  (byte `0x54`) trong bảng `0x180256C88` đều có stub nhảy tới
  `0x18022ADB0`.
- **Confirmed (luồng mã tĩnh):** từ `0x18022ADB0`, phép duyệt CFG
  bằng pseudo-disassembly đi tới `CALL 0x180525DF0` tại
  `0x18022D28F`. Duyệt 1.043 instruction, không gặp lỗi giải mã hoặc
  indirect branch trong vùng đã giới hạn; đường tìm được có 461
  instruction. Đích gọi là method `0x0600042E` đã nối với bốn field
  `short[][]` trong [m3-simulation-boundary.md](m3-simulation-boundary.md).
- **Giới hạn:** duyệt CFG xét cả hai phía của nhánh điều kiện, không
  chứng minh đường đi đó khả thi trong một phiên chơi. Hai byte có cùng
  entry code nhưng chưa biết điều kiện nhận hoặc ý nghĩa nghiệp vụ.
  Các case khác vẫn có thể nhảy vào đoạn code dùng chung.

## Đọc payload và tạo mảng

- **Confirmed:** tại `0x18022ADB8`, handler lấy object message trên
  stack; `FUN_1801A02F0` lấy field reader `+0x18` từ object đó.
  Đường mã gọi `0x1801A0520` nhiều lần. Helper này nhảy tới
  `FUN_1801A0450`: đọc một byte trong buffer tại field `+0x10` và
  tăng cursor `+0x18`. Đây là phép đọc trên buffer message, không
  chứng minh layout packet thô trước giải mã.
- **Confirmed:** `FUN_1801A0540` đọc hai byte liên tiếp từ cùng kiểu
  buffer theo thứ tự byte cao trước, tăng cursor sau mỗi byte và trả
  về số 16-bit. Lời gọi tại `0x18022B7F9` dùng kết quả làm độ dài
  cho bốn lần gọi helper cấp phát mảng `0x1800B77A0`
  (`0x18022B847`, `0x18022B895`, `0x18022B8E3`,
  `0x18022B931`). Helper đó chuyển tới `FUN_1801241C0`,
  nơi cấp phát theo kích thước phần tử × số lượng và ghi độ dài ở
  offset `+0x18`.
- **Confirmed:** trong thân vòng lặp bắt đầu `0x18022B79C`, lời gọi
  `0x18022BA26` đọc thêm một giá trị 16-bit; `0x18022BA6D`
  chuyển giá trị đó cùng mảng và chỉ số tới `FUN_180002A30`.
  Hàm cuối kiểm tra biên rồi ghi 16-bit vào
  `array + 0x20 + index * 2`. Một cặp tương tự ở
  `0x18022BAEE` / `0x18022BB35` điền mảng thứ hai.
- **Confirmed:** byte đọc tại `0x18022AE15` được giữ ở stack slot
  `+0x117` và chọn một trong hai vòng đọc bên dưới. Byte khác đọc
  tại `0x18022AFAA` được giữ ở `+0x86`; giá trị `0x31` của byte
  thứ hai chỉ ảnh hưởng nhánh cuối của vòng đọc thứ nhất.
- **Inferred:** bốn mảng ngoài và các mảng con cùng kích thước được
  xây từ các giá trị trong message để cập nhật trạng thái client.
  Chưa truy hết mọi nhánh để mô tả chính xác thứ tự và số lượng của
  từng mảng, nên đây **chưa phải schema packet**.

## Hai chế độ điền mảng con

Gọi bốn mảng con cùng độ dài `n` là `a`, `b`, `c`, `d`; `i` là chỉ số
trong mảng. Các quy tắc sau là **Confirmed (luồng mã tĩnh)** cho vùng
`0x18022B79C..0x18022C87C`, không khẳng định mọi đường đi đều khả thi
với một message hợp lệ:

- Nếu byte `+0x117 == 0`, vòng lặp bắt đầu tại `0x18022B98E`.
  Với `i == 0`, nó đọc hai giá trị 16-bit vào `a[0]`, `b[0]`
  (`0x18022BA26`, `0x18022BAEE`), rồi sao chép sang `c[0]`,
  `d[0]` (`0x18022BBED`, `0x18022BCA5`).
- Với `i > 0`, nếu `i == n - 1` và byte `+0x86 == 0x31`, nhánh
  `0x18022BD1F..0x18022BEA9` đọc trực tiếp hai giá trị 16-bit
  vào `c[i]`, `d[i]`. Sau đó còn hai lượt đọc byte cho trạng thái
  khác; chưa xác định ý nghĩa của chúng.
- Với các `i > 0` còn lại, nhánh `0x18022C14C..0x18022C5D6`
  đọc hai byte có dấu vào `a[i]`, `b[i]`, rồi tính
  `c[i] = (c[i-1] + a[i]) mod 65536` và
  `d[i] = (d[i-1] + b[i]) mod 65536`. Helper `0x180002AB0` tính
  `i-1`, `0x180002A10` đọc phần tử mảng 16-bit, `0x180002A70`
  cộng, `0x180002EF0` giữ 16 bit thấp và `0x180002A30` ghi lại.
- Nếu byte `+0x117 == 1`, nhánh `0x18022C674..0x18022C877`
  duyệt `i = 0..n-1` và đọc trực tiếp hai giá trị 16-bit vào
  `c[i]`, `d[i]` (`0x18022C6FF`, `0x18022C7C7`). Không thấy
  lượt đọc/ghi tương ứng cho `a[i]`, `b[i]` trong vòng này.

Đây là hai **kiểu giải mã dữ liệu**, không phải bằng chứng về hai
message ID. Chưa xác nhận cách xử lý mọi giá trị khác `0` và `1`
của byte chế độ, giới hạn hợp lệ của `n`, hay mục đích của bốn mảng.

## Đường đi của bốn mảng ngoài

**Confirmed (luồng tham số):** bốn lần cấp phát mảng ngoài trong cùng
nhánh lần lượt lưu kết quả vào stack slot `+0x3940`, `+0x3948`,
`+0x3950`, `+0x3958`. Ngay trước lời gọi `0x180525DF0`, chúng được
đặt vào bốn vị trí tham số `short[][]` của method `0x0600042E`.
Method này gọi `0x180407270` / `0x06000B64`, truyền tiếp bốn tham số
đó theo cùng thứ tự. Setter ghi chúng vào object như sau:

| Mảng ngoài | Cấp phát tại | Stack tại lời gọi `0x180525DF0` | Field của object |
| --- | --- | --- | --- |
| A | `0x18022B678` | `+0x30` (tham số 6) | `+0x48` |
| B | `0x18022B6C5` | `+0x38` (tham số 7) | `+0x50` |
| C | `0x18022B712` | `+0x58` (tham số 11) | `+0x58` |
| D | `0x18022B75F` | `+0x60` (tham số 12) | `+0x60` |

Các offset stack ở bảng được đo tại **caller**; offset field được đo
trên object đích. Đối chiếu native disassembly với chữ ký method trong
metadata (Windows x64 ABI) là cần thiết vì ISIL khôi phục có vài tên
biến tạm không nhất quán. Đây là ánh xạ mảng ngoài, không gán ý nghĩa
cho bốn thành phần của payload.

**Confirmed (consumer đã thấy):** một method của chính type chứa bốn
field đọc `+0x48` và `+0x50`, lấy hai `short[]` theo cùng chỉ số rồi
truyền chúng cho constructor của object hình học; xem
[ranh giới mô phỏng](m3-simulation-boundary.md). Trong phần ISIL đã
khôi phục của type này, chưa thấy lượt đọc tương ứng cho `+0x58` và
`+0x60`. Đó chỉ là giới hạn của phép quét, **không** chứng minh hai
field sau không được dùng.

**Confirmed (consumer tuần tự):** method `0x06000B66` kiểm tra chỉ số
instance tại field `+0x68` với độ dài mảng ngoài ở `+0x48`. Khi còn
phần tử hợp lệ, nó lấy `A[index]` và `B[index]`, truyền cả hai
`short[]` vào constructor `0x180300740`, thêm object vừa tạo vào
`ArrayList` rồi tăng `index` lên 1. Các nhánh trước constructor còn
kiểm tra dữ liệu trạng thái khác, nên không phải mọi lần gọi đều tạo
object. ISIL khôi phục cho thấy method `0x06000B65` và `0x06000B67`
gọi consumer này; `0x060007C0` gọi `0x06000B67` trên một instance
tĩnh khi instance đó tồn tại. Metadata cho thấy `0x060007C0` là
`override` của một method trên base class trừu tượng; Ghidra ánh xạ
nó tới `FUN_1802870F0` và hiện chỉ thấy hai data reference tới entry,
không thấy code reference trực tiếp. Do đó việc quét IL không tìm thấy
caller trực tiếp **không** chứng minh method không chạy: virtual
dispatch hoặc IL bị khôi phục thiếu vẫn là khả năng. Chưa xác định
caller thực tế hoặc tần suất thực thi.

**Confirmed (ngữ cảnh của override):** trong `0x060007C0`, trước lời
gọi `0x06000B67` còn có một nhánh lấy `ArrayList.Count`, duyệt phần
tử, gọi xử lý trên từng object và có đường `ArrayList.Remove`.
Method chỉ gọi `0x06000B67` khi instance tĩnh ở field `+0x1A8`
khác null. Đây là cấu trúc của một lượt xử lý collection, nhưng
**không** đủ để gọi là Unity `Update`/`FixedUpdate` hay xác định
tần suất của nó.

## Điều chưa biết

- **Unknown:** tên message, ý nghĩa bốn mảng và vai trò của `0x16`
  so với `0x54`. Không gọi chúng là map/quỹ đạo/sát thương.
- **Unknown:** các giá trị trong mảng là trạng thái có thẩm quyền từ
  server hay dữ liệu đầu vào để client tiếp tục mô phỏng. M3 vẫn chưa
  xác định được bên quyết định va chạm và sát thương.
- **Unknown:** byte command thô trên TCP, điều kiện chọn case và
  các nhánh còn lại trong handler.

## Tái lập

Ghidra đã import `GameAssembly.dll` vào project Git-ignored
`analysis/generated/ghidra/army3-native`. Script read-only:

```text
-process GameAssembly.dll -noanalysis -readOnly
-scriptPath scripts/ghidra
-postScript TracePseudoReachability.java 18022ADB0 18022D28F 18022D329
```

Log Git-ignored: `handler-jumptable-stubs-script.log`,
`case16-coordinate-fullpath-script.log`, `packet-byte-core.log`,
`case16-parser-helpers.log`, `case16-loop-entry-script.log`,
`case16-loop-body-script.log`, `case16-third-array-script.log`,
`case16-array-write-script.log`, `case16-branches-script.log`,
`case16-loop-control-script.log`, `case16-base-copy-script.log`,
`case16-arith-helpers-script.log`, `case16-sub-helper-script.log`,
`array-core.log` và `array-write-helper.log`. Cần tiếp tục xác định
ý nghĩa byte chế độ/marker, giới hạn độ dài và nơi hai field sau được
dùng. Quét caller bằng `scripts/inspect-il-calls.ps1` sinh các TSV
Git-ignored `analysis/generated/m3/coordinate-consumer-callers.tsv`
và `coordinate-main-consumer-callers.tsv`. Log Ghidra
`coordinate-consumer-caller-script.log` chứa entry và xref của
`FUN_1802870F0`; `coordinate-base-virtual-callers.tsv` cho thấy các
override khác gọi base method, không phải call site đã xác nhận tới
override `0x060007C0`.
