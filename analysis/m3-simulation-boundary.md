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
- **Confirmed:** hai virtual call slot `+0x178` trong `0x060007C0`
  lấy object từ hai field tĩnh cùng type tại `+0x2B0/+0x2B8` và gọi
  sibling override `0x06000A67`. Override này chọn hai nhánh
  `0x06000A6C/0x06000A6D` theo một byte trạng thái; các nhánh duyệt
  collection cục bộ và chưa cho thấy direct call tới enqueue/send.
  Cả 11 computed call của `FUN_1802870F0` đã được phân loại: hai call
  sibling override và chín thao tác collection (`Count`, `Item`,
  `Remove`); không call nào trực tiếp là enqueue/worker/serializer.
  Xem
  [khảo sát virtual dispatch](m3-virtual-dispatch.md).
- **Confirmed (cấu trúc):** hai mảng sau C/D tại `+0x58/+0x60` cũng
  được `0x06000B66` đọc theo cùng cursor. Method `0x06000A43` ghép
  chúng thành danh sách point `(C[i], D[i])`; `0x06000A62` duyệt danh
  sách theo thứ tự và so sánh point với tọa độ hiện tại của object.
  Cấu trúc này tương thích với waypoint/path nhưng chưa có tên ngữ nghĩa
  gốc. Xem [đường projectile và sát thương](m3-projectile-damage-terrain.md).
- **Confirmed:** field entity `+0x17C` là HP hiện tại và `+0x180` là
  HP tối đa: code hiển thị tính `current * 100 / max`, còn các nhánh
  trạng thái kiểm tra `current <= 0`. Method `0x0600042A` kiểm tra vùng
  chồng lấn giữa projectile và player, trừ damage của projectile tại
  `+0x68`, gọi `0x0600042B`, rồi ghi HP mới trở lại `+0x17C`.
  Caller tìm được là method update projectile `0x06000BB4`.
- **Confirmed:** entity còn có HP đích `+0x184`, cờ nội suy `+0x37C` và
  bước `+0x3A8`. `0x0600042B` thiết lập chúng trong đường damage cục bộ;
  method công khai `0x0600044A` thiết lập cùng state từ `(int, sbyte)`;
  `0x0600044B` được các vòng update entity gọi để kéo HP hiện tại về đích.
  Không có direct call/`ldftn` tới `0x0600044A` trong IL khôi phục và native
  chỉ có reference từ `.pdata` cùng một dãy code pointer trong `.data`, không
  có code xref tới ô pointer riêng. Vì vậy nguồn cập nhật qua method này vẫn
  **Unknown**; hiện thậm chí chưa có execution edge chứng minh method chạy,
  và các reference này chưa phải bằng chứng về callback mạng.
- **Confirmed (phép kiểm tra âm có giới hạn):** quét toàn handler native
  `FUN_1801FCAB0` theo displacement HP/cờ/bước chỉ gặp ba offset trùng trên
  stack, không gặp object access; handler cũng không direct-call ba helper
  `0x0600042B/44A/44B`. Điều này loại đường ghi HP trực tiếp trong dispatcher,
  nhưng không loại callback, virtual/interface dispatch hay helper trung gian.
- **Confirmed (phép kiểm tra âm có giới hạn):** các write site
  `Texture2D` đã kiểm tra là helper recolor hoặc crop/copy tài nguyên;
  chưa thấy chúng trong đường projectile, damage hoặc callback kết thúc.
  Từ bốn callback `0x06000B69/6C/6D/6E`, đồ thị IL khôi phục cũng không
  tìm được đường tới enqueue gửi hoặc hai helper ảnh chính ở độ sâu 12.
  Điều này không loại trừ buffer/mask tự quản lý hay cạnh native bị thiếu.
- **Confirmed (cấu trúc):** đường `0x06000A62 -> 0x0600080B ->
  0x060005B8` đọc một stamp ảnh qua `0x06000830`, duyệt vùng quanh tọa độ
  va chạm và ghi `0` hoặc màu thay thế vào `int[]` mask đích. Các sentinel
  màu được kiểm tra gồm `0xFF0000` và `0xFFFFFF`.
- **Strongly inferred:** phép ghi mask trên là biến đổi địa hình/tạo hố cục
  bộ. Kết luận ngữ nghĩa dựa trên tọa độ va chạm, stamp và thao tác xóa pixel;
  tên gốc của các type/method vẫn bị làm rối.
- **Confirmed (đối chiếu native):** `0x060007C0` gọi `0x06000B67` tại
  `0x180287C4E`; `0x06000B67` duyệt collection và gọi `0x06000A62` tại
  `0x180409CD6`; từ đó IL nối tiếp tới `0x0600080B -> 0x060005B8`.
  Wrapper `0x06000A52` cũng tail-call `0x06000A62`. Điều này đặt phép sửa
  mask trong đường update collection cục bộ. Cạnh `0x06000B67 ->
  0x06000A62` là một cạnh native khác bị call graph IL bỏ sót.
- **Confirmed (cấu trúc):** `0x06000407` đặt HP hiện tại và HP tối đa bằng
  cùng một giá trị; `0x060001F6` gọi nó theo lô từ năm mảng dữ liệu qua chuỗi
  `0x060007AF -> 0x060007EC -> 0x060001F6`. Chưa gắn được entry công khai
  `0x060007AF` với command mạng cụ thể.
