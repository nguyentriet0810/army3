# M3: Năm command dùng outer length 4 byte

Phân tích tĩnh trên bản client đã hash ở M1. Không chạy client và không liên
hệ server bên thứ ba. Các command dưới đây là byte logic sau biến đổi của
transport; địa chỉ native chỉ đúng cho bản client này.

## Ranh giới framing

`Confirmed`: parser nhận chọn outer length 32-bit big-endian cho đúng năm
command `0x88`, `0xA4`, `0xC4`, `0xD7`, `0xE1`. Command vẫn tiêu thụ một byte
khóa khi biến đổi đang bật, nhưng bốn byte length và payload không đi qua
helper XOR trong nhánh đã thấy. Chi tiết ở
[m3-packet-framing.md](m3-packet-framing.md).

Jump table của message handler đưa chúng tới các nhánh sau:

| Command | Entry | Địa chỉ nhánh |
| --- | ---: | --- |
| `0x88` | 6 | `0x180255E52` |
| `0xA4` | 34 | `0x180212E2A` |
| `0xC4` | 66 | `0x18020FE72` |
| `0xD7` | 85 | `0x18022148F` |
| `0xE1` | 95 | `0x1802143EA` |

Việc cùng dùng outer length 4 byte chỉ là đặc điểm framing. Nó không chứng
minh năm command cùng một giai đoạn nghiệp vụ hoặc được server gửi liền nhau.

## `0x88`: sáu số nguyên 64-bit

- `Confirmed`: handler gọi reader `FUN_1801A0600` đúng sáu lần. Helper này
  đọc tám byte mỗi lần và ghép theo thứ tự byte cao trước.
- `Confirmed`: sáu kết quả được ghi liên tiếp vào các field instance
  `+0xC0`, `+0xC8`, `+0xD0`, `+0xD8`, `+0xE0`, `+0xE8` của cùng một object.
- `Confirmed`: handler chỉ sử dụng 48 byte đầu theo đường đã thấy rồi thoát
  khỏi case. Chưa thấy kiểm tra rằng outer payload phải dài đúng 48 byte.
- `Unknown`: ý nghĩa sáu field, hướng request/response trong phiên thực tế và
  command này có liên quan đăng nhập hay không.

Schema tối thiểu đã xác nhận:

```text
[value0:u64 BE] ... [value5:u64 BE]
```

Không gán tên tiền tệ, tài khoản hoặc chỉ số nhân vật cho các field khi chưa
có consumer hoặc metadata đủ rõ.

## `0xA4`: response có nhánh con

- `Confirmed`: byte đầu payload là selector. Giá trị `1` gọi
  `FUN_180426090`, là một virtual dispatch trên object lấy từ state tĩnh.
- `Confirmed`: selector khác `0` và `1` thoát sớm. Selector `0` tiếp tục đọc
  thêm byte, `i16`, `i32` và cập nhật collection/object.
- `Unknown`: schema đầy đủ, ý nghĩa collection và state nghiệp vụ.

## `0xC4`: request rỗng, response nhiều nhánh

- `Confirmed`: `FUN_180317E20` tạo message command `0xC4` mà không ghi
  payload trước khi gửi qua listener của service.
- `Confirmed`: caller thực của sender là `FUN_1801971A0`, một UI event handler.
  Chỉ nhánh `*param_2 == 2` mới có thể gửi request. Nhánh này đóng/reset UI,
  tạo control dùng localization ID `0x134` và event code `4`, rồi kiểm tra byte
  tĩnh `+0x78`.
- `Confirmed`: request chỉ được gửi khi byte `+0x78 == 0`; sau đó handler đặt
  byte này thành `1`. Một control event-code `4` thứ hai có thể được tạo tùy
  byte state `+0x11` ở một static object khác.
- `Confirmed`: response đọc selector byte và có nhiều nhánh tiếp tục đọc
  string length-prefixed, `i16`, `i32` và dữ liệu mảng.
- `Confirmed`: hai đường trong handler gọi cùng virtual-dispatch helper với
  selector slot `7` trên object lấy từ field state `+0x70`. Đây là callback
  có thể ảnh hưởng UI/state, nhưng target cụ thể chưa được ánh xạ.
- `Inferred`: đây là request một lần do thao tác UI kích hoạt, không phải bước
  tự động ngay sau transport handshake.
- `Unknown`: ý nghĩa event `2`, selector response và callback slot `7`. Không
  coi `0xC4` là transition lobby hoặc đặt nó trong chuỗi bootstrap tự động.

## `0xD7`: dữ liệu theo chỉ số/collection

- `Confirmed`: response bắt đầu bằng một `i16` big-endian rồi dùng giá trị
  trong luồng xử lý index/count và collection.
- `Confirmed`: handler không gọi helper virtual slot `7` giống `0xC4` trong
  phạm vi case đã lần.
- `Unknown`: schema phần còn lại, loại collection và state nghiệp vụ.

## `0xE1`: ba khối dữ liệu bootstrap

- `Confirmed`: có hai method service (`FUN_180317D20` và
  `FUN_18031EC90`) tạo request command `0xE1` không payload.
