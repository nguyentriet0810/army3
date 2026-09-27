# M3: `0x9E` selector `2` và đồng bộ tọa độ

Phân tích tĩnh trên bản client đã hash ở M1. Không chạy client và không liên
hệ server bên thứ ba. Các tên `entityKey`, `x`, `y`, `current` và `target` là
alias mô tả theo data-flow; chỉ `x/y` có bằng chứng sử dụng hình học trực tiếp.

## Dispatch và schema

`Confirmed`: jump table con của command `0x9E` ánh xạ selector `2` qua stub
`0x1802497E5` tới nhánh `0x18024C43D`.

`Confirmed`: sender `FUN_18031B0E0` tạo request gồm selector `2` và hai số
16-bit big-endian, không kèm key:

```text
client -> server
[selector: u8 = 2]
[x: i16 BE]
[y: i16 BE]
```

`Confirmed`: handler luôn đọc `entityKey`. Trên đường không bị bỏ qua sớm,
nó đọc thêm đúng hai word big-endian:

```text
server -> client
[selector: u8 = 2]
[entityKey: u8]
[x: i16 BE]
[y: i16 BE]
```

Hai word được sign-extend trước khi ghi vào các field int32. Request dài đúng
5 byte. Đường response đầy đủ tiêu thụ 6 byte nếu tính selector; đường bỏ qua
sớm chỉ tiêu thụ selector và key. Phân tích tĩnh không cho biết server gửi
response ngắn 2 byte ở trường hợp này hay vẫn gửi 6 byte để client bỏ phần dư
trong buffer message riêng.

## Chứng minh hai trường cuối selector `0` là tọa độ

Hai field cuối của response selector `0` đi vào cùng cặp tham số mà sender
selector `2` ghi lên wire:

- field 17 trở thành `x`;
- field 18 khởi tạo `yCandidate`.

`Confirmed`: `FUN_180519910(entity, x, y)` ghi `x/y` vào `+0x84/+0x88` và
nhiều mirror field, gồm `+0x298/+0x29C`. Nó còn ghi `y - 50` vào một state
liên quan và chuyển `x` thành float tại `+0x3D0`.

`Confirmed`: `FUN_18041C450(grid, x, y)` tính:

```text
cellIndex = x / 24 + (y / 24) * gridWidth
```

rồi lấy một phần tử 32-bit từ mảng grid. Trong hậu xử lý selector `0`, client
tăng `yCandidate` từng đơn vị, kiểm tra bit `0x4` của cell và chặn scan ở
`1000`. Khi tìm được vị trí phù hợp, một đường khởi tạo entity bằng
`(x, yCandidate)` và gửi selector `2` với chính cặp đó. Nếu scan vượt giới hạn,
đường fallback dùng lại tọa độ ban đầu.

Vì vậy `Confirmed` về vai trò hình học: field 17/18 là tọa độ 2D, theo thứ tự
`x/y`. `Inferred`: đây là bước đặt vị trí spawn/placement hợp lệ trên grid;
tên nghiệp vụ chính xác vẫn chưa khôi phục.

## Nguồn tọa độ outbound

`Confirmed`: sender `FUN_18031B0E0` có sáu direct code call site. Năm call
site `0x180522EE5`, `0x18052315D`, `0x1805233AB`, `0x180523409` và
`0x180523512` nằm trong `FUN_1805225D0`; routine này được `FUN_180414150` gọi
với object do `FUN_180446E50()` trả về. Helper `FUN_180446E50()` lấy một byte
chỉ số ở static `+0x31`, rồi trả phần tử tương ứng từ collection entity. Vì
chưa khôi phục được tên gốc, tài liệu gọi đây là **selected/current entity**.

Trong cả năm call site, cặp đưa lên wire là current coordinate của chính object
đó tại `+0x84/+0x88`. Routine so current coordinate với snapshot
`+0x1B2/+0x1B4`; tùy movement state, thay đổi `x` hoặc `x/y` sẽ kích hoạt send,
sau đó snapshot tương ứng được cập nhật ngay. Một gate tĩnh `+0x110 == 0`
cũng phải thỏa trước các đường gửi đã thấy.

`Confirmed`: call site thứ sáu `0x1805259F4` nằm trong `FUN_180524E70`, là
đường placement đã nối với selector `0`. Nó lấy selected/current entity qua cùng
`FUN_180446E50()`, đọc mirror `+0x298/+0x29C` và gửi cặp đó. Như vậy cả sáu
direct call site đã tìm được đều phát tọa độ hiện có trong state client; không
call site nào gửi một yêu cầu để server tự tính vị trí.

