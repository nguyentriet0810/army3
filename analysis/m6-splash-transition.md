# M6: Đường chuyển khỏi splash qua command `0xC4`

Phân tích này dùng đúng bản `GameAssembly.dll` đã kiểm kê ở M1. Các địa chỉ
native chỉ đúng cho bản client đó. Không chạy client và không liên hệ server
bên thứ ba trong bước này.

## Kết luận

`Confirmed`: trong dispatcher packet chính, command logic `0xC4` có một nhánh
selector `0` đi tới activation của object màn hình tại `UI manager +0x70`.
Activation này gọi writer chung và thay `UI manager +0x50` (current screen),
do đó có thể đưa client ra khỏi splash tại `UI manager +0x58`.

Đây là command server-push có đường điều khiển trực tiếp và ngắn nhất đã tìm
được từ jump table tới writer current-screen. Nó là ứng viên kiểm chứng M6,
chưa được nâng thành hành vi runtime cho tới khi client thật đi qua nhánh.

## Chuỗi địa chỉ đã xác nhận

```text
jump table 0x180256C88, command 0xC4
  -> case entry 0x18020FE72
  -> selector == 0
  -> compare revision payload với revision local
  -> CALL 0x1801961E0 tại 0x1802103A6
  -> FUN_180195EE0
  -> FUN_1804E5720
  -> FUN_1804E76B0
  -> ghi UI manager static field +0x50
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
- Chỉ nhánh `revision != localRevision` mới đi thẳng tới
  `FUN_1801961E0` theo đường tối thiểu đã nêu.

Vì `0xC4` thuộc nhóm outer-length 32-bit, wire payload rỗng-text nhỏ nhất có
dạng logic:

```text
00 RR 00 00
```

Trong đó `RR` phải khác revision local. Chọn một hằng số cụ thể cho local
server vẫn là quyết định thử nghiệm `Inferred`, không phải protocol fact.

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

- `0xC4`: `Confirmed` đi tới activation của `UI manager +0x70` và writer
  chung. Đây là ứng viên splash-exit.
- `0x6E`, `0xEF`: `Confirmed` đi tới timed/modal constructor; không coi là
  chuyển bootstrap/login.
- `0x9E/selector 0`: `Confirmed` đi tới một screen transition sau khi
  bootstrap data sẵn sàng; không phải ứng viên đầu tiên ở splash.

Quét raw toàn vùng dispatcher `0x1801FCAB0..0x180256C88` không tìm thấy lời
gọi trực tiếp nào tới virtual activation slot `+0x1A8`. Edge `0xC4` dùng
concrete activation `FUN_1801961E0`, nên không mâu thuẫn với kết quả âm này.

## Ràng buộc cho thử nghiệm runtime

`Confirmed` từ control flow activation:

1. `FUN_1801961E0` reset cờ one-shot `+0x78` về `0`.
2. Nó gọi `FUN_180195EE0`, dẫn tới UI event `2`.
3. Event `2` có thể gửi một request `0xC4` rỗng và đặt `+0x78 = 1`.
4. Sau đó activation mới gọi writer chuyển màn hình.

Vì vậy local server khi thử server-push `0xC4` phải chấp nhận request `0xC4`
rỗng do client gửi lại. Không nên tự động trả cùng response vô hạn, vì mỗi
lần activation lại reset cờ one-shot và có thể tạo vòng request/response.

Thử nghiệm đầu tiên nên:

1. gửi đúng một response/push `0xC4` selector `0` sau khi transform đã bật;
2. chọn `revision` khác cache local đã đo hoặc dùng bản sao client với cache
   đã reset có kiểm soát;
3. dùng empty string để giới hạn payload;
4. accept-and-log request `0xC4` rỗng tiếp theo nhưng chưa trả lời;
5. đọc lại `UI manager +0x50`, `+0x58`, `+0x70` và theo dõi client có gửi
   `0xDB` hay không.

## WWW không phải command chuyển màn hình

`Confirmed`: splash update sau timer gọi một helper `UnityEngine.WWW`. Callback
của helper lọc chuỗi kết quả rồi gọi `FUN_180194290`, nhưng hàm này không dùng
tham số string; nó giải hai byte-array nhúng sẵn để dựng endpoint, đặt port
`19150` và gọi connect. Đường này không ghi current screen. Vì vậy WWW là một
trigger của endpoint/connect lifecycle, không phải packet server chủ động
chuyển khỏi splash.

## Mức chắc chắn còn lại

- `Confirmed`: command, selector, reader tối thiểu, compare revision, concrete
  activation và writer current-screen.
- `Inferred`: một revision thử nghiệm khác cache sẽ hiển thị đúng panel mong
  muốn trong runtime hiện tại.
- `Unknown`: ý nghĩa nghiệp vụ chính xác của revision/text, tên chính thức của
  màn hình `+0x70`, và payload đầy đủ của nhánh khi revision bằng cache.

