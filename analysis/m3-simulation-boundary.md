# M3 — Ranh giới mô phỏng: khảo sát tĩnh ban đầu

**Phạm vi:** `Assembly-CSharp.dll` khôi phục bởi Cpp2IL và ISIL/native
disassembly của `GameAssembly.dll`. Không chạy client hoặc kết nối server.
Đây chưa phải kết luận client-authoritative hay server-authoritative.

## Bằng chứng đã xác nhận

- **Confirmed:** Trong 3.127 method được quét từ IL khôi phục, có 84
  call/string event khớp các API thời gian, toán học, random và physics
  đã chọn. 62 event là `Time.get_realtimeSinceStartup`. Không thấy call
  đến `UnityEngine.Physics`, `Physics2D`, `Rigidbody`, `Collider` hoặc
  `Vector2/Vector3` trong *tập IL được khôi phục và bộ lọc này*.
  Đây là kết quả âm của phép quét, không phải chứng minh client không có
  vật lý.
- **Confirmed:** Method `0x06000232` của một type bị làm rối nhận bốn
  số nguyên, trừ hai cặp tọa độ, bình phương, cộng, lấy căn và chuyển
  kết quả về số nguyên. Native disassembly ở khoảng `0x18044E230`
  thể hiện phép tính khoảng cách Euclid dạng
  `int(sqrt((x2-x1)^2 + (y2-y1)^2))`.
- **Confirmed:** Method `0x0600022F` trong cùng type nhận bốn số nguyên
  và một `sbyte`, ghi các tọa độ vào field instance `+0x20/+0x24` và
  `+0x64/+0x68`. Ở nhánh `sbyte == 0x11`, method cũng tính căn của tổng
  bình phương chênh lệch tọa độ rồi ghi các giá trị tính được vào
  `+0x6C/+0x70`. Caller từ type lớn khác là `0x06000A42`;
  method `0x0600023D` trong cùng type gọi hàm khoảng cách
  `0x06000232` hai lần.
- **Confirmed:** Method `0x06000A42` nhận hai `short[]` và một số
  tham số byte; các constructor `0x06000A3D/3E/3F` gọi method này.
  Trong một nhánh nó tạo object tọa độ (type chứa `0x0600022F`) rồi
  truyền bốn số nguyên và một byte vào `0x0600022F`. Đây là đường
  khởi tạo/xử lý dữ liệu hình học, chưa phải bằng chứng cho va chạm.
- **Confirmed:** Method `0x06000B66` lấy hai `short[]` từ hai field
  `short[][]` của cùng một object (offset `+0x48` và `+0x50` trong
  metadata), tạo instance của type chứa `0x06000A42` và thêm instance
  đó vào một `ArrayList`. IL khôi phục chỉ tìm thấy lời gọi constructor
  này tại `0x06000B66`; điều đó không loại trừ call site bị bỏ sót.
- **Confirmed:** Handler message cấp ứng dụng `0x060006DC` /
  `FUN_1801fcab0` có lời gọi trực tiếp ở `0x18022D28F` tới
  `FUN_180525df0`, method `0x0600042E` trong metadata. Bảng
  `.pdata` của PE đặt call site trong runtime-function
  `0x1801FCAB0..0x1802570DC`. Method `0x0600042E` gọi
  `0x06000B64` để ghi bốn tham số `short[][]` vào các field
  `+0x48/+0x50/+0x58/+0x60` của object. Hai field đầu cũng được
  `0x06000B66` đọc để tạo object bên trên. Như vậy có đường cấu trúc
  từ xử lý message tới dữ liệu mảng tọa độ của client, dù điều kiện
  runtime và ý nghĩa byte lệnh chưa rõ.

## Diễn giải và giới hạn

- **Inferred:** client có xử lý hình học/toạ độ cục bộ. Một khả năng là
  định vị hoặc trình diễn đối tượng chuyển động, nhưng chưa phân biệt
  được hiển thị với luật mô phỏng có thẩm quyền.
- **Unknown:** nơi tính quỹ đạo, va chạm, trúng đích, sát thương, địa
  hình và trạng thái trận cuối cùng. Đã nối được một đường từ handler
  message tới mảng tọa độ, nhưng chưa xác định message nào, liệu mảng
  do server gửi hay được client tạo, hoặc server có chấp nhận kết quả
  client hay không.
- **Unknown:** byte command dẫn vào call site `0x18022D28F`. Hai
  entry bảng điều phối `0x16/0x54` cùng trỏ tới vùng bắt đầu
  `0x18022ADB0` gần phía trước, nhưng chỉ thứ tự địa chỉ không chứng
  minh call site thuộc riêng hai case đó: các nhánh khác có thể nhảy
  vào giữa hoặc dùng chung code.
- **Unknown:** việc không thấy Unity Physics API là do mô phỏng viết
  bằng số học riêng, do phần IL chưa khôi phục, hoặc do server đảm nhận.
  Không chọn kiến trúc server M5 dựa trên phép quét này.

## Cách kiểm tra lại

Tạo trace bỏ qua bởi Git bằng `scripts/inspect-il-calls.ps1`:

```powershell
./scripts/inspect-il-calls.ps1 -TypeName '*' -TargetPattern 'UnityEngine\.(Physics|Physics2D|Mathf|Vector2|Vector3|Rigidbody|Rigidbody2D|Collider|Collider2D|Time|Random)::|System\.Math::' -OutputPath 'analysis/generated/m3/simulation-api-calls.tsv'
./scripts/inspect-il-calls.ps1 -TypeName '*' -TargetPattern 'lIlllIllIllIlIllIIIIIIlllllIIlIlIIIlIIlIlIIlllllIlIIlIllllIIIIllIllllIII|lIIlIIIIIlllIIIIIllIlIllIlIlIIIllIlIIlIIIlIIlIIlIlllIllllIIllllllIlllIlI' -OutputPath 'analysis/generated/m3/geometry-callers.tsv'
```

ISIL gốc của hai method ở
`analysis/generated/cpp2il/isil/IsilDump/Assembly-CSharp/lIlIlIlllIllllIlIIlIlIllIIlllIIIlIlI/llllIIIlIlIlllIlIIllIIlIlIllIllIllIIIIIIIIlIIIIIIlIllIllllIIIlIllllllIIl.txt`,
bắt đầu gần dòng 1959 và 3160. Các cạnh gọi tiếp theo nằm trong ISIL
của type chứa `0x06000A42`, `0x06000B66` và `0x0600042E`.
Trace bỏ qua bởi Git:
`analysis/generated/m3/geometry-type-callers.tsv`,
`geometry-entry-callers.tsv`, `coordinate-object-constructors.tsv`,
`coordinate-config-callers.tsv` và `coordinate-config-entry.tsv`.
Ghidra script logs `coordinate-config-target-script.log` và
`coordinate-handler-pseudo-script.log` xác nhận đích hàm và lệnh
`CALL` tại `0x18022D28F`.

Output Cpp2IL chứa placeholder và có method bị bỏ qua. Bước tiếp theo
là lần nguồn của bốn mảng ở từng case của handler, tìm đường ghi/đọc HP
và biến đổi địa hình, rồi mới phân vai client/server.