- `Confirmed`: response đọc một byte dẫn đầu, sau đó gọi `FUN_180266F10` ba lần.
  Helper này đọc length 32-bit big-endian, cấp phát đúng length và chép byte
  từ reader. Vì vậy phần đã xác nhận là:

```text
[leadingByte:byte]
[length1:u32 BE] [blob1:length1 bytes]
[length2:u32 BE] [blob2:length2 bytes]
[length3:u32 BE] [blob3:length3 bytes]
```

- `Confirmed`: ba blob lần lượt đi vào `FUN_1804F5C70`, `FUN_180451670` và
  `FUN_180450FA0`. Các hàm này đọc record/array và ghi nhiều bảng state tĩnh;
  ít nhất bộ giải thứ ba đọc count, string và số nguyên để dựng các mảng.
- `Confirmed`: cuối nhánh handler đặt byte `1` vào field state tĩnh `+0x188`.
  Handler không gọi virtual helper slot `7` đã thấy trong `0xC4`.
- `Inferred`: `0xE1` là phản hồi tải bộ dữ liệu cấu hình/bootstrap và field
  `+0x188` là cờ hoàn tất/sẵn sàng của bộ dữ liệu đó.
- `Confirmed`: caller thực của `FUN_180317D20` nằm trong handler command
  `0xE2` (`FUN_1801FCAB0`, nhánh `0x1802135A8`). Handler này so sánh ba cặp
  version/cache. Với cặp thứ hai ở static field `+0x2E8/+0x2EC`, mismatch gọi
  sender `0xE1`; match tải cache cục bộ rồi cũng đặt `+0x188 = 1`.
- `Unknown`: tên nghiệp vụ của ba blob và nguồn gửi `0xE2`; chưa nối được
  handler `0xE2` ngược về `0xE5/0xA9` bằng một execution edge tĩnh.

## Bộ ba bootstrap do `0xE2` điều phối

`Confirmed`: `0xE2` không chỉ gọi `0xE1`. Nó điều phối ba nhánh độc lập và mỗi
nhánh đều hội tụ về một readiness flag dù dùng dữ liệu mới hay cache cục bộ:

| Nhánh | Cache mismatch | Cache match | Cờ hoàn tất |
| --- | --- | --- | --- |
| 1 (`+0x2F8/+0x2FC`) | gửi request rỗng `0xDA` qua `FUN_180318660` | tải cache cục bộ | `+0x18A` |
| 2 (`+0x2E8/+0x2EC`) | gửi request rỗng `0xE1` qua `FUN_180317D20` | tải cache cục bộ | `+0x188` |
| 3 (`+0x2F4/+0x2F0`) | gửi request rỗng `0xE0` qua `FUN_180317EB0` | tải cache cục bộ | `+0x189` |

`Confirmed`: case `0xE2` lấy buffer reader và gọi byte-reader đúng ba lần;
trong CFG bounded của case không còn lời gọi reader payload nào khác. Schema
tối thiểu quan sát được là:

```text
[value0:i8 -> +0x2E8]
[value1:i8 -> +0x2F4]
[value2:i8 -> +0x2F8]
```

`Confirmed`: ba byte lần lượt được sign-extend thành int32 và ghi vào
`+0x2E8`, `+0x2F4`, `+0x2F8`. Chúng sau đó được so tương ứng với `+0x2EC`,
`+0x2F0`, `+0x2FC`. Do đó thứ tự byte trên wire không trùng thứ tự ba nhánh
trong bảng: byte thứ ba điều phối `0xDA`, byte thứ nhất điều phối `0xE1`, byte
thứ hai điều phối `0xE0`. Ý nghĩa nghiệp vụ của các version/cache value vẫn
`Unknown`.

Các response tương ứng `0xDA`, `0xE1`, `0xE0` lần lượt đặt `+0x18A`, `+0x188`,
`+0x189`. Vì các so sánh độc lập, thứ tự request thực tế phụ thuộc cặp cache
nào mismatch; không có một thứ tự cố định `DA → E1 → E0`.

`Confirmed`: `FUN_18043D800` là consumer/barrier của ba cờ. Khi cả ba khác
zero, nó:

1. đặt byte static `+0x40 = 1` (gọi là `appReady` trong tài liệu này);
2. gửi request rỗng `0xDB`;
3. xóa cả ba cờ `+0x188/+0x189/+0x18A`.

Tên `appReady` chỉ là alias mô tả. Command `0xDB` đi vào default/ignore của
jump table handler đã khảo sát, vì vậy `Inferred`: đây là thông báo client đã
sẵn sàng hơn là response mang dữ liệu.

## Từ `appReady` tới request `0x9E`

- `Confirmed`: trong `FUN_1801A2FE0`, UI event case `1` kiểm tra `appReady`.
  Nếu cờ bằng zero, nó đi vào đường localization `0x7AC`; nếu cờ khác zero,
  nó gọi `FUN_18031AE70`.
- `Confirmed`: `FUN_18031AE70` gửi command `0x9E` với payload một byte bằng
  `0`, tức selector `0`.