- **Confirmed (tọa độ selector `2`):** cả sáu direct call tới sender
  `FUN_18031B0E0` đều lấy `x/y` từ selected/current entity phía client. Năm
  call trong routine movement so current `+0x84/+0x88` với snapshot
  `+0x1B2/+0x1B4`, gửi khi thay đổi rồi cập nhật snapshot; call còn lại gửi
  mirror `+0x298/+0x29C` trên đường placement sau selector `0`.
- **Confirmed (lọc self):** event chiều về thêm `entityKey`; handler tra entity
  theo key và bỏ qua nếu object đó chính là selected/current entity, trước khi
  đọc hai word tọa độ. Chỉ event của entity khác mới đi vào so sánh và state
  correction.
- **Confirmed (inventory writer):** quét toàn listing tìm sáu field tọa độ
  `+0x84/+0x88`, `+0x1D0/+0x1D4`, `+0x298/+0x29C`, rồi đối chiếu toàn bộ
  writer ứng viên với dispatcher. Không có inline write trong dispatcher; có
  13 direct call-site hợp lệ tới tám writer entity. Chúng nối tới command
  `0x15`, `0xC0`, `0x35`, `0x16/0x54`, `0x18`, `0x59`, `0xC1` và các
  selector `0/2/10` của `0x9E`. Xem
  [inventory writer tọa độ](m3-coordinate-writers.md).
- **Confirmed (hydrate `0x16/0x54`):** method `FUN_180525DF0` lấy hai word
  từ payload và đặt đồng thời current `+0x84/+0x88` cùng target
  `+0x1D0/+0x1D4`, trước khi cấu hình các mảng A–D. Đây là state vị trí do
  response cung cấp ở pha hydrate/config.

## Diễn giải và giới hạn

- **Inferred:** client có xử lý hình học/toạ độ cục bộ. Một khả năng là
  định vị hoặc trình diễn đối tượng chuyển động, nhưng chưa phân biệt
  được hiển thị với luật mô phỏng có thẩm quyền.
- **Strongly inferred:** riêng selector `0x9E/2` là publication tọa độ do
  client tạo, sau đó server gắn `entityKey` và relay/state-replicate cho các
  entity khác. Đây không phải bằng chứng cho authoritative correction của
  chính sender. Server vẫn có thể validate, clamp, thay thế hoặc từ chối tọa
  độ; logic đó không thể xác định từ client tĩnh.
- **Inferred:** tổng hợp các command writer cho thấy mô hình lai: server
  response có thể hydrate hoặc sửa vị trí, còn client tiến current về target,
  xử lý collision/movement cục bộ và publish một phần tọa độ. Chưa đủ bằng
  chứng để gắn nhãn toàn game là client-authoritative hay server-authoritative.
- **Confirmed (cấu trúc):** entry `0x16/0x54` cùng vào
  `0x18022ADB0` và có đường đi tĩnh tới call site
  `0x18022D28F`. Đoạn code đọc giá trị 16-bit từ buffer message rồi
  ghi vào các mảng; xem [khảo sát hai entry](m3-case16-54-arrays.md).
- **Confirmed:** client chứa ít nhất một đường update projectile, kiểm tra
  trúng đích dạng vùng chồng lấn và trừ HP cục bộ. Đây không còn là
  hành vi chỉ suy ra từ tên method.
- **Inferred:** C/D là waypoint/path do được ghép thành point và duyệt
  tuần tự. Chưa biết chúng là quỹ đạo gameplay, đường effect hay dữ liệu
  trình diễn khác.
- **Confirmed (công thức):** khi transform bật, raw command cho entry logic
  `C` là `((C + shift) mod 256) XOR key[recvIndex]`; khi tắt thì raw = logic.
  Vì key/index có state, `0x16/0x54` không có raw byte cố định.
- **Unknown:** command nào kích hoạt/đồng bộ hit và HP; key/shift/index của
  một phiên và ý nghĩa nghiệp vụ chính xác của entry `0x16/0x54`; trạng thái
  trận cuối cùng; server có xác nhận hoặc ghi đè kết quả mô phỏng của client
  hay không.
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
Đối chiếu mới cho đường update/mask dùng `InspectNativeTargets.java` với
`18030BFC0`, `180409CD6`, `180305434`; `InspectDecompileWindow.java` với
`1804098B0 FUN_18030beb0`; và `InspectInstructionWindow.java` trên cửa sổ
`180409C90..180409D20`.

Output Cpp2IL chứa placeholder và có method bị bỏ qua. Hai field mảng sau,
đường HP, một nhánh sát thương cục bộ và đường biến đổi `int[]` mask địa hình
đã được định vị. Bước tiếp theo là tìm đường bàn giao gián tiếp nhận cặp
`(int HP, sbyte loại)` tới setter `0x0600044A`, đồng thời xác định điều kiện
runtime và state key/shift/index của entry `0x16/0x54`, trước khi kết luận
server xác nhận, phát lại hay ghi đè trạng thái nào.
