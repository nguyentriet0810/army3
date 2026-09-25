# M3: response `0x9E` selector `0`

Phân tích tĩnh trên bản client đã hash ở M1. Không chạy client và không liên
hệ server bên thứ ba. Tên field trong tài liệu là alias mô tả theo offset,
không phải tên nghiệp vụ đã khôi phục.

## Vị trí trong luồng

`Confirmed`: `FUN_18031AE70` gửi command `0x9E` với một byte payload bằng
`0`. Handler response đọc selector trước khi vào nhánh selector `0` tại
`0x180249830`.

`Confirmed`: nhánh này đọc đúng 19 giá trị sau selector. Không có count hay
vòng lặp đọc record; đây là một record duy nhất được áp vào nhiều
object/collection cùng tra bằng byte đầu tiên.

`Inferred`: gọi byte đầu là `recordKey` vì nó liên tục được sign-extend rồi
dùng làm chỉ số tra collection. Chưa đủ bằng chứng gọi nó là character ID,
player ID hay slot nhân vật.

## Schema theo thứ tự wire

Reader `FUN_1801A0540` và `FUN_1801A05A0` ghép số theo big-endian. Caller
thường sign-extend kết quả 16-bit trước khi lưu, nên bảng phân biệt kiểu wire
với cách dùng semantic.

| # | Offset động | Kiểu wire | Cách dùng đã xác nhận |
| ---: | --- | --- | --- |
| 0 | `0` | `u8` | `recordKey`, dùng để tra nhiều collection |
| 1 | `1` | `u32 BE` | ghi dword vào field `+0xBC` |
| 2 | `5` | `string16` | ghi reference string vào field `+0x1C0` |
| 3 | `7 + N` | `u16 BE` | sign-extend rồi ghi dword `+0x34` của một object được chọn |
| 4 | `9 + N` | `u32 BE` | ghi dword `+0x380` |
| 5 | `13 + N` | `u16 BE` | ghi word `+0x320` |
| 6 | `15 + N` | `u16 BE` | ghi word `+0x322` |
| 7 | `17 + N` | `u16 BE` | ghi word `+0x324` |
| 8 | `19 + N` | `u16 BE` | ghi word `+0x328` |
| 9 | `21 + N` | `u16 BE` | ghi word `+0x32A` |
| 10 | `23 + N` | `u16 BE` | ghi word `+0x326` |
| 11 | `25 + N` | `u8` | sign-extend rồi ghi dword `+0x1DC` |
| 12 | `26 + N` | `u8` | ghi boolean `(value == 1)` vào byte `+0x334` |
| 13 | `27 + N` | `u8` | ghi byte `+0x30` |
| 14 | `28 + N` | `i32 BE` | sentinel; so sánh trực tiếp với `-1` |
| 15 | conditional | `i16 BE` | chỉ có khi field 14 khác `-1`; ghi dword `+0x14` của object lồng |
| 16 | dynamic | `u8` | ghi byte `+0x57` của object được chọn |
| 17 | dynamic | `i16 BE` | tọa độ `x`; helper grid chia cho `24` |
| 18 | dynamic | `i16 BE` | tọa độ `y` ban đầu; client có thể tăng để tìm cell hợp lệ |

Trong bảng, `N` là số byte encoded của string, không phải số ký tự. `string16`
có dạng:

```text
[byteLength:u16 BE] [encodedBytes:byteLength]
```

Reader sau đó gọi virtual decoder với mode `0`; encoding cụ thể vẫn
`Unknown`.

Schema compact sau selector:

```text
[recordKey:u8]
[field1:u32 BE]
[textLength:u16 BE] [text:textLength bytes]
[field3:u16 BE]
[field4:u32 BE]
[field5:u16 BE] ... [field10:u16 BE]
[field11:u8] [field12:u8] [field13:u8]
[optionalId:i32 BE]
if optionalId != -1:
    [optionalValue:i16 BE]
[field16:u8]
[field17:i16 BE]
[field18:i16 BE]
```

Phần body sau selector dài `37 + N` byte khi `optionalId == -1`, hoặc
`39 + N` byte khi có `optionalValue`. Nếu tính cả selector, payload dài
`38 + N` hoặc `40 + N` byte.

## Record tùy chọn và hậu xử lý

`Confirmed`: field 14 được so với `-1` tại `0x18024B2D3`. Khi khác `-1`,
handler tạo/gắn một object lồng ở field `+0x48`, lưu field 14 vào dword
`+0x34` của record được chọn, rồi mới đọc field 15 và lưu giá trị sign-extend
vào dword `+0x14` của object lồng. Khi bằng `-1`, field 15 hoàn toàn không có
trên wire.

`Confirmed`: field 17 là tọa độ `x`; field 18 khởi tạo tọa độ `yCandidate`.
`FUN_18041C450` ánh xạ cặp này vào cell grid bằng
`x / 24 + (y / 24) * width`. Client có thể tăng `yCandidate` từng đơn vị,
kiểm tra bit cell `0x4` và giới hạn ở `1000`. Lời gọi `FUN_18031B0E0` tại
`0x18024C19E` vì vậy gửi `x` và **tọa độ y dẫn xuất**, không nhất thiết gửi y
nguyên bản, dưới dạng `0x9E` selector `2`. Response và đường correction được
ghi tại [m3-command-9e-selector2.md](m3-command-9e-selector2.md).

`Confirmed`: sau hydrate/placement, nếu byte instance `+0x2DD` khác zero,
handler có
đường gọi `FUN_18027D8D0(0)` và `FUN_180419570`, dẫn tới transition UI đã ghi
trong [client-state-machine](../docs/client-state-machine.md). Bằng chứng
tọa độ/grid khiến tên “main menu/lobby” không còn đủ mạnh; scene đích vẫn
`Unknown`.

## Giới hạn kết luận

- Sáu word liên tiếp ở `+0x320..+0x32A` trông giống một cụm chỉ số, nhưng tên
  từng chỉ số vẫn `Unknown`.
- Các offset giống nhau có thể thuộc object khác nhau được tra bằng cùng
  `recordKey`; không hợp nhất chúng thành một struct khi chưa xác nhận type.
- Chưa có capture hợp pháp hoặc test server cục bộ để xác thực range và điều
  kiện runtime.

## Chứng cứ tái lập

- `scripts/ghidra/SummarizeReaderSequence.java`: duyệt CFG bounded và liệt kê
  19 call reader theo địa chỉ.
- `scripts/ghidra/InspectPseudoCallWindows.java`: in cửa sổ pseudo-disassembly
  quanh reader, sentinel và call hậu xử lý.
- `scripts/ghidra/FindPseudoInstructions.java`: lần mọi use của stack slot giữ
  field 17, field 18 và biến dẫn xuất trong CFG.
- `analysis/generated/ghidra/case9e-selector0-reader-sequence-script.log`:
  thứ tự 19 reader.
- `analysis/generated/ghidra/case9e-selector0-read-windows-script.log`,
  `case9e-selector0-tail-windows-script.log` và
  `case9e-optional-record-script.log`: field write và nhánh sentinel.
- `analysis/generated/ghidra/case9e-selector0-cfg-script.log`: inventory call,
  write và compare của toàn nhánh selector `0`.

Các log sinh tự động bị Git ignore. Mọi script được chạy read-only trên project
Ghidra với `-process GameAssembly.dll -noanalysis -readOnly`.
