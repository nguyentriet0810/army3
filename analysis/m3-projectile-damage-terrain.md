# M3 — Đường tọa độ, va chạm, sát thương và địa hình

**Phạm vi:** phân tích tĩnh `Assembly-CSharp.dll` do Cpp2IL khôi phục,
ISIL và native disassembly đã có. Không chạy client, không kết nối máy chủ
bên thứ ba. Token bên dưới thuộc assembly C# khôi phục; offset field là offset
native quan sát được trong object IL2CPP.

## Kết quả chính

| Phát hiện | Mức chắc chắn |
| --- | --- |
| Hai field mảng C/D (`+0x58/+0x60`) được đọc cùng chỉ số và chuyển thành danh sách các cặp `(x, y)` có thứ tự. | **Confirmed (cấu trúc)** |
| Danh sách C/D được một method khác duyệt tuần tự và so với tọa độ hiện tại của object. | **Confirmed (cấu trúc)** |
| C/D biểu diễn waypoint/đường đi của một object. | **Inferred**; chưa có tên gốc hoặc điều kiện runtime |
| Field player `+0x17C` là HP hiện tại và `+0x180` là HP tối đa. | **Confirmed (cấu trúc)** |
| Player còn có HP đích `+0x184`, cờ nội suy `+0x37C` và bước `+0x3A8`; vòng update kéo HP hiện tại về HP đích. | **Confirmed (cấu trúc)** |
| Một projectile cục bộ kiểm tra vùng chồng lấn rồi trừ field `+0x68` của projectile khỏi HP hiện tại. | **Confirmed trong code client** |
| Client là phía có thẩm quyền cuối cùng đối với hit/damage. | **Unknown** |
| Helper ghi `Texture2D` đã thấy là recolor/crop tài nguyên, không phải bằng chứng tạo hố. | **Confirmed đối với các helper đã kiểm tra** |
| `0x060005B8` áp một mask ảnh quanh tọa độ va chạm và ghi `0`/màu thay thế vào `int[]` đích. | **Confirmed (cấu trúc)** |
| `0x06000A62 -> 0x0600080B -> 0x060005B8` là đường biến đổi mask địa hình cục bộ. | **Strongly inferred** từ đường projectile/hình học và phép ghi mask |

## 1. Nơi dùng hai mảng C/D

Object chứa bốn field `short[][]` A–D có các offset lần lượt
`+0x48`, `+0x50`, `+0x58`, `+0x60`; cursor nằm ở `+0x68`.
Method `0x06000B64` là đường ghi bốn field này từ dữ liệu được parser message
tạo ra.

Native method `0x06000B66` (`FUN_180407C90`) lấy cả bốn mảng con tại cùng
một chỉ số:

- A/B được chuyển vào đường tạo object hình học `0x06000A42`;
- C/D được chuyển vào `0x06000A43` (`FUN_180302440`).

`0x06000A43` tạo `ArrayList` ở field `+0xD8` của object hình học. Khi byte
loại tại `+0xBD` bằng `0x30`, method duyệt đồng thời C và D, tạo một point
cho mỗi cặp `(C[i], D[i])`, rồi thêm point vào danh sách.

Method `0x06000A62` chỉ vào nhánh này khi loại cũng bằng `0x30`: nó lấy point
theo chỉ số hiện tại, so sánh tọa độ object ở `+0x10/+0x14` với tọa độ point
ở `+0x10/+0x14`, rồi tăng chỉ số khi điều kiện đạt. Vì vậy:

- **Confirmed (cấu trúc):** C/D là chuỗi cặp tọa độ có thứ tự và có consumer
  duyệt tuần tự;
- **Inferred:** C/D là waypoint/path cho chuyển động hoặc trình diễn;
- **Unknown:** phía server hay client quyết định đường này và byte `0x30`
  mang tên ngữ nghĩa gì.

## 2. Field HP và đường sát thương

Type player/entity:

