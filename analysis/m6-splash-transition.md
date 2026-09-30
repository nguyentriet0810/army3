# M6: Đường chuyển khỏi splash qua command `0xC4`

Phân tích này dùng đúng bản `GameAssembly.dll` đã kiểm kê ở M1. Các địa chỉ
native chỉ đúng cho bản client đó. Kết quả tĩnh được đối chiếu bằng bản sao
client chạy cô lập firewall, chỉ kết nối server loopback; không liên hệ server
bên thứ ba.

## Kết luận

`Confirmed`: command `0xC4`, selector `0` chọn một trong hai lifecycle dựa
trên so sánh revision server với giá trị cache `vcBig`:

- mismatch gọi direct activation của object `UI manager +0x70`, mở flow tải
  dữ liệu và gửi request `0xC4` rỗng;
- cache-hit gọi virtual activation slot `7` của cùng object, không gửi request
  tải và cho phép UI tiếp tục tới singleton login.

Runtime cô lập ngày 2026-09-29 xác nhận cả hai nhánh. Sau cache-hit và thao
tác UI, client đặt `appReady=1`, xóa splash pointer, phát `0xC6`, rồi phát
`0xDB` khi reconnect. Lần chạy cuối xác nhận server mới chấp nhận cả hai
command và giữ nguyên socket với heartbeat; blocker M6 đã được gỡ.

## Chuỗi địa chỉ đã xác nhận

```text
jump table 0x180256C88, command 0xC4
  -> case entry 0x18020FE72
  -> selector == 0
  -> compare revision payload với revision local key vcBig
  mismatch -> CALL 0x1801961E0 tại 0x1802103A6
           -> FUN_180195EE0 -> FUN_1804E5720 -> FUN_1804E76B0
  cache-hit -> FUN_1800028E0(slot 7, target)
            -> live vtable +0x1A8 = FUN_180195570
            -> setup target và writer current-screen
```

`MapTargetsToJumpTableCases.java` đi 431 instruction từ entry `0xC4` tới
call-site `0x1802103A6`, không gặp lỗi decode hoặc indirect branch.
`TracePseudoReachability.java` xác nhận một đường dài 167 instruction từ
entry tới call-site đó.

## Payload tối thiểu của nhánh activation

Trước call activation, đường đã xác nhận đọc:

```text
[selector:s8 = 0]
[revision:s8]
[textLength:u16 BE]
[text:utf8 bytes]
```

- `FUN_1801A0520` chuyển tới byte-reader `FUN_1801A0450`.
- `FUN_1801A07C0` chuyển tới `FUN_1801A0680`; hàm này đọc độ dài hai byte
  big-endian, đọc đúng số byte và dựng string.
- `selector != 0` không đi vào đường activation trên.
- `revision` được ghi vào static field `+0x304` của type
  `DAT_1814545E8`.
- `text` được ghi vào instance field `+0x50` của object màn hình
  `UI manager +0x70`.
- Client lấy một signed byte local bằng key string index `0x40C`; nếu không
  có giá trị thì helper trả `-1`.
- `revision != localRevision` đi thẳng tới `FUN_1801961E0`.
- `revision == localRevision` đặt target flag `+0x84=1` rồi gọi
  `FUN_1800028E0(7, target)`. Đây là generic vtable dispatcher; số `7` không
  phải UI event code.

Vì `0xC4` thuộc nhóm outer-length 32-bit, wire payload rỗng-text nhỏ nhất có
dạng logic:

```text
00 RR 00 00
```

`RR` phải bằng revision local để dùng cache-hit. Trong cache của phiên test,
file `vcBig` chứa signed byte `0`, nên server dùng revision `0`. Giá trị này
phụ thuộc cache máy test, không phải hằng protocol.

## Selector tải resource

Hai nhánh nonzero đã được xác nhận tĩnh:

```text
selector 1: [01][resourceVersion:u8][itemCount:u16 BE]
selector 2: [02][key:string16][length:u32 BE][bytes:length]
```

Selector `1` khởi tạo tổng item. Mỗi selector `2` ghi byte-array theo key vào
storage local, tăng bộ đếm và cập nhật phần trăm. Item cuối ghi marker `vcBig`
rồi gọi lifecycle tiếp theo. Một thử nghiệm với key giả và một zero byte đã
đi hết bộ đếm nhưng client crash trong `UnityPlayer.dll` sau đó. Vì payload
resource hợp lệ chưa biết, server không phát selector `1/2` giả.

## Writer `UI manager +0x50` và command liên quan

Các writer trực tiếp đã rà:

| Writer | Vai trò | Liên kết packet |
| --- | --- | --- |
| `FUN_180185E80` | khởi tạo/base screen | không có edge command trực tiếp |
| `FUN_180186DA0` | quay lại/khôi phục màn hình | không có edge command trực tiếp |
| `FUN_180189640` | input/update đóng hoặc quay lại | không có edge command trực tiếp |
| `FUN_1804E76B0` | writer chuyển màn hình chung | `0xC4`; `0x9E/selector 0` qua wrapper |
| `FUN_1804F2490` | dựng modal/timed screen | `0x6E`, `0xEF` |

Phân loại:

