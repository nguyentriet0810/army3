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
- **Confirmed:** `0x06000B66` dùng field instance `+0x68` làm chỉ số
  qua các phần tử của hai mảng ngoài, lấy một cặp `short[]`, thêm
  object mới vào `ArrayList` rồi tăng chỉ số. IL khôi phục nối
  `0x06000B65/0x06000B67` tới consumer này và `0x060007C0` tới
  `0x06000B67`. Method `0x060007C0` là `override` trên một base class
  trừu tượng; Ghidra hiện chỉ thấy data reference tới entry native
  `0x1802870F0`, không có code reference trực tiếp. Trong thân
  `0x060007C0` còn có đường duyệt/xóa phần tử `ArrayList` trước khi
  gọi `0x06000B67` trên instance tĩnh khác null. Đây là đường tiêu
  thụ tuần tự dữ liệu trong một lượt xử lý collection, chưa chứng
  minh nó chạy theo frame hoặc quyết định kết quả trận đấu.
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
- **Confirmed:** bốn mảng ngoài được cấp phát theo thứ tự A–D ở
  `0x18022B678`, `0x18022B6C5`, `0x18022B712`, `0x18022B75F`;
  method `0x0600042E` chuyển chúng theo đúng thứ tự vào bốn field
  `+0x48/+0x50/+0x58/+0x60`. Vùng parser có hai chế độ theo một
  byte payload: một chế độ dùng cặp đầu làm giá trị gốc/bước tăng
  để tích lũy vào cặp sau; chế độ kia đọc cặp sau trực tiếp dưới dạng
  16-bit. Giá trị `0x31` của **byte payload khác** chỉ chọn cách đọc
  phần tử cuối trong chế độ thứ nhất. Chi tiết địa chỉ và giới hạn ở
  [khảo sát hai entry](m3-case16-54-arrays.md).
- **Confirmed (phép kiểm tra âm có giới hạn):** trong thân ISIL khôi phục
  của `0x06000B66` (tạo object hình học) và `0x06000B67` (consumer
  gọi `0x06000B66`), không có lời gọi trực tiếp tới type transport
  chứa `TcpClient`, `NetworkStream` và `BinaryWriter` (`0x0600028D`
  là method kết nối của type đó). Disassembly của đúng hai method này
  cũng không có direct `call` tới ba điểm đã xác định trên đường gửi
  `0x1804E2520`, `0x1804E02F0`, `0x1804E1B60`. Đây **không** phải
  bằng chứng rằng client không gửi kết quả: lời gọi gián tiếp, method
  được gọi tiếp, code chưa khôi phục và những đường xử lý khác đều nằm
  ngoài phép kiểm tra.
- **Confirmed (khảo sát một tầng):** các lời gọi có tên trong ISIL của
  `0x06000B67` trỏ tới bảy type ứng dụng ngoài chính nó. Quét file ISIL
  của các type này theo tên type transport, `TcpClient`, `NetworkStream`,
  `BinaryWriter` và ba địa chỉ gửi ở trên chỉ cho hai lần nhắc tới
  type transport trong **một method khác** của type chứa hai callee
  `lIlIIllIlllIlIlIlIIllllIIllIlIllIlIIIlIlIIlIlIllIlllIlllllIllllIlIIIlIlI`
  và `lIllIIIIIllIllIllllIIlIlIIIllllIIIllIIlIIIIIIIlIlIlIIlIllIllllIIlIlllIII`.
  Hai lần nhắc đó ở method nhận ba `string` và một `sbyte`, không phải
  hai callee vừa nêu. Việc quét theo type vẫn không chứng minh đường
  gọi sâu hơn hoặc virtual call không tới transport.
- **Confirmed (đồ thị IL khôi phục):** method `0x0600028F` của type
  transport nhận một object message và gọi method `Add` của hàng đợi
  nested type; method nested này dùng `Monitor.Enter/Exit` và
  `List<T>.Add`. Đây là điểm enqueue phía gửi, trước worker
  `0x1804E2520`, không phải lời gọi socket trực tiếp. Quét 3.127 method
  cho 108.726 call/string event rồi lần cạnh `call`, `callvirt`,
  `newobj`, `ldftn`, `ldvirtftn` theo token đến độ sâu 12: từ
  `0x06000B66`, `0x06000B67`, `0x060007C0` đều **không tìm được**
  đường tới `0x0600028F` trong phần IL khôi phục. Số node thăm lần
  lượt là 52, 95, 356; độ sâu xa nhất 6, 7, 9 và không node nào bị
  cắt bởi giới hạn 12. Tương ứng còn 0, 1, 85 call event không ánh xạ
  vào method trong assembly. Thuật toán bảo thủ nối mọi overload trùng
  tên, nên có thể tạo cạnh thừa chứ không chứng minh đầy đủ cạnh thật.
