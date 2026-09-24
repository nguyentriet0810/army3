# M3: Nguồn host/port và bước chọn server

Phân tích tĩnh trên đúng bản client đã hash ở M1. Không chạy client hoặc liên
hệ server bên thứ ba. File ISIL và log Ghidra nằm ở `analysis/generated/` và
không được đưa vào Git.

## Đường dữ liệu đã xác nhận

Type metadata có tên bị làm rối
`lllIIlIIIlIIllIllllIllIlIlIIlIIlIlll.llllIllIllllllIllIlllIIlllIIIIIIIlIlllIIllllllIllIllIlllIIIlllllllllIIIl`
có field tĩnh `string` tại offset `+0x20` và `int` tại `+0x28`. Trong ISIL của
caller `0x060001C1`, hai field này được truyền vào method transport
`0x0600028A`. Ghidra đối chiếu caller thành `FUN_18043BEA0`, với call native
`FUN_1804DF040` nhận cùng hai field; cờ kết nối `+0x30` của transport được
kiểm tra trước lời gọi.

Static initializer của type endpoint là `FUN_1801B2260`:

- `Confirmed`: gán field host từ hàm giải mã chuỗi `FUN_1801BA350(0x612)`
  (chỉ số 1554), chưa giải được giá trị chuỗi.
- `Confirmed`: gán field port `0x4ACE`, tức **19150** ở hệ thập phân. Đây là
  *port khởi tạo*, không phải cam kết mọi phiên đều dùng port này.

Rà 351 tham chiếu tới class pointer `DAT_181454640` trong project Ghidra phân
tích từng phần cho 76 function; 75 decompile thành công. Ngoài initializer,
có lệnh ghi cả host và port trong `FUN_180194290`, `FUN_1804FBEE0`,
`FUN_180195900`, `FUN_1801971A0`. Phép rà dựa trên text decompile và project
chưa phân tích hoàn chỉnh, nên danh sách này không bảo đảm đầy đủ mọi đường
ghi gián tiếp.

## Lựa chọn endpoint

`Confirmed` trong decompile native:

- `FUN_180194290` tạo các mảng một phần tử: một mảng host và một mảng port;
  đặt port phần tử đầu là `0x4ACE`. Static initializer tạo hai mảng byte
  dài 14 và 13; hàm này gọi `Encoding.UTF8.GetString` để tạo các chuỗi
  từ chúng, rồi copy host/port của phần tử đầu sang field endpoint.
- `FUN_1804FBEE0` lấy một chỉ số được lưu, kiểm tra giới hạn mảng, gán
  `hosts[index]` và `ports[index]` vào field endpoint, rồi gọi
  `FUN_18043BEA0` — chính caller kết nối ở trên. Đây là bằng chứng cho bước
  **chọn endpoint → yêu cầu kết nối** trong code, chưa xác định tên màn hình.
- `FUN_180195900` cũng dùng chỉ số đã chọn để gán cặp host/port từ hai mảng.
  Trong `FUN_1801971A0`, nhánh `*param_2 == 6` lấy một chỉ số từ field
  `+0x88` của class `DAT_181454620`, gán vào chỉ số chọn `+0x58` của
  `DAT_181454550`, rồi chép cặp `hosts[index]`/`ports[index]` vào endpoint.
  Sau đó gọi `FUN_180193340` và `FUN_18043BEA0`. Đây là đường chọn endpoint
  thứ hai đã xác nhận bằng decompile, có thể đi tới yêu cầu kết nối.

### Nguồn của sự kiện `6`

`Confirmed` từ ISIL và decompile native:

1. Trong `FUN_1801971A0`, một nhánh duyệt mảng `string[]` ở offset tĩnh
   `+0x0` của `DAT_181454550`. Mỗi chuỗi được truyền vào constructor
   `FUN_18044B180` của thành phần tương tác, cùng `this` làm callback và
   hằng số `6` làm mã sự kiện (`r9d=6`). Các mục được thêm vào cùng một
   container. Mảng này là **nhãn hiển thị**; host và port nằm ở hai mảng
   khác tại `+0x8` và `+0x10`.
2. Thành phần tương tác lưu callback và mã sự kiện trong field instance
   `+0x28` và `+0x30`. Method tại `FUN_18044B640` chuyển hai giá trị này
   vào lời gọi dispatch interface. Method triển khai interface của class
   chọn server là `FUN_180195DE0`; nó đóng gói tham số `int` và `object`,
   rồi gọi `FUN_1801971A0`.
3. Vì vậy đường gọi cụ thể `widget → callback(int=6) → handler → chọn
   host/port → yêu cầu kết nối` là code client cục bộ, **không phải** bằng
   chứng cho command ID `6` của giao thức mạng.

`Inferred`: thành phần trên là mục chọn server trong UI dựa vào nhãn,
container, callback và mảng host/port đi kèm. `Unknown`: thao tác người dùng
nào kích hoạt method dispatch, tên màn hình/scene thực tế và hành vi runtime
khi danh sách được thay đổi.

Trên file binary, hai ô tham chiếu dữ liệu mảng chứa handle metadata `0xE00003D1`
và `0xE00003EF`, không phải con trỏ tới byte array có thể đọc trực tiếp
trong project Ghidra. Vì vậy giá trị host chưa được giải mã từ client gốc.

`Inferred`: hai mảng và chỉ số tương ứng với danh sách server/chọn server vì
chúng được dùng nguyên cặp để khởi tạo kết nối. Không suy ra rằng toàn bộ danh sách
được nhúng trong client, tải từ server, hay chỉ có một server trong mọi phiên.

`Unknown`: chuỗi mặc định tại chỉ số `0x612`; liệu nó có bằng IP ứng viên
`14.225.206.44` tìm thấy ở M1 hay không; nguồn và thứ tự ưu tiên các đường
ghi đè; trường hợp người dùng chọn endpoint nào ở runtime; login/lobby sau
kết nối. Không dùng IP ứng viên để thử kết nối.

## Tái lập bằng công cụ hiện có

ISIL type endpoint:
`analysis/generated/cpp2il/isil/IsilDump/Assembly-CSharp/lllIIlIIIlIIllIllllIllIlIlIIlIIlIlll/`
và ISIL caller dưới namespace `lllllIIIIIlllIIIIIIlIlIIIllIIIIIIlII`.
Ghidra chạy script chỉ đọc `InspectNativeTargets.java` với các địa chỉ
`18043BF09`, `1801B2260`, `180194290`, `1804FBEE0`, `180195900`;
`InspectDataReferences.java` và `InspectEndpointWrites.java` nhận địa chỉ
`181454640`. `InspectDecompileWindow.java` nhận `1801971A0` và
`DAT_181454640` để in cửa sổ decompile quanh đường gán endpoint; log lưu ở
`analysis/generated/ghidra/endpoint-branch-script.log`. Xref của handler và
hai caller trực tiếp nằm trong `endpoint-event-callers.log` và
`endpoint-event-sources.log` cùng thư mục. ISIL của class chọn server có
constructor call `0x18044B180` với `r9d=6` gần dòng 16135; ISIL của
thành phần tương tác có method dispatch tại `0x18044B640`.