```text
lIlIIIlllIIllllIlIIIIlIIllllIllIlIll.
lllIIIllIIIIIIIIlIllIllIlIllllIIlIIIIlIlIlIIlIlllllIIIlIIIlIlIlIIIlIllII
```

Hai field sau được định danh bằng nhiều phép dùng độc lập:

- `+0x17C`: HP hiện tại;
- `+0x180`: HP tối đa.

Bằng chứng:

1. đường khởi tạo chép giá trị nguồn tại `+0x180` vào cả `+0x180` và
   `+0x17C` của entity mới;
2. đường hiển thị tính `field(+0x17C) * 100 / field(+0x180)` rồi chuyển kết
   quả thành chuỗi phần trăm;
3. nhiều nhánh kiểm tra `field(+0x17C) <= 0` trước xử lý trạng thái chết;
4. các field từng là ứng viên khác đã bị loại: `+0x15C` là trạng thái hành
   động, `+0x128` là góc modulo 360, còn `+0x344` chọn frame/equipment.

Method `0x0600042A` nhận một projectile candidate và thực hiện:

```text
nếu currentHp <= 0: thoát
kiểm tra vùng projectile giao với vùng player quanh (x, y)
newHp = currentHp - projectile.damage(+0x68)
gọi 0x0600042B(newHp, ...)
ghi newHp trở lại player.currentHp(+0x17C)
```

Kiểm tra vùng dùng vị trí/kích thước projectile và vùng player quanh tọa độ
`+0x84/+0x88`; đây là kiểm tra chồng lấn dạng AABB, không phải chỉ định dạng
UI. `0x0600042A` còn tạo effect tại tọa độ player và có nhánh riêng khi
`newHp <= 0`.

Caller duy nhất tìm thấy trong IL khôi phục của `0x0600042A` là
`0x06000BB4`, method update/chuyển động của class projectile. Field damage
của projectile nằm tại `+0x68`. `0x06000BB4` tính chuyển động bằng số học
và bảng lượng giác riêng rồi gọi kiểm tra trúng đích; caller của nó là vòng
update `0x06000B95`.

Ngoài ba helper lượng giác và lời gọi kiểm tra player, application call có
tên còn lại trong `0x06000BB4` nhận `(x, y, sbyte)` và quản lý/tạo object
trong một collection; tại call site byte được truyền là `1`. Nó không gọi API
pixel trong phần IL khôi phục và phù hợp với đường effect/spawn hơn là một
texture mutator. Các field access inline và native edge bị thiếu vẫn có thể
chứa kiểm tra nền, nên đây không phải phép loại trừ đầy đủ va chạm địa hình.

Điều này xác nhận client có **mô phỏng va chạm và trừ HP cục bộ**. Nó chưa
chứng minh kết quả đó là authoritative: server vẫn có thể gửi trạng thái,
xác nhận hit, hoặc ghi đè HP sau đó.

Đồ thị IL khôi phục không tìm thấy đường từ update projectile
`0x06000BB4`, hit/damage `0x0600042A`, hoặc helper cập nhật HP
`0x0600042B` tới enqueue gửi `0x0600028F` ở độ sâu 12. Số node đã thăm là
58, 45 và 7; còn hai call event không ánh xạ được ở hai điểm đầu. Vì vậy
kết quả âm này chưa đủ để nói damage chỉ tồn tại cục bộ.

### Đường khởi tạo HP từ dữ liệu mảng

Quét riêng hai field HP trên 142 method cho 37 access tới HP hiện tại và
6 access tới HP tối đa. Ngoài constructor/copy và đường damage, method
`0x06000407` ghi **cùng một giá trị** vào cả `+0x17C` và `+0x180`.

Caller trực tiếp tìm được của `0x06000407` là `0x060001F6`. Method này nhận
năm mảng:

```text
short[], short[], int[], int[], short[]
```

Nó duyệt các phần tử/entity và gọi `0x06000407` với tọa độ, cờ trạng thái
và các giá trị lấy từ mảng. `0x060001F6` được gọi từ callback
compiler-generated `0x060007EC`; callback này nhận dữ liệu capture từ method
công khai `0x060007AF`, có chữ ký gồm hai `sbyte`, hai `short[]`, hai `int[]`,
một `short[]` và hai `int`.

