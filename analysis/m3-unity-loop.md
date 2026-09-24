# M3: Điểm khởi tạo Unity và nhịp xử lý transport

Phân tích tĩnh trên client đã hash ở M1. Không chạy client, không truy cập
server bên thứ ba. `Confirmed` dưới đây nghĩa là thấy trong metadata/ISIL và
được đối chiếu với native; không khẳng định thứ tự scene hay hành vi phiên chơi.

## Các callback tìm được

`Assembly-CSharp` có bốn type trực tiếp kế thừa `MonoBehaviour` trong output
`diffable-cs`. Type thứ nhất có `OnApplicationQuit` và field
`UnityWebRequest`; type thứ hai có `Update` và field `AudioSource`/`WWW`.
Chưa có chứng cứ để gọi chúng là manager game chính.

| Vai trò cấu trúc | Bằng chứng | Kết luận |
| --- | --- | --- |
| Bootstrap trước scene | Một type có method `0x06000001` mang attribute `RuntimeInitializeOnLoadMethod(BeforeSceneLoad)`; IL khôi phục tạo `GameObject` tên `AndroidBridge`, gọi `DontDestroyOnLoad` và `AddComponent` | Confirmed về hook/chuỗi lời gọi; Unknown về vai trò đối với đăng nhập |
| Main loop ứng viên | Một type khác có `Start` (`0x0600036D`), `OnGUI` (`0x0600036E`), `FixedUpdate` (`0x06000373`), `Update` (`0x06000374`) và `OnApplicationQuit` (`0x06000377`); field tĩnh offset `+0x10` có type transport | Confirmed về cấu trúc, Inferred về vai trò manager chính |
| Khởi tạo hiển thị/nhập liệu | Trong `Start` có lời gọi `Screen.SetResolution`; `Update` có `Input.GetKeyDownInt` và `Time.get_realtimeSinceStartup` | Confirmed về call site; chưa xác định điều kiện nhánh |

Attribute `BeforeSceneLoad` là điểm khởi tạo sớm **của AndroidBridge**, không
chứng minh đây là điểm khởi tạo game logic. Chưa biết scene đầu tiên hoặc
thời điểm component main loop được gắn vào scene.

## Từ `FixedUpdate` đến transport

`Confirmed` ở mức đường gọi:

1. ISIL của `FixedUpdate` `0x06000373` chứa lời gọi tới method tĩnh
   `0x06000297` của type transport.
2. ISIL ánh xạ hai method sang native `FUN_1804ff770` và
   `FUN_1804e0740`; Ghidra xác nhận call `0x1804ffabd` từ hàm thứ nhất
   sang hàm thứ hai.
3. `FUN_1804e0740` đọc field tĩnh `+0xA8` của transport. Metadata cho
   biết field đó là object có `ArrayList` tại offset instance `+0x10`.
   Decompile kiểm tra số phần tử qua virtual call, lấy phần tử chỉ số `0`,
   kiểm tra kiểu, gọi helper `FUN_180004250`, rồi gọi
   `FUN_180425f30` với chỉ số `0`. Helper sau kiểm tra biên và gọi một
   virtual method khác trên collection.
4. Worker nhận `FUN_1804e3d60` gọi `FUN_1804e05e0` với message ở nhánh
   không phải ba nhánh đặc biệt `0xE5`, `0xA9`, `0x83`. Trong một nhánh
   của `FUN_1804e05e0`, code lấy cùng field `+0xA8`, rồi truyền message
   vào virtual method `+0x308` của `ArrayList` bên trong. Nhánh khác gọi
   helper `FUN_180004250` qua field transport `+0x20`. Điều kiện chọn
   hai nhánh này chưa được xác định chắc chắn.

`Inferred`: virtual method `+0x308` là thao tác thêm phần tử, còn nhánh
`FixedUpdate` tiêu thụ hàng đợi sự kiện/message. Đường worker nhận →
collection → `FixedUpdate` có chứng cứ cấu trúc, nhưng chưa chứng minh
mọi message đều đi qua collection: một nhánh có thể dispatch trực tiếp.
Chưa biết callback hoặc message nào được xử lý, và chưa chứng minh việc
tiêu thụ xảy ra trong mọi trạng thái màn hình. Không coi đây là bằng
chứng cho login, heartbeat hay quyền mô phỏng trận.

## Điểm vào xử lý message cấp ứng dụng

Metadata cho thấy field transport `+0x20` có type interface gồm bốn method,
trong đó một method nhận object message. Trong `Assembly-CSharp` đã tìm
thấy một class trực tiếp triển khai interface này; method nhận message
của class có token `0x060006DC`. Đây là **Confirmed** về quan hệ type và
chữ ký, không phải bằng chứng mọi message đều được class đó xử lý.

`Inferred`: interface này là ranh giới giữa transport và game logic, còn
`0x060006DC` là ứng viên handler cho state đăng nhập/lobby/phòng/trận.
Method rất lớn (ISIL cho thấy stack frame `0x136E8`) và IL recovery chủ
yếu chứa placeholder, nên chưa thể phân loại các nhánh command bằng
output IL hiện tại. Cần phân tích native có mục tiêu thay vì đặt tên
command theo phỏng đoán. Bước đầu đã xác định bảng điều phối native;
xem [m3-message-dispatch.md](m3-message-dispatch.md).

## Chứng cứ tái lập

- Metadata: `analysis/generated/cpp2il/diffable-cs/DiffableCs/Assembly-CSharp/`.
- Call trace (Git-ignored): `analysis/generated/m3/unity-bootstrap.tsv`,
  `unity-mainloop.tsv`, `unity-webrequest.tsv`, `unity-audio.tsv`, tạo bằng
  `scripts/inspect-il-calls.ps1` với `-TypeName` bắt đầu bằng dấu `.` vì các
  type trên ở global namespace.
- ISIL: `analysis/generated/cpp2il/isil/IsilDump/Assembly-CSharp/`.
- Interface và class triển khai trong `diffable-cs`; trace handler:
  `analysis/generated/m3/transport-listener.tsv` (Git-ignored).
- Native: `analysis/generated/ghidra/unity-dispatch.log` và
  `unity-queue-helpers.log`, `unity-receive-handoff.log`, chạy
  `InspectNativeTargets.java` trên các địa chỉ `1804E0790`,
  `1804FF7F3`, `180425F30`, `180004250`, `1804E05E0` với
  `-process GameAssembly.dll -noanalysis -readOnly`.

Cpp2IL có placeholder và `NoteDecompilerIssue`; Ghidra project mới phân
tích từng phần. Vì thế các nhánh điều kiện và ý nghĩa nghiệp vụ còn phải
đối chiếu tiếp trước khi chốt state machine.