- **Confirmed (đối chiếu native):** Ghidra ánh xạ `0x06000B67` vào
  `FUN_1804098B0`; function này có xref `UNCONDITIONAL_CALL` từ
  `0x180287C4E` trong consumer `0x060007C0` và nhiều direct call
  tới `0x180407C90` (`0x06000B66`). Nested queue `Add` mà
  `0x0600028F` gọi nằm ở `FUN_1804E23C0`. Đối chiếu này xác nhận
  các cạnh dương, không khép kín các cạnh virtual/indirect còn thiếu.

## Diễn giải và giới hạn

- **Inferred:** client có xử lý hình học/toạ độ cục bộ. Một khả năng là
  định vị hoặc trình diễn đối tượng chuyển động, nhưng chưa phân biệt
  được hiển thị với luật mô phỏng có thẩm quyền.
- **Confirmed (cấu trúc):** entry `0x16/0x54` cùng vào
  `0x18022ADB0` và có đường đi tĩnh tới call site
  `0x18022D28F`. Đoạn code đọc giá trị 16-bit từ buffer message rồi
  ghi vào các mảng; xem [khảo sát hai entry](m3-case16-54-arrays.md).
- **Unknown:** nơi tính quỹ đạo, va chạm, trúng đích, sát thương, địa
  hình và trạng thái trận cuối cùng. Đã thấy dữ liệu mảng được giải mã
  từ message, nhưng chưa biết ý nghĩa mảng hoặc server có chấp nhận
  kết quả mô phỏng của client hay không.
- **Unknown:** object được tạo từ hai mảng A/B có kích hoạt gửi message
  qua một tầng khác hay không. Kết quả âm ở hai method tiêu thụ trực
  tiếp chưa phân định trách nhiệm mô phỏng của client/server.
- **Inferred:** nhánh `0x16/0x54` tương thích với giả thuyết server cấp
  dữ liệu hình học để client tiêu thụ/hiển thị. Không nâng giả thuyết
  này thành phân vai thẩm quyền: graph IL bỏ sót cả một cạnh đã thấy
  trong native (`0x060006DC` gọi `0x0600042E`), và virtual/indirect
  call hoặc native code không khôi phục có thể đi tới đường gửi.
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

Phép kiểm tra đường gửi dùng hai method liên tiếp trong file ISIL
`llIIlIllllIIIIIIIIIIllllllIIIIlIIIII/lIlIIIlIIIIIIlIlIIlIllIIIIlIllllIIIllIlIlIIllllIIIlIIIlllIllIIlllIIIlIII.txt`
(method `0x06000B66` bắt đầu gần dòng 2061, `0x06000B67` gần dòng
2790, method kế tiếp gần dòng 8766). Đối chiếu các dòng `Call`/`CallVoid`
với type transport được ánh xạ ở
[báo cáo transport](m3-native-transport.md), rồi tìm các địa chỉ gửi
trên dòng `call` native trong đúng hai đoạn method. Không dùng kết quả
âm này để loại trừ các cạnh gọi gián tiếp. Với khảo sát một tầng, lấy
các `Call`/`CallVoid` ứng dụng trong `0x06000B67`, tìm bảy file ISIL
theo tên type, rồi đối chiếu các match với ranh giới `Method:` trong
từng file; hai match type transport của file
`llllIIIlllIllIIIlIIIIlIIlIIIllIIIlIIIlIlIlllIlIIlllIIIllIlIIlllIlIlllIlI.txt`
đều ở method bắt đầu gần dòng 1914, không phải hai callee bắt đầu gần
dòng 71 và 8631.

Để kiểm tra sâu hơn bằng IL khôi phục (hai file TSV nằm trong thư mục
bị Git ignore), chạy:

```powershell
./scripts/inspect-il-calls.ps1 -TypeName '*' -TargetPattern '.*' -OutputPath 'analysis/generated/m3/all-il-calls.tsv'
./scripts/trace-il-reachability.ps1 -CallsPath 'analysis/generated/m3/all-il-calls.tsv' -StartTokens '0x06000B66','0x06000B67','0x060007C0' -TargetToken '0x0600028F' -MaxDepth 12
```

Đối chứng dương: `0x06000B67 -> 0x06000B66` và
`0x06000054 -> 0x0600028F` đều được tìm thấy. Đối chứng về giới hạn: cạnh native đã
xác nhận `0x060006DC -> 0x0600042E` lại **không** hiện trong đồ thị
IL khôi phục. Vì vậy kết quả âm ở trên chỉ áp dụng cho đồ thị được
Cpp2IL khôi phục, không phải toàn bộ native binary.
Ghidra log đọc-only tương ứng:
`analysis/generated/ghidra/geometry-send-native-script.log`.

Output Cpp2IL chứa placeholder và có method bị bỏ qua. Bước tiếp theo
là kiểm tra native/virtual dispatch của các nhánh còn thiếu, tìm nơi
hai field mảng sau được dùng, đường ghi/đọc HP và biến đổi địa hình,
rồi mới phân vai client/server.