- **Confirmed:** có đường batch setup tạo/cập nhật entity và đặt HP hiện
  tại = HP tối đa từ dữ liệu mảng;
- **Inferred:** đây phù hợp với khởi tạo danh sách nhân vật/trận;
- **Unknown:** không có direct caller/`ldftn` của `0x060007AF` trong IL khôi
  phục, nên chưa thể gắn đường này với một command mạng cụ thể hoặc coi nó
  là đồng bộ HP động từ server.

### HP đích và nội suy trạng thái

Quét các writer ngoài đường batch/damage làm lộ thêm ba field player:

- `+0x184`: HP đích cho quá trình nội suy;
- `+0x37C`: cờ quá trình nội suy/effect đang hoạt động;
- `+0x3A8`: bước thay đổi mỗi lượt update.

Method `0x0600042B` nhận `(int hpMới, byte loại)`, bật cờ, đặt bước bằng
`abs(hpMới - currentHp) / 20` (tối thiểu 1) và ghi `hpMới` vào `+0x184`.
Direct caller native duy nhất tìm thấy là đường damage cục bộ
`0x0600042A`; caller này sau đó còn ghi ngay `hpMới` vào HP hiện tại
`+0x17C`.

Method công khai `0x0600044A` nhận `(int hpMới, sbyte loại)` và thiết lập
cùng bộ trạng thái đích/cờ/bước, đồng thời chạy effect và nhánh chết khi
`hpMới < 1`. Trong 108.726 event IL đã khôi phục không có `call`, `callvirt`,
`ldftn` hay `ldvirtftn` nhắm tới method này; Ghidra cũng chỉ thấy data
reference tới entry native `FUN_180531360`, không có direct call. Reference
tại `0x1817EAB70` nằm trong section `.pdata`; reference tại `0x181405998`
nằm trong một dãy con trỏ code liên tiếp ở `.data`, kẹp giữa các entry method
`0x1805312C0` và `0x180531830`, và bản thân ô này không có code xref. Dữ liệu
đó phù hợp với bảng method pointer do IL2CPP sinh: ba slot liên tiếp ánh xạ
các method lân cận `0x06000449/44A/44B` tới ba entry native tương ứng. Nó
không phải bằng chứng về một delegate cụ thể. Ngữ nghĩa của `0x0600044A`
tương thích với việc nhận một giá trị HP mới, nhưng hiện chưa có execution
edge nào chứng minh method này thực sự chạy; càng chưa thể gắn nó với
message/network.

Method `0x0600044B` (`FUN_180531830`) là consumer theo lượt update: khi cờ
bật, nó cộng hoặc trừ `+0x3A8` vào HP hiện tại `+0x17C` và clamp tại HP đích
`+0x184`. Hai direct caller native đã thấy nằm trong các vòng update entity
(`0x18051B0EC` và `0x180423919`), không nằm trong message dispatcher.
Method `0x06000BE6` chỉ dựng effect từ chênh lệch HP và xóa cờ sau khi
current bằng target đủ hơn 30 lượt; caller trực tiếp trong IL là
`0x06000BE5`.

Phép quét displacement trên toàn native handler `FUN_1801FCAB0` chỉ gặp
`[RSP+0x17C]`, `[RSP+0x180]`, `[RSP+0x184]` — đều là vùng stack — và không
thấy truy cập object tới năm offset HP/cờ/bước trên. Handler cũng không có
direct call tới `0x0600042B`, `0x0600044A` hay `0x0600044B`. Đây là
**kết quả âm có giới hạn**: callback, interface/virtual dispatch hoặc helper
trung gian vẫn có thể bàn giao cập nhật HP.

## 3. Callback kết thúc viên đạn

Khi consumer đường đi `0x06000A62` kết thúc, nó gọi `0x06000B69` với:

