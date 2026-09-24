# Kiến trúc client — M3 (đang khảo sát)

Tài liệu này chỉ dựa trên file client và IL do Cpp2IL khôi phục. Không chạy
client, không kết nối server bên thứ ba. `Confirmed` nghĩa là có thể kiểm tra
trực tiếp trong metadata hoặc output IL; nó không khẳng định nhánh mã đó đã chạy
trong một phiên game thực tế.

## Bằng chứng và cách tái lập

- Metadata và type: [báo cáo M2](../analysis/il2cpp-tooling.md).
- Cpp2IL `dll_il_recovery` được chạy bằng
  `./scripts/run-cpp2il.ps1 -OutputAs dll_il_recovery`.
- Truy vết lời gọi/chuỗi bằng
  [inspect-il-calls.ps1](../scripts/inspect-il-calls.ps1); các TSV sinh ra nằm ở
  `analysis/generated/m3/` và bị Git bỏ qua.
- Các token method dưới đây là token của `Assembly-CSharp.dll` **đã khôi phục**,
  không phải địa chỉ trong `GameAssembly.dll`.

## Đường kết nối tìm được

Type ứng viên transport là type duy nhất của `Assembly-CSharp` có đồng thời
field tĩnh `TcpClient`, `NetworkStream`, `BinaryReader` và `BinaryWriter`.
Tên type bị làm rối; xem đường dẫn và dòng 63–67 trong báo cáo M2.

| Bước | Bằng chứng trong IL khôi phục | Mức chắc chắn |
| --- | --- | --- |
| Gọi phương thức tạo thread kết nối | Method `0x060001C1` thuộc type khác gọi `0x0600028A`; hai method khác trong type transport cũng gọi `0x0600028A` | Confirmed trong IL khôi phục; hoàn cảnh gọi chưa rõ |
| Tạo thread | `0x0600028A` nhận `(string, int)` và lấy function pointer (`ldftn`) tới `0x0600028C` | Confirmed trong IL khôi phục |
| Wrapper gọi kết nối | `0x0600028C` gọi `0x0600028D` tại IL offset `0x02AC` | Confirmed trong IL khôi phục |
| Mở socket | `0x0600028D` nhận `(string, int)`; `newobj TcpClient::.ctor` ở `0x0043`, `TcpClient::Connect` ở `0x00C4` | Confirmed trong IL và ISIL; Connect nhận hai tham số `(string, int)` |
| Chuẩn bị I/O | Cùng method gọi `GetStream` ở `0x012D`, tạo `BinaryReader` ở `0x01CD` và `BinaryWriter` ở `0x0273` | Confirmed trong IL khôi phục |
| Khởi động worker | Cùng method gọi `Thread::Start` hai lần, tại `0x036F` và `0x0467` | Confirmed trong IL; native xác nhận hai worker gửi/nhận |

Chuỗi tóm tắt (không biểu diễn mọi nhánh điều kiện):

```text
caller 0x060001C1 hoặc caller nội bộ
  → tạo thread 0x0600028A
  → wrapper 0x0600028C
  → kết nối 0x0600028D
  → TcpClient.Connect → GetStream → BinaryReader/BinaryWriter
  → hai worker thread (đường gửi và đường nhận, theo native)
```

`0x0600028D` là điểm vào mạng quan trọng đầu tiên. Việc hai caller nội bộ gọi
`0x0600028A` **có thể** liên quan đến thử lại kết nối, nhưng không đủ bằng
chứng để gọi đó là reconnect. Chưa thấy bằng chứng xác nhận heartbeat.

Đối chiếu native cho thấy callback thứ nhất xử lý hàng đợi gửi qua `BinaryWriter`, callback thứ hai đọc message qua `BinaryReader`. Cả hai có lời gọi sleep `5`, nhưng chưa thể gọi đó là heartbeat. Chi tiết xem báo cáo transport native.

## Điểm khởi tạo và vòng đời Unity

`Assembly-CSharp` có bốn type trực tiếp kế thừa `MonoBehaviour` trong output
`diffable-cs`. Trong số đó có các tên method Unity còn nguyên như `Awake`,
`Start`, `Update`, `FixedUpdate`, `OnApplicationQuit`. Đây là **Confirmed** về
chữ ký type/method, không chứng minh thứ tự thực thi hoặc scene chứa chúng.
Chưa nối được các callback Unity tới caller `0x060001C1` hay transport type.

## Tài nguyên, mô phỏng và ranh giới server

- **Confirmed:** M1 đã tìm thấy một số tệp và ảnh liên quan bản đồ trong các
  archive `res_x*.zip`; xem [m1-findings.md](../analysis/m1-findings.md).
- **Unknown:** tài nguyên nào được load ở từng scene và dữ liệu nào do server
  gửi sau kết nối.
- **Unknown:** nơi tính vật lý, quỹ đạo, sát thương và thay đổi địa hình; chưa
  thể kết luận client hay server giữ vai trò mô phỏng chính.
- **Confirmed:** port khởi tạo là `19150`, nhưng có nhiều đường ghi đè host/port trước kết nối; xem [báo cáo endpoint](../analysis/m3-endpoint-state.md).
- **Unknown:** port thực tế ở mọi phiên, handshake, framing đầy đủ, ý nghĩa command ID, encoding của packet,
  heartbeat và reconnect.
- **Unknown:** chuỗi IP ứng viên `14.225.206.44` trong metadata có được method
  kết nối dùng hay không. Không thấy tham chiếu `ldstr` tới chuỗi đó trong IL
  khôi phục, nhưng công cụ có thể bỏ sót hoặc chuỗi có thể được truyền gián tiếp.

## Giới hạn của IL recovery

Cpp2IL báo bỏ qua hai method rất lớn. Trong trace của riêng type transport,
344/938 event là ghi chú `Cpp2ILInjected...NoteDecompilerIssue`; còn có nhiều
`Method not found`, `Indirect call` và unmanaged-memory placeholder. Bởi vậy
IL khôi phục có ích để định vị call site, nhưng chưa đủ để suy ra byte-level
packet hoặc chứng minh mọi nhánh runtime. Cần kiểm tra chéo bằng phân tích mã
máy khi cần, trước khi chuyển nhận định sang `Confirmed` về hành vi client.

## Đối chiếu native và việc tiếp theo

Đã đối chiếu method kết nối `0x0600028D` với native `0x1804DF5A0` và hai callback với `0x1804E2520` (đường gửi) / `0x1804E3D60` (đường nhận). Xem [báo cáo transport native](../analysis/m3-native-transport.md). Kết quả này xác nhận ranh giới transport ở mức cấu trúc, chưa xác nhận message ngữ nghĩa hay luồng màn hình.

1. Đã lần caller `0x060001C1` tới mảng chọn host/port; tiếp tục xác định callback Unity hoặc màn hình kích hoạt nhánh đó.
2. Xác minh các nhánh framing, biến đổi byte và xử lý lỗi ở native.
3. Liên kết state/tài nguyên với đăng nhập, lobby, phòng và trận.
4. Xác định nơi tính vật lý, sát thương và thay đổi địa hình trước khi chốt M3.