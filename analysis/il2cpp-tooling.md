# M2: Phân tích metadata IL2CPP

**Trạng thái:** Hoàn thành bước trích xuất cấu trúc; chưa khôi phục giao thức.

## Công cụ và cách tái lập

- Cpp2IL Windows x64 development CI build `2022.1.0-development.1715+f92ff8b`.
- SHA-256 của `Cpp2IL.exe`:
  `7AFC9A908014483BBFB847E2A06C90231EA0318899C6215B9DB3A2C105E9C38D`.
- Nguồn tải: [README chính thức của Cpp2IL](https://github.com/SamboyCoding/Cpp2IL/blob/development/README.md), liên kết Windows Native Build. Liên kết CI có thể thay đổi nội dung; hash trên xác định đúng bản đã thử.
- Công cụ đặt mặc định tại `tmp/cpp2il/Cpp2IL.exe` và không đưa vào Git.

Sau khi người dùng cho phép chạy công cụ:

```powershell
./scripts/run-cpp2il.ps1 -OutputAs dll_empty
./scripts/run-cpp2il.ps1 -OutputAs diffable-cs
./scripts/index-cpp2il.ps1
```

Hai script cho phép truyền đường dẫn khác qua tham số. Chúng từ chối ghi đè
thư mục output không rỗng; muốn chạy lại, chọn một `-OutputDirectory` mới.
Output mặc định ở `analysis/generated/cpp2il/`, đã được Git bỏ qua. Script không
chạy client hay kết nối tới server game.

## Kết quả được xác nhận

Cpp2IL nhận Unity `6000.5.10f1`, đọc được file metadata có header version
`107` theo layout nội bộ `106`, tìm code/metadata registration trong
`GameAssembly.dll`, và ánh xạ 45.467 method definitions. Kết quả trích xuất:

| Chỉ mục | Số lượng |
| --- | ---: |
| Assembly | 80 |
| Tệp C# đại diện type | 5.155 |
| Chữ ký method trong tệp C# | 45.467 |
| Chữ ký field có offset | 22.449 |
| Tệp type trong `Assembly-CSharp` | 197 |
| Method/field trong `Assembly-CSharp` | 3.126 / 4.489 |

Danh sách đầy đủ nằm trong các file `assemblies.txt`, `type-files.txt`,
`method-signatures.txt`, `field-signatures.txt` ở thư mục index bị Git ignore.
Bộ đếm method/field của script dựa trên mẫu dòng text; đây là chỉ mục tìm kiếm,
không phải trình phân tích cú pháp C# đầy đủ. Số method khớp con số Cpp2IL báo.

Các chuỗi chọn lọc từ metadata ở M1: `14.225.206.44` (ứng viên endpoint,
offset `0x62B968`), `System.Net.Sockets`, `Encrypt` và `Decrypt`. Chỉ IP được
tìm trong vùng literal gần dữ liệu game; các chuỗi còn lại cũng có thể thuộc
thư viện hệ thống. Chưa xác định call site của bất kỳ chuỗi nào trong số này.

## Type mạng ứng viên

Trong 197 tệp C# của `Assembly-CSharp`, chỉ một tệp chứa `TcpClient`,
`NetworkStream`, `BinaryReader` và `BinaryWriter` dưới dạng các field tĩnh.
Đường dẫn tương đối từ thư mục `DiffableCs`:

```text
Assembly-CSharp/llllIllllIlIllIllIIIIIlIlllIIIlllllI/llllIlIIlIlIlIIIllIlIlIllllIIlIIIIlllllIlIIIlIllIllIIlIllIIIIIllIIIlIlII.cs
```

- **Confirmed:** các field trên ở dòng 63–67 của output `diffable-cs`.
- **Inferred:** type này là thành phần kết nối/đọc-ghi giao thức của game vì nó
  gom cả TCP stream và binary reader/writer. Chưa chứng minh type này thực sự
  được gọi ở runtime.
- **Inferred:** ba method instance nhận `(string, int)` tại dòng 113, 136, 144
  có thể liên quan đến endpoint, nhưng chữ ký không đủ để khẳng định method
  nào gọi `TcpClient.Connect`.
- **Unknown:** nơi tham chiếu chuỗi IP ứng viên từ M1, port, cấu trúc gói tin,
  mã hóa/nén và thứ tự message.

## Ảnh hưởng của obfuscation và giới hạn

196/197 tên tệp type trong `Assembly-CSharp` chỉ gồm chuỗi dài ký tự `l`/`I`;
tệp còn lại là `_Module_`. Nhiều tên method/field và tham số cũng bị làm rối.
Do đó không thể dựa vào tên để gán chức năng; phải kiểm tra call site hoặc mã
máy ở bước tiếp theo.

`dll_empty` chỉ tạo DLL cấu trúc với method body rỗng. `diffable-cs` cho chữ ký
và field nhưng không phục hồi source C# hay logic server. Đã thử chế độ
`dll_il_recovery` ở M3: nó cho phép tìm call site mạng, nhưng cũng bỏ qua hai
method rất lớn và chèn nhiều placeholder cho chỗ chưa giải mã được. Xem
[kiến trúc client](../docs/client-architecture.md). Cần đối chiếu mã máy trong
`GameAssembly.dll` trước khi ghi nhận chi tiết giao thức.

SHA-256 của `GameAssembly.dll` và `global-metadata.dat` vẫn khớp manifest M1
sau lần chạy đầu. Client không được thực thi; không có truy cập server bên thứ
ba. Xem thêm [ghi chú smoke test](m2-cpp2il.md).