- tọa độ cuối ở `+0x10/+0x14`;
- một cặp tọa độ gốc ở `+0x2C/+0x30`;
- một byte loại tại `+0x78`.

`0x06000B69` đóng các giá trị thành event rồi gọi callback compiler-generated
ở native `0x18040D300`. Các giá trị `+0x2C/+0x30` là tọa độ gốc được sao
chép trong đường hoàn tất, không phải damage. Vì vậy event này là ứng viên
thông báo kết thúc chuyển động/effect, chưa phải bằng chứng cập nhật địa hình.

Trên đồ thị IL khôi phục, lần từ `0x06000B69`, `0x06000B6C`, `0x06000B6D`
và `0x06000B6E` tới độ sâu 12 không tìm thấy đường tới:

- enqueue gửi `0x0600028F`;
- helper crop/copy pixel `0x06000827`;
- helper recolor `0x06000B1F`.

Số node được thăm tương ứng là 20, 5, 3 và 3; độ sâu xa nhất là 4 hoặc 1,
không node nào bị cắt bởi giới hạn. Đây là **phép kiểm tra âm có giới hạn**:
IL recovery có thể thiếu virtual/indirect/native edge.

## 4. Mask địa hình và biến đổi cục bộ

Các write site `Texture2D` thấy trong IL khôi phục gồm:

- `0x06000B1F`: đọc pixel, nội suy RGB về một màu theo hệ số, ghi vào ảnh
  mới rồi `Apply`; hai caller truyền hệ số `0.6`. Đây là recolor/tint sprite;
- `0x06000827`: `GetPixel` → `SetPixel` → `Apply` để crop/copy ảnh trong
  đường khởi tạo tài nguyên;
- `0x060000B4` và `0x06000822`: dùng `SetPixels32` trong các helper ảnh khác.

Method `0x06000830` đọc một vùng ảnh thành `int[]` bằng `GetPixel` và alpha.
Một caller (`0x06000398`) đúng là đường tạo bảng tài nguyên tĩnh, nhưng ba
caller còn lại thuộc cùng một type có:

- hai image wrapper tĩnh và các mảng image wrapper;
- `int[][]` tĩnh tại `+0x30`;
- hai `int[]` trên mỗi instance tại `+0x18/+0x20`;
- các field kích thước/offset và method kiểm tra theo tọa độ.

Type này là:

```text
llIIIIIIllIllIIIIlIIIlllIlIllllIIllI.
llIIIIIlIlIIIlllIIIlIlIlIIlIIIIlIIllIIlIlIlIIllllllIllllIlllIllIlIIIIIIl
```

Method `0x060005B8` của type nhận ba `int` và thực hiện các bước có thể kiểm
tra trực tiếp trong ISIL:

1. chọn image/mask theo tham số thứ ba;
2. gọi `0x06000830` để đọc vùng pixel vào một `int[]` stamp;
3. tính cửa sổ quanh hai tham số tọa độ đầu;
4. duyệt stamp và mask đích theo chỉ số hai chiều đã tuyến tính hóa;
5. so sánh các màu sentinel `0xFF0000` và `0xFFFFFF`;
6. ghi `0` vào `int[]` instance tại `+0x18` ở các pixel bị loại; một nhánh
   khác ghi giá trị màu dùng chung.

Đây là **Confirmed (cấu trúc)** về phép biến đổi mask cục bộ. Từ ngữ cảnh
tọa độ va chạm, stamp ảnh và việc xóa pixel, việc nó là tạo hố/biến đổi địa
hình được xếp **Strongly inferred**, chưa dựa trên tên gốc.

Đường gọi dương trong IL khôi phục:

```text
0x06000A62 (consumer hình học/projectile)
  -> 0x0600080B(x, y, sbyte loại)  tại 0x26DB hoặc 0x284C
  -> 0x060005B8(x', y', loại)     tại 0x10FE
  -> 0x06000830(ref int[] stamp, ...)
  -> ghi mask đích int[]
```

