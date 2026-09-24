# Kết quả bổ sung M1: mạng, tài nguyên và làm rối

**Trạng thái:** Hoàn thành phần kiểm kê tĩnh

**Client:** Bản được nhận diện trong [client-inventory.md](client-inventory.md) và [hashes.sha256](hashes.sha256)

Tài liệu này chỉ ghi nhận dữ liệu đọc từ file. Không chạy client, không giải nén
asset ra repository và không kết nối đến bất kỳ địa chỉ tìm thấy nào.

## 1. Dấu hiệu mạng

Đã trích chuỗi ASCII và UTF-16LE (tối thiểu sáu ký tự) từ
`GameAssembly.dll`, `global-metadata.dat` và `resources.assets` bằng
`strings.exe -a -n 6 -t x -e s` / `-e l`. Đồng thời tìm chuỗi địa chỉ trên toàn
bộ thư mục client bằng `rg -a`. Dump tạm ở `analysis/generated/` được Git bỏ
qua.

| Dấu hiệu | Vị trí | Đánh giá |
| --- | --- | --- |
| `14.225.206.44` | `global-metadata.dat`, chuỗi ASCII tại offset `0x62B968` | **Inferred:** có thể là IP máy chủ game vì là một chuỗi riêng trong vùng gần các literal của client. Chưa xác nhận nó được dùng khi kết nối. |
| `127.0.0.1` | `GameAssembly.dll`, offset `0x132C608` | **Confirmed:** chuỗi nằm cạnh các literal `System.Net`/`Socket`; nhiều khả năng thuộc runtime .NET, chưa phải cấu hình game. |
| URL của Unity Analytics và tài liệu Unity | metadata/binary Unity | **Confirmed:** chuỗi thư viện/dịch vụ Unity có trong bản build. Chưa xác nhận client có gọi chúng lúc chạy. |

Không tìm thấy hostname game rõ ràng hoặc port có thể gắn chắc với IP ứng viên
trong các chuỗi đã trích. Tìm chuỗi đơn thuần không loại trừ endpoint được ghép
tại runtime, mã hóa hoặc lưu trong asset nhị phân. Việc xác định chính xác nơi
tạo kết nối thuộc M2–M3.

Chuỗi `https://localhost` xuất hiện trong một đoạn literal metadata bị nối với
chuỗi thư viện khác; chưa có cơ sở xem đó là endpoint của game. Các số có dạng
IPv4 trong chuỗi chứng chỉ/X.509 cũng không được tính là địa chỉ server game.

## 2. Danh mục archive và bản đồ

Đã liệt kê entry và đọc metadata ZIP bằng `tar -tf` và `ZipFile.OpenRead`, không
giải nén ra đĩa.

| Archive | Entry | PNG | File `.meta` | Entry có tên liên quan map |
| --- | ---: | ---: | ---: | ---: |
| `res_x1.zip` | 1.095 | 484 | 557 | 15 |
| `res_x2.zip` | 990 | 432 | 504 | 15 |
| `res_x3.zip` | 988 | 431 | 503 | 15 |
| `res_x4.zip` | 980 | 427 | 499 | 13 |

Cả bốn archive đều có `rpg/map0`, `rpg/map0.bytes`, `rpg/itemmap0`,
`rpg/itemmap0.bytes` và ảnh `map/t0.png` theo tỉ lệ tương ứng. `x1`–`x3` có
`randomMap.png`; `x4` không có entry này. Tên file trong ZIP dùng dấu `\` theo
cách đọc của `ZipFile` trên Windows, còn `tar` hiển thị bằng `/`.

`rpg/map0` và `rpg/itemmap0` trong `res_x1.zip` đều dài 1.000 byte và có ít
giá trị byte khác nhau. Chưa biết đây là bảng dữ liệu, placeholder hay chỉ mục.
Ảnh `map/t0.png` có dữ liệu riêng theo tỉ lệ. `resources.assets` cũng chứa các
chuỗi `randomMap` và `itemmap0`, nhưng định dạng asset chưa được giải mã.

**Kết luận:** Đã xác nhận một phần tài nguyên liên quan bản đồ nằm cục bộ.
Không thể kết luận client có toàn bộ map hoặc dữ liệu khởi tạo trận; cần tiếp
tục ở M2–M4.

## 3. Dấu hiệu làm rối

`ScriptingAssemblies.json` liệt kê `Assembly-CSharp.dll` và
`GUPS.Obfuscator.dll`. Trong metadata, ngay sau chuỗi `Assembly-CSharp` tại
offset `0x50B1C`, nhiều tên có dạng dài chỉ gồm `l`, `I`, `i` hoặc dạng
`p` + ký tự hex, ví dụ `p0BB904B7F6D927A1`. Đây là **bằng chứng trực tiếp**
rằng tên trong assembly của game đã bị làm rối; chỉ riêng tên package
`GUPS.Obfuscator.dll` sẽ không đủ để kết luận điều đó.

Các chuỗi `Encrypt`/`Decrypt` và `System.Net.Sockets` có trong metadata, nhưng
phần lớn thuộc thư viện .NET/Unity. Chưa xác nhận giao thức game có mã hóa,
nén hay cơ chế chống phân tích khi chạy.

## 4. Vấn đề chuyển sang M2

- Công cụ nào đọc được metadata IL2CPP của Unity `6000.5.10f1` với header
  `AF-1B-B1-FA-6B-00-00-00`?
- IP `14.225.206.44` được tham chiếu bởi method nào? Port và framing là gì?
- Tên type/method nào còn đủ nghĩa để lần theo kết nối và message handler sau
  khi làm rối?
- Dữ liệu bản đồ/trận nào nằm trong Unity assets, dữ liệu nào do server cấp?

Các câu hỏi này được giữ ở mức **Unknown** cho đến khi có bằng chứng từ mã hoặc
kiểm thử tái lập được.