- `0xC4`: `Confirmed` đi tới target `UI manager +0x70`; mismatch mở resource
  flow, cache-hit đi qua virtual activation của target.
- `0x6E`, `0xEF`: `Confirmed` đi tới timed/modal constructor; không coi là
  chuyển bootstrap/login.
- `0x9E/selector 0`: `Confirmed` đi tới một screen transition sau khi
  bootstrap data sẵn sàng; không phải ứng viên đầu tiên ở splash.

Quét raw toàn vùng dispatcher `0x1801FCAB0..0x180256C88` không tìm thấy lời
gọi trực tiếp tới activation slot `+0x1A8`, vì nhánh cache-hit đi qua generic
dispatcher `FUN_1800028E0`. Vtable runtime nối slot này với `FUN_180195570`.

## Ràng buộc runtime

Server chỉ gửi selector `0` đúng một lần sau initial `0xBB`. Với cache-hit,
revision phải khớp `vcBig`; mismatch sẽ vào flow download mà local server chưa
có resource hợp lệ. Server vẫn accept request `0xC4` rỗng để quan sát mismatch
an toàn, nhưng không replay response thành vòng activation.

## WWW không phải command chuyển màn hình

`Confirmed`: splash update sau timer gọi một helper `UnityEngine.WWW`. Callback
của helper lọc chuỗi kết quả rồi gọi `FUN_180194290`, nhưng hàm này không dùng
tham số string; nó giải hai byte-array nhúng sẵn để dựng endpoint, đặt port
`19150` và gọi connect. Đường này không ghi current screen. Vì vậy WWW là một
trigger của endpoint/connect lifecycle, không phải packet server chủ động
chuyển khỏi splash.

## Đối chiếu runtime 2026-09-29

Phiên mismatch dùng revision `127` (`00 7F 00 00`): current screen thành target
`+0x70`, client mở "Đang tải dữ liệu" và gửi `0xC4` rỗng. Đây là update path,
không phải đường mong muốn để dùng cache local.

Phiên cache-hit dùng revision `0`, khớp `vcBig=0`:

- client không gửi request tải `0xC4`;
- inspector đọc `cached +0x300 == revision +0x304 == 0` và target flag
  `+0x84=1`;
- sau thao tác UI, current screen bằng singleton login; activation slot live
  có RVA `0x43BDD0`, splash pointer bằng `0`, `appReady=1`, ba readiness flag
  đã reset về `0`;
- client gửi `0xC6` payload ba byte và, sau reconnect, gửi `0xDB` rỗng.

Server cũ đóng kết nối ở cả `0xC6` và `0xDB` vì state machine chưa nhận diện
hai command này. Server mới đã được xác minh runtime: cùng socket tiếp
tục nhận heartbeat sau hai command và trong suốt thao tác `Chơi mới`.

## Event kế tiếp từ màn hình `+0x70`

`Confirmed` từ `FUN_180193340`: setup của object `+0x70` tạo từ ba đến năm
control. Control index `0` gắn UI event `3`; khi field instance `+0x38 == 0`,
control index `1` gắn UI event `7`.

`Confirmed` từ `FUN_1801971A0`:

- event `3` lấy singleton bằng `FUN_18043BCA0`, gọi virtual activation slot
  `+0x1A8`, rồi tiếp tục nhánh preference/connection setup;
- event `7` cũng lấy singleton và gọi đúng activation slot đó, nhưng không
  đi qua phần setup bổ sung của event `3`;
- concrete activation `FUN_18043BDD0` của singleton xóa splash field
  `UI manager +0x58`, chạy setup của chính nó và gọi writer chuyển màn hình;
- barrier `FUN_18043D800` chỉ được tick trong lifecycle của singleton này.

Runtime sau thao tác UI xác nhận singleton trở thành current screen, splash bị
xóa và `appReady` được đặt. Exact label-to-event mapping vẫn `Inferred`, vì
inspector chỉ xác nhận layout control trên target và thao tác được quan sát ở
cấp state/packet.

## Command sau barrier

Sender `FUN_180313A10` tạo command `0xC6`, ghi một `string16`, gọi helper chỉ
đảm bảo capacity, rồi append literal byte `1`. Payload runtime dài ba byte,
phù hợp vector chuỗi rỗng:

```text
00 00 01
```

`0xDB` là request rỗng đã biết từ barrier. Server phải chấp nhận `0xC6` trong
`BOOTSTRAP` và chấp nhận `0xDB` cả trong `BOOTSTRAP` lẫn
`AWAIT_INITIAL_BB`, vì reconnect runtime có thể phát `0xDB` ngay sau
`0xA9/0` mà không gửi `0xBB` mới.

## Mức chắc chắn còn lại

- `Confirmed`: schema selector `0/1/2`, cache compare, hai activation path,
  transition runtime tới singleton login, barrier `appReady`, `0xC6` schema
  và request `0xDB`.
- `Inferred`: exact label của control đã kích hoạt event `3` trong UI target.
- `Unknown`: ý nghĩa nghiệp vụ của revision/text, nội dung resource hợp lệ,
  tên chính thức của màn hình `+0x70` và ý nghĩa string trong `0xC6`.