`0x0600080B` duyệt collection, chọn các object đúng type mask bên trên và
gọi `0x060005B8` cho từng object với tọa độ đã quy đổi. Đồ thị IL tìm thấy
đường `0x06000A62 -> 0x0600080B -> 0x060005B8` ở độ sâu 2. Trong khi đó,
không tìm thấy đường tương ứng từ projectile class `0x06000BB4` hoặc callback
`0x06000B69`; client có ít nhất hai họ projectile/hình học khác nhau.

Đối chiếu native khép thêm đường lập lịch/update mà Cpp2IL không khôi phục:

```text
0x060007C0 / FUN_1802870F0
  -> 0x06000B67 / FUN_1804098B0  tại native 0x180287C4E
  -> 0x06000A62 / FUN_18030BEB0  tại native 0x180409CD6
  -> 0x0600080B
  -> 0x060005B8
```

Ghidra decompile cho thấy `0x06000B67` duyệt collection, lấy từng object rồi
gọi `0x06000A62`; caller native còn lại `FUN_1803053B0` là wrapper
`0x06000A52` tail-call cùng target. Đây là **Confirmed** rằng biến đổi mask
nằm trong đường update collection cục bộ, không chỉ là một helper không được
dùng. Cạnh `0x06000B67 -> 0x06000A62` không xuất hiện trong call graph IL,
nên các kết quả âm dựa trên graph đó tiếp tục phải được xem là có giới hạn.

Không write site `Texture2D` nào ở trên xuất hiện trong đường damage
`0x06000BB4/0x0600042A` hoặc callback kết thúc `0x06000B69`. Tuy nhiên đường
`0x06000A62` xác nhận giả thuyết client dùng buffer `int[]` tự quản lý thay
vì sửa `Texture2D` trực tiếp ở điểm va chạm.

Trace riêng từ `0x06000BB4`, `0x0600042A` và `0x0600042B` cũng không tới
`0x06000827` hay `0x06000B1F`; số node/giới hạn giống phép kiểm tra enqueue
ở trên. Đây tiếp tục là kết quả âm trên đồ thị khôi phục, không phải bằng
chứng phủ định ở native runtime.

## 5. Ranh giới mô phỏng hiện tại

```text
entry điều phối sau biến đổi 0x16/0x54
  -> parser tạo A/B/C/D -> 0x06000B64 lưu vào controller
  ~> lượt update sau đọc cùng state bằng 0x06000B66/0x06000B67
     -> A/B tạo object hình học
     -> C/D tạo chuỗi point có thứ tự
     -> update cục bộ di chuyển/duyệt point
     -> 0x06000A62 -> 0x0600080B -> sửa mask địa hình 0x060005B8

projectile class khác 0x06000BB4
  -> overlap + trừ HP 0x0600042A
  -> effect/kết thúc

dữ liệu mảng -> batch setup entity 0x060001F6 -> đặt current/max HP 0x06000407

HP target +0x184 -> 0x0600044B nội suy current HP +0x17C
nguồn gọi gián tiếp của setter target 0x0600044A?  UNKNOWN

server xác nhận/ghi đè kết quả?  UNKNOWN
raw command cụ thể của 0x16/0x54?  phụ thuộc key/shift/index
nghĩa gameplay của 0x16/0x54?      UNKNOWN
command mạng cho hit/HP?          UNKNOWN
```

**Kết luận tạm thời:** client chắc chắn không chỉ vẽ UI; nó chứa chuyển động,
kiểm tra trúng đích, phép trừ HP và biến đổi mask địa hình. Chưa đủ bằng chứng
để chọn mô hình server M5 là authoritative hay relay/state-sync: chưa gắn được
batch HP hoặc hit với command mạng cụ thể. Hai entry `0x16/0x54` đã nối
được tới state tạo object có khả năng đi qua đường sửa mask. Công thức đổi
logical/raw command đã xác định, nhưng key/shift/index của phiên, điều kiện
runtime và ý nghĩa nghiệp vụ của hai entry vẫn chưa biết.

## Cách tái lập