- `Confirmed`: response `0x9E` đọc selector `0..15`. Nhánh selector `0` tại
  `0x180249830` đọc một record duy nhất gồm 19 giá trị, keyed bằng byte đầu;
  trong đó có một string, cụm sáu word và một record con tùy chọn được gate
  bởi sentinel `i32 == -1`. Schema đầy đủ ở
  [m3-command-9e-selector0.md](m3-command-9e-selector0.md). Ở cuối nhánh, nếu
  byte instance `+0x2DD` khác zero, nó gọi
  `FUN_18027D8D0(0)` rồi gọi `FUN_180419570` trên object ở static field
  `+0x140`.
- `Confirmed`: hai field cuối selector `0` là tọa độ `x/y`. Client có đường
  quét grid theo `y`, gửi `0x9E` selector `2` với tọa độ ứng viên; event
  selector `2` trả `entityKey + x/y`, so với current position rồi đặt state
  correction khi khác. Nhánh nhận không gửi lại message, nên không tạo vòng
  đệ quy. Xem [m3-command-9e-selector2.md](m3-command-9e-selector2.md).
- `Confirmed`: `FUN_180419570` xóa UI/state hiện tại, tính lại tọa độ dựa trên
  kích thước màn hình, đặt một global state byte thành `10`, rồi gọi một chuỗi
  helper dựng/chuyển UI. Sau phát hiện placement/grid, chỉ còn có thể gọi đây
  là transition scene sau hydrate entity; main menu, lobby, room hay match
  đều vẫn `Unknown`.
- `Confirmed`: đường này do UI event case `1` kích hoạt, không tự chạy chỉ vì
  barrier ba cờ hoàn tất.

## Kết luận về state sau handshake

- `Confirmed`: handler `0xE5` chỉ cài key/shift, bật biến đổi và xử lý một
  giá trị text-like; nhánh transport có thể gửi `0xA9` subcommand `0` để
  đồng bộ tiếp. Xem
  [m3-byte-transform-state.md](m3-byte-transform-state.md) và
  [m3-special-messages.md](m3-special-messages.md).
- `Confirmed`: từ handler `0xE2` trở đi đã xác định được chuỗi bootstrap:
  ba nhánh cache/request `0xDA/0xE1/0xE0` hội tụ ở barrier ba cờ, barrier đặt
  `appReady` và gửi `0xDB`; một UI event sau đó có thể gửi `0x9E` selector `0`,
  hydrate state rồi đi tới một transition UI.
- `Confirmed`: `0xC4` nằm ở UI event case `2` có gate one-shot riêng, không có
  bằng chứng thuộc chuỗi tự động trên.
- `Inferred`: state chắc chắn nhất ngay sau `0xE5` là **transport transformed /
  synchronization pending hoặc ready**, chưa phải login hay lobby.
- `Unknown`: execution edge từ `0xE5/0xA9` tới nguồn `0xE2`, ý nghĩa byte
  `+0x2DD`, tên màn hình cuối, và command xác thực account/session. Command
  `0x2B` đã được tách thành form chín trường nhưng chưa đủ bằng chứng gọi là
  login; xem [m3-command-2b.md](m3-command-2b.md).

## Chứng cứ tái lập

- `analysis/generated/ghidra/handler-jumptable-stubs-script.log`: ánh xạ
  jump-table.
- `analysis/generated/ghidra/length4-cfg-summary-script.log` và
  `length4-cfg-full-script.log`: call/write inventory từng case.
- `analysis/generated/ghidra/length4-focused-helpers.log`: reader `u64`,
  reader blob và ba bộ giải của `0xE1`.
- `analysis/generated/ghidra/length4-request-callers.log`: request rỗng
  `0xC4/0xE1`.
- `analysis/generated/ghidra/c4-virtual-window-script.log`: hai call site
  virtual slot `7` của `0xC4`.
- `analysis/generated/ghidra/e1-c4-method-data-script.log`: method-data và
  caller native của hai sender.
- `analysis/generated/ghidra/e1-ready-field-accesses-script.log` và
  `bootstrap-barrier-field-accesses-script.log`: producer/consumer của ba
  readiness flag và barrier `0xDB`.
- `analysis/generated/ghidra/casee2-bootstrap-cfg-script.log` và
  `casee2-windows-script.log`: ba byte-reader, thứ tự ghi field, ba cặp
  version/cache và các nhánh request/cache của handler `0xE2`.
- `analysis/generated/ghidra/bootstrap-ui-transition-script.log`: call graph
  cục bộ của transition UI cuối nhánh `0x9E` selector `0`.
- `analysis/generated/ghidra/case9e-selector0-cfg-script.log`: CFG bounded của
  selector `0`, gồm các call site tới `FUN_18031B0E0`, `FUN_18027D8D0` và
  `FUN_180419570`.
- `analysis/generated/ghidra/case9e-selector0-reader-sequence-script.log`:
  chuỗi 19 reader của selector `0`; xem tài liệu riêng để có field mapping.

Các log là output sinh tự động và bị Git ignore. Script Ghidra được chạy với
`-process GameAssembly.dll -noanalysis -readOnly`.
