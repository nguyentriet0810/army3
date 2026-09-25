# M3 — Virtual dispatch quanh consumer dữ liệu hình học

Phân tích tĩnh trên `Assembly-CSharp.dll` khôi phục và bản
`GameAssembly.dll` có hash ở M1. Không chạy client hoặc liên hệ server
bên thứ ba. Mục tiêu của khảo sát này là kiểm tra các lời gọi gián tiếp
quanh `0x060007C0` có dẫn tới đường gửi message hay không.

## Điểm gửi dùng để đối chiếu

- **Confirmed:** method transport `0x0600028F` nhận một object message,
  native entry `FUN_1804DFC50`, rồi gọi `FUN_1804E23C0` để thêm message
  vào hàng đợi có khóa.
- **Confirmed:** worker gửi bắt đầu tại `FUN_1804E2520`, lấy message khỏi
  hàng đợi và đi qua `FUN_1804E02F0` tới serializer
  `FUN_1804E1B60`.

Các địa chỉ này là đích kiểm tra cấu trúc; việc không có direct call tới
chúng không loại trừ một đường gửi sâu hơn hoặc callback chưa phục hồi.

## Hai virtual call trên field tĩnh `+0x2B0/+0x2B8`

- **Confirmed:** type chứa `0x060007C0` có hai field tĩnh tại `+0x2B0`
  và `+0x2B8`, cùng mang type
  `lIIllIIIlllIIIIlIIIIlIlIIlllIIIIlIllIllIIlIIlllIlIIlllIlllIIIIlIlIIlIlII`.
- **Confirmed:** trong ISIL của `0x060007C0`, hai object từ các field này
  được gọi gián tiếp qua slot `+0x178`. Type đích override đúng method
  cùng chữ ký; token của override là `0x06000A67`.
- **Confirmed:** `0x06000A67` đọc byte instance tại `+0x10`. Tùy giá trị,
  nó gọi `0x06000A6C`, `0x06000A6D`, hoặc trả về. Disassembly native
  chuyển điều khiển tới `FUN_18030FDB0` và `FUN_180310280` cho hai nhánh
  xử lý.
- **Confirmed:** IL khôi phục của `0x06000A6C/0x06000A6D` có các cặp
  `ArrayList.get_Count` / `ArrayList.get_Item` và các phép cập nhật
  object cục bộ. Đồ thị IL không tìm thấy đường từ `0x06000A67`,
  `0x06000A6C` hoặc `0x06000A6D` tới enqueue `0x0600028F` khi lần tới
  độ sâu 12. Ba điểm bắt đầu lần lượt thăm 9, 6 và 5 method; còn 3, 3
  và 0 event không ánh xạ vào method của assembly.
- **Confirmed (native, có giới hạn):** `FUN_180310280` có 19 call site,
  `FUN_18030FDB0` có 23; mỗi function có hai computed call. Không có
  direct call tới `FUN_1804DFC50`, `FUN_1804E23C0`, worker gửi hay hai
  hàm serialize đã biết. Hai computed call ở mỗi function dùng slot
  `+0x298/+0x2E8`, phù hợp với cặp `ArrayList.get_Count/get_Item` đã
  phục hồi trong IL.

## Các indirect call còn lại trong `0x060007C0`

- **Confirmed:** Ghidra đếm 135 call site trong `FUN_1802870F0`
  (`0x060007C0`), trong đó 11 call là computed/indirect.
- **Confirmed:** Cpp2IL khôi phục rõ tám indirect call trong ranh giới
  method này: hai call slot `+0x178` nêu trên, bốn call slot `+0x298`
  trả số lượng collection và hai call slot `+0x2E8` lấy phần tử theo
  chỉ số. Các cặp sau đọc collection nằm trong object tĩnh tại `+0x178`
  hoặc `+0x1B0`, kiểm tra chỉ số rồi cast phần tử sang type game.
- **Confirmed:** ba computed call native còn lại đã được Cpp2IL phục
  hồi thành API có tên thay vì node `IndirectCall`: hai call
  `ArrayList.get_Count` tại `0x1802876B9/0x1802876F5` và một call
  `ArrayList.Remove` tại `0x18028781A`. Disassembly cho thấy cả ba
  lấy `ArrayList` từ field `+0x10` của wrapper ở instance field
  `+0x80`; metadata của wrapper cũng khai báo đúng field `ArrayList`
  tại `+0x10`.
- **Confirmed (phạm vi trực tiếp):** như vậy cả 11 computed call của
  `FUN_1802870F0` đã được phân loại cấu trúc: hai sibling override và
  chín thao tác collection (`Count`, `Item`, `Remove`). Không call nào
  trong số này trực tiếp là enqueue/worker/serializer của transport.
  Điều này vẫn không loại trừ method xử lý phần tử được gọi trực tiếp ở
  nơi khác rồi gửi message.

## Kết luận hiện tại

- **Inferred:** đường đã biết từ message `0x16/0x54` tới mảng, object
  hình học, consumer `0x060007C0` và hai sibling override chủ yếu giống
  đường cập nhật/duyệt collection cục bộ. Trong phạm vi đã lần, chưa có
  bằng chứng nó gửi kết quả mô phỏng trở lại transport.
- **Unknown:** client có gửi kết quả qua một callback chưa khôi phục,
  qua method xử lý phần tử collection, hoặc qua một luồng nghiệp vụ khác
  hay không. Việc đã phân loại đủ 11 computed call chỉ đóng phạm vi của
  chính `0x060007C0`; chưa thể kết luận server-authoritative hoặc
  client-authoritative chỉ từ kết quả âm này.

## Tái lập

Tạo call inventory IL và lần tới enqueue:

```powershell
./scripts/inspect-il-calls.ps1 -TypeName '*' -TargetPattern '.*' -OutputPath 'analysis/generated/m3/all-il-calls.tsv'
./scripts/trace-il-reachability.ps1 -CallsPath 'analysis/generated/m3/all-il-calls.tsv' -StartTokens '0x06000A67','0x06000A6C','0x06000A6D' -TargetToken '0x0600028F' -MaxDepth 12
```

Ghidra read-only:

```text
-process GameAssembly.dll -noanalysis -readOnly
-scriptPath scripts/ghidra
-postScript InspectCallSites.java 1802870F0 1804098B0 180407C90 1804DFC60
-postScript InspectCallSites.java 180310280 18030FDB0
-postScript InspectInstructionWindow.java 1802875D0 180287730
-postScript InspectInstructionWindow.java 1802877D0 180287850
```

Log sinh ra nằm trong `analysis/generated/ghidra/` và bị Git ignore.
Script dùng để liệt kê đầy đủ call site là
`scripts/ghidra/InspectCallSites.java`.