`Unknown`: hai data reference tới sender nằm trong bảng metadata/code pointer,
chưa có execution edge chứng minh một indirect caller khác. Kết luận trên chỉ
bao phủ sáu direct code call đã xác nhận.

## Xử lý response selector `2`

Handler dùng `entityKey` để tra nhiều collection song song. Control flow đã
xác nhận:

1. Tra object theo `entityKey` và so identity với selected/current entity do
   `FUN_180446E50()` trả về. Nếu trùng, handler thoát sớm **trước khi đọc** hai
   word tọa độ còn lại.
2. Nếu không trùng, đọc `x/y`, ghi chúng vào mirror `+0x298/+0x29C`.
3. Đọc tọa độ hiện tại `+0x84/+0x88` của một object cùng key.
4. Nếu cả hai bằng `x/y`, thoát ngay: không tạo correction.
5. Nếu khác, chọn một trong hai đường cập nhật:
   - với object thỏa predicate `FUN_180517380`, đặt byte `+0x168 = 1` và cập
     nhật `+0x298/+0x29C` của mirror khác;
   - nếu không, gọi `FUN_180449900(entityKey, x, y)`.

`FUN_180517380` trả true khi field `+0x1DC` bằng `1` hoặc `8`, hoặc khi object
thuộc một type cụ thể và byte `+0x13 == 2`. Ý nghĩa các mode vẫn `Unknown`.

`Confirmed`: `FUN_180449900` ghi:

```text
+0x1D0 = x
+0x1D4 = y
+0x1D8 = 1
+0x294 = 0
```

Nếu `entityKey` trùng một key tĩnh ở `+0x27C`, helper còn gọi
`FUN_180534440`, và helper này cập nhật `+0x1B8/+0x1BC` bằng `x/y` khi byte
instance `+0xF0` khớp cùng key.

## Consumer của state correction

Đã lần cả `+0x1D8` và `+0x168` vào routine update entity
`FUN_180423620`. Kết quả sửa lại giả thuyết “teleport hay nội suy” như sau.

`Confirmed`: `+0x168` không phải cờ boolean riêng của selector `2`; nó là
một state chuyển động/animation nhiều giá trị. Helper chuyển động
`FUN_180532A40` tự đổi các state `0`, `2` hoặc `8` thành `1` trước khi di
chuyển. Vì vậy nhánh đặc biệt của selector `2` đặt `+0x168 = 1` có nghĩa kích
hoạt state di chuyển đang dùng, đồng thời đặt đích mirror `+0x298/+0x29C`.
Tên gameplay chính xác của state `1` vẫn `Unknown`.

`Confirmed`: trên đường thông thường, mỗi lần update client so sánh
`+0x1D0/+0x1D4` với current `+0x84/+0x88`. Khi `x` chưa tới đích và các gate
entity cho phép, nó gọi `FUN_180532A40` với hướng `0` hoặc `2`. Helper này:

- tăng/giảm tọa độ float `+0x3D0` theo một bước tốc độ rồi copy phần nguyên
  sang current `x` tại `+0x84`;
- probe collision map tại vị trí mới, gồm điểm gần `y - 5`;
- rollback bước ngang nếu gặp collision;
- có thể dò xuống tối đa bốn pixel để bám bề mặt;
- chỉ trên một số đường sau khi `x` đã hội tụ mới copy trực tiếp target
  `+0x1D4` sang current `y`.

Do đó correction thông thường là **chuyển động theo tick có kiểm tra vật lý**,
không phải teleport tức thời. Riêng trục `y` có đường snap/căn chỉnh sau khi
trục `x` đã hội tụ, nên mô hình tổng thể là hybrid chứ không phải nội suy đều
hai trục.

`Confirmed`: `+0x1D8` là pending marker được consumer kiểm tra sau các gate
state. Trước khi tiêu thụ marker, routine yêu cầu sai số giữa current
`+0x84/+0x88` và mirror `+0x298/+0x29C` không quá hai đơn vị trên từng trục.
Sau đó nó xóa `+0x1D8`, reset `+0x168`, rồi chạy một nhánh hội tụ sai số nhỏ:
`x` float tiến về `+0x298` với bước bị chặn, `y` tiến về `+0x29C` với bước bị
chặn, và current được cập nhật từ các giá trị này. Đây là **micro-reconcile**
ở cuối/biên của movement state, không phải một teleport khoảng cách lớn.