Tạo bảng field access (output nằm dưới thư mục bị Git ignore):

```powershell
./scripts/inspect-il-fields.ps1 -TypeName 'lIlIIIlllIIllllIlIIIIlIIllllIllIlIll.lllIIIllIIIIIIIIlIllIllIlIllllIIlIIIIlIlIlIIlIlllllIIIlIIIlIlIlIIIlIllII' -FieldPattern '.*' -OutputPath 'analysis/generated/m3/player-field-accesses.tsv'
./scripts/inspect-il-fields.ps1 -TypeName '*' -FieldPattern '.*::(llllIlIIllllIlIIlIlIIlllllIIlllIllIlIIIIllIlIIlIlIIlIIlIIlllIIllIIlllIII|lllIIIIllIllIlIlIIIIIlIlIIlIlIIlIIIIlIlIIlIIIlIlIIIlIlIIIIllllllIlIIIllI|lIIIIIllIIIIlIlIlIIIIIlIlIIlllIIlIlIIIlIlIIIlIIIIlllIlIlllIlIIIIIlllllII)$' -OutputPath 'analysis/generated/m3/hp-target-accesses-all.tsv'
```

Kiểm tra các cạnh callback tới enqueue và hai helper ảnh:

```powershell
./scripts/trace-il-reachability.ps1 -CallsPath 'analysis/generated/m3/all-il-calls-20260924.tsv' -StartTokens '0x06000B69','0x06000B6C','0x06000B6D','0x06000B6E' -TargetToken '0x0600028F' -MaxDepth 12
./scripts/trace-il-reachability.ps1 -CallsPath 'analysis/generated/m3/all-il-calls-20260924.tsv' -StartTokens '0x06000B69','0x06000B6C','0x06000B6D','0x06000B6E' -TargetToken '0x06000827' -MaxDepth 12
./scripts/trace-il-reachability.ps1 -CallsPath 'analysis/generated/m3/all-il-calls-20260924.tsv' -StartTokens '0x06000B69','0x06000B6C','0x06000B6D','0x06000B6E' -TargetToken '0x06000B1F' -MaxDepth 12
./scripts/trace-il-reachability.ps1 -CallsPath 'analysis/generated/m3/all-il-calls-20260924.tsv' -StartTokens '0x06000BB4','0x0600042A','0x0600042B' -TargetToken '0x0600028F' -MaxDepth 12
./scripts/trace-il-reachability.ps1 -CallsPath 'analysis/generated/m3/all-il-calls-20260924.tsv' -StartTokens '0x06000A62','0x06000BB4','0x06000B69' -TargetToken '0x060005B8' -MaxDepth 12
```

Đối chiếu các cạnh update bằng Ghidra read-only:

```text
-process GameAssembly.dll -readOnly -noanalysis
-scriptPath scripts/ghidra
-postScript InspectNativeTargets.java 18030BFC0 180409CD6 180305434
-postScript InspectDecompileWindow.java 1804098B0 FUN_18030beb0
-postScript InspectInstructionWindow.java 180409C90 180409D20
-postScript InspectDisplacementAccesses.java 1801FCAB0 17C 180 184 37C 3A8
-postScript InspectDataReferences.java 181405998
-postScript InspectPointerBytes.java 181405980 181405988 181405990 181405998 1814059A0 1814059A8 1814059B0
```

Log Git-ignored `method-pointer-table-proof.log` đối chiếu lại ba slot
`0x181405990/998/9A0`; ô của `0x0600044A` không có code reference riêng.

Các source chính để đối chiếu nằm trong output Cpp2IL bị ignore:

- player/entity: `diffable-cs/.../lIlIIIlllIIllllIlIIIIlIIllllIllIlIll/...cs`;
- projectile: `diffable-cs/.../lIlllIIlIIIlllIIllIIlIlIlllIIlIlllIl/...cs`;
- controller A/B/C/D: `isil/.../llIIlIllllIIIIIIIIIIllllllIIIIlIIIII/...txt`.
