# M3: Command `0x2B` và form chín trường text

Phân tích tĩnh trên bản client đã hash ở M1. Không chạy client và không liên
hệ server bên thứ ba. Mục tiêu là kiểm tra giả thuyết `0x2B` liên quan đăng
nhập mà không gán tên nghiệp vụ chỉ từ hình dạng packet.

## Đường gửi

- `Confirmed`: method public token `0x06000AEA` nhận đúng chín tham số
  `string`. Native entry `FUN_18031D0F0` chép chúng vào một struct closure rồi
  gọi `FUN_18031F4E0`.
- `Confirmed`: `FUN_18031F4E0` tạo message logic `0x2B`, sau đó gọi
  `FUN_1802FFB00` chín lần theo đúng thứ tự field `0x00..0x40` của struct.
- `Confirmed`: `FUN_1802FFB00` encode string thành byte array qua một virtual
  encoder, ghi length bằng `FUN_1802FF7B0`, rồi ghi từng byte. Helper length
  ghi hai byte theo thứ tự byte cao trước. Encoding cụ thể chưa được ánh xạ.

Schema payload gửi đã xác nhận về cấu trúc:

```text
repeat 9 times:
    [byteLength:u16 BE] [encodedText:byteLength bytes]
```

`0x2B` không thuộc nhóm năm command dùng outer length 4 byte. Vì vậy nó đi
qua frame length 2 byte thông thường; khi transform bật, command, outer length
và payload đều tiêu thụ key theo thứ tự đã mô tả trong
[m3-packet-framing.md](m3-packet-framing.md).

## Caller UI

- `Confirmed`: caller native `FUN_180411CC0` lấy text ở field `+0x28` của
  chín input object tại `+0x38`, `+0x40`, `+0x48`, `+0x50`, `+0x58`, `+0x60`,
  `+0x68`, `+0x70`, `+0x30` rồi chuyển nguyên thứ tự vào method chín string.
- `Confirmed`: trước khi gửi, caller kiểm tra các input/object tồn tại và
  chín text khác empty string. Nếu một trường rỗng, nó đi vào đường hiển thị
  thông báo qua localization ID `0x66F`.
- `Confirmed`: action UI khác đóng/reset transport và gọi virtual slot `7`
  trên object state khác, phù hợp với thao tác hủy/quay lại nhưng tên chính
  xác vẫn `Unknown`.

Hình dạng này xác nhận `0x2B` là submit của một form chín trường bắt buộc.
Nó không giống request đăng nhập tối thiểu hai trường, nhưng vẫn có thể thuộc
luồng tạo tài khoản, tạo hồ sơ, kích hoạt hoặc bước xác thực mở rộng.

## Localization của chín trường

`Confirmed`: initializer `FUN_18040EEA0` tạo chín input với các localization
ID dưới đây. Cột cuối được sắp theo đúng thứ tự sender `0x2B` serialize:

| Input field | Localization ID | Vị trí trong payload |
| --- | ---: | ---: |
| `+0x38` | `0x725` | 1 |
| `+0x40` | `0x842` | 2 |
| `+0x48` | `0x453` | 3 |
| `+0x50` | `0x0E1` | 4 |
| `+0x58` | `0x79C` | 5 |
| `+0x60` | `0x89F` | 6 |
| `+0x68` | `0x593` | 7 |
| `+0x70` | `0x7AB` | 8 |
| `+0x30` | `0x2BC` | 9 |

Vì vậy chuỗi ID theo wire order là:

```text
0x725, 0x842, 0x453, 0x0E1, 0x79C, 0x89F, 0x593, 0x7AB, 0x2BC
```

- `Confirmed`: trong mode constructor bằng `1`, bảy field `+0x38..+0x68`
  cùng dùng label thay thế `0x214`; hai field `+0x70` và `+0x30` không đi qua
  nhánh thay thế này.
- `Confirmed`: `0x696` thuộc panel/title riêng, không phải label của một trong
  chín input. Localization `0x66F` là đường báo lỗi khi có field rỗng.
- `Unknown`: plaintext ứng với các ID. Decoder `FUN_1801BA350` lấy dữ liệu từ
  các managed array được truy cập qua metadata handle, giải mã theo seed phụ
  thuộc ID rồi cache/intern chuỗi. Các giá trị handle quan sát được không phải
  con trỏ dữ liệu thô, nên chưa thể đọc an toàn label chỉ bằng cách dereference
  trong binary.

Việc ánh xạ ID xác nhận quan hệ giữa control và payload, nhưng chưa đủ để gán
tên nghiệp vụ cho các trường nếu chưa giải được bảng localization.

## Đường nhận

- `Confirmed`: jump-table entry `169` ánh xạ command `0x2B` tới
  `0x1801FEC7D`.
- `Confirmed`: handler gọi `FUN_180458EA0`, hàm này xóa field state tĩnh
  `+0xA0`, rồi đọc đúng một byte từ payload.
- `Confirmed`: nếu object ở field state tĩnh `+0x08` chưa tồn tại, handler
  cấp phát một object UI, gọi `FUN_18040EEA0(object, leadingByte)` và lưu vào
  field đó. Sau đó nó gọi virtual slot `7` trên object này.
- `Confirmed`: theo nhánh đã lần, response không đọc thêm trường nào sau byte
  đầu.

Schema response tối thiểu:

```text
[leadingByte:byte]
```

`FUN_18040EEA0` là initializer UI lớn: nó tạo nhiều control, lấy nhiều chuỗi
localization và dùng byte đầu trong ít nhất một nhánh cấu hình. Chưa ánh xạ
được ý nghĩa từng giá trị byte hoặc tên màn hình.

## Kết luận state

- `Confirmed`: `0x2B` nối một form chín trường bắt buộc với response một byte
  và một callback hiển thị/state virtual slot `7`.
- `Inferred`: command thuộc luồng onboarding/account/profile hơn là bản thân
  transport handshake.
- `Unknown`: đây là đăng ký tài khoản, tạo nhân vật, cập nhật hồ sơ hay bước
  xác thực nào; tên chín trường; giá trị success/failure; transition tiếp theo.
- Không dùng `0x2B` làm “login command” của server localhost cho tới khi ánh
  xạ được label của form hoặc caller từ màn hình trước đó.

## Chứng cứ tái lập

- `analysis/generated/cpp2il/index/method-signatures.txt`: signature public
  chín string.
- `analysis/generated/cpp2il/isil/IsilDump/...`: struct closure và lời gọi private
  sender.
- `analysis/generated/ghidra/utf-writer-script.log`: sender `0x2B`, caller UI
  và writer length-prefixed.
- `analysis/generated/ghidra/case2b-script.log`: handler response.
- `analysis/generated/ghidra/case2b-helpers-script.log`: reset state và UI
  initializer.
- `analysis/generated/ghidra/case2b-caller-script.log`: chín input bắt buộc.
- `analysis/generated/ghidra/case2b-localization-windows-script.log`: các call
  localization và phép gán control trong initializer.
- `analysis/generated/ghidra/localization-data-pointers-script.log`: metadata
  handle và các mảng được decoder sử dụng.

Các log Ghidra được tạo ở chế độ `-noanalysis -readOnly` và bị Git ignore.