`Inferred`: `+0x1D0/+0x1D4` là movement target chính;
`+0x298/+0x29C` là mirror/anchor dùng để đối chiếu và sửa sai số nhỏ; `+0x1D8`
đánh dấu một correction đang chờ hoàn tất. Chưa biết tên field gốc và chưa
chứng minh mọi mode entity đi qua cùng các gate.

## Vòng publish/relay và nhánh phát sinh từ selector `0`

Luồng tối thiểu đã xác nhận là:

```text
selected/current entity thay đổi vị trí
    ├─ movement path: current +0x84/+0x88 khác snapshot
    └─ placement path sau 0x9E/0: mirror +0x298/+0x29C
                         ↓
client -> server: 0x9E/2 (x, y)
                         ↓
server -> client: 0x9E/2 (entityKey, xServer, yServer)
                         ↓
recipient: nếu entityKey là selected/current entity thì bỏ qua
           nếu là entity khác và tọa độ lệch thì đặt correction/target
```

`Confirmed`: nhánh nhận selector `2` không gọi sender `FUN_18031B0E0` và
không gửi message khác. Vì vậy đây không phải vòng lặp đệ quy hay pagination;
nó kết thúc sau bước áp dụng/đặt correction. Những lần selector `2` tiếp theo
chỉ có thể do event/gameplay khác kích hoạt sender.

`Strongly inferred`: vai trò transport của selector `2` là **client position
publication rồi server relay/state replication cho các entity khác**, không
phải kênh authoritative correction cho chính sender. Bằng chứng kết hợp là:

- mọi direct sender đã biết lấy tọa độ từ selected/current entity phía client;
- request không chứa key, còn event chiều về được server gắn `entityKey`;
- recipient bỏ qua selected/current entity trước khi đọc tọa độ;
- chỉ entity khác mới so current coordinate và đi vào correction;
- nhánh nhận không tạo một request selector `2` mới.

Tên `xServer/yServer` trong sơ đồ chỉ biểu thị giá trị nhận từ wire, không có
nghĩa rằng server đã tự tính chúng. `Unknown`: server có thể kiểm tra, clamp,
thay thế hoặc từ chối tọa độ trước khi phát lại; phân tích client tĩnh không
thể chứng minh response là echo byte-for-byte hay server hoàn toàn không có
thẩm quyền. Vì vậy đặc tả server cục bộ ban đầu có thể dùng mô hình relay
`[2,x,y] -> [2,entityKey,x,y]`, nhưng phải giữ validation là một điểm mở.

Phát hiện tọa độ/grid làm suy yếu suy luận cũ gán transition cuối selector
`0` cho main menu/lobby. An toàn hơn là gọi nó **transition scene sau
hydrate entity và placement**; room, match hay gameplay scene vẫn `Unknown`.

## Chứng cứ tái lập

- `scripts/ghidra/SummarizePseudoCfg.java`: CFG bounded
  `0x18024C43D..0x18024CD9E`, 389 instruction, không lỗi decode.
- `scripts/ghidra/SummarizeReaderSequence.java`: xác nhận đúng ba reader
  `byte, u16 BE, u16 BE`.
- `scripts/ghidra/InspectPseudoCallWindows.java` và
  `FindPseudoInstructions.java`: field write, current-coordinate comparison và
  các đường correction.
- `scripts/ghidra/InspectNativeTargets.java`: decompile sender và các helper
  tọa độ/grid/correction, gồm movement helper `FUN_180532A40`.
- `scripts/ghidra/FindProgramDisplacementAccesses.java`: tìm consumer của
  `+0x1D8/+0x168` trên toàn listing; kết quả được lọc lại theo cùng entity
  layout để tránh nhầm offset của type khác.
- `analysis/generated/ghidra/selector2-authority-callers.log` và
  `selector2-authority-producers.log`: sáu direct sender call site, nguồn
  coordinate và snapshot write; đều bị Git ignore.
- `analysis/generated/ghidra/selector2-update-loop.log`: caller lấy
  selected/current entity rồi gọi routine chứa năm sender; bị Git ignore.
- `analysis/generated/ghidra/selector2-self-filter.log`: lookup theo key, so
  identity và nhánh bỏ qua self trước hai reader tọa độ; bị Git ignore.
- `analysis/generated/ghidra/case9e-selector2-analysis.log`: log tổng hợp của
  các phép kiểm tra trên; file sinh tự động và bị Git ignore.
- `analysis/generated/ghidra/coordinate-correction-analysis.log`: instruction
  window, field access và decompile helper cho đường correction; bị Git ignore.

Mọi script được chạy read-only với
`-process GameAssembly.dll -noanalysis -readOnly`.
