# M3: Vòng đời trạng thái biến đổi byte

Kết quả phân tích tĩnh của bản client đã hash ở M1; không chạy client hoặc
liên hệ server bên thứ ba. Địa chỉ native chỉ đúng cho bản này.

## Luồng đã xác nhận trong mã

1. Worker nhận `FUN_1804E3D60` phân nhánh theo byte lệnh của message.
   Khi byte đó là `0xE5` (Ghidra hiển thị `-0x1B`), nó gọi
   `FUN_1804E2E00` với object message. Các nhánh `0xA9` và `0x83` gọi
   helper khác; chưa xác định ý nghĩa của chúng.
2. `FUN_1804E2E00` lấy object dữ liệu từ field `+0x18` của message và gọi
   `FUN_1801A0450` để lấy một giá trị đầu dùng làm độ dài mảng tại field
   tĩnh `+0x68`. Nó gọi cùng hàm trong vòng lặp để lấp mảng, rồi thực hiện
   phép biến đổi tại chỗ `key[i+1] ^= key[i]` cho các phần tử kế tiếp.
   Một giá trị đọc tiếp được gán vào field `+0x70`; sau đó cờ `+0x60` được
   đặt thành `1`. `FUN_1801A0450` đọc một byte từ buffer tại field
   instance `+0x10` và tăng con trỏ đọc `+0x18`; đường hết buffer đi vào
   xử lý lỗi.

Ở mức byte, payload `0xE5` có cấu trúc đã xác nhận đến hết giá trị text-like:

```text
[N: byte] [seed[0] ... seed[N-1]] [shift: byte]
[textLength: i16 BE] [textBytes:textLength]
```

`FUN_1801A0680` đọc length hai byte theo thứ tự byte cao trước, chép đúng số
byte rồi gọi một virtual decoder để tạo object kết quả. Vì chưa ánh xạ decoder,
encoding và ý nghĩa của text vẫn `Unknown`.

Sau vòng biến đổi tại chỗ, key hiệu dụng là prefix-XOR:

```text
key[0] = seed[0]
key[i] = seed[i] XOR key[i-1]
       = seed[0] XOR ... XOR seed[i]
```

Client chỉ vào nhánh cấp phát khi `N != 0`. Decompiler biểu diễn `N` bằng
`char`; chưa thấy kiểm tra biên đủ để khẳng định mọi giá trị `128..255` hợp
lệ, nên chưa coi đây là miền độ dài được hỗ trợ. Trong thân
`FUN_1804E2E00` không thấy ghi hai index `+0x71/+0x72`; việc đặt cả hai về
0 nằm ở đường reset `FUN_1804E0EF0`. Vì vậy lần thiết lập đầu sau reset bắt
đầu ở index 0, còn hành vi re-key giữa phiên nếu không reset trước vẫn
`Unknown`.
3. Khi cờ bật, `FUN_1804E0400` và `FUN_1804E04F0` XOR byte qua cùng mảng
   `+0x68`, nhưng dùng chỉ số vòng riêng: `+0x71` cho nhận và `+0x72` cho
   gửi. Byte lệnh còn dùng giá trị `+0x70` (trừ ở chiều nhận, cộng ở chiều
   gửi). Xem [khung packet](m3-packet-framing.md).
4. Sau khi đọc giá trị text-like, nếu cờ transport `+0xB0` bằng `0`, client
   lưu object đó vào field `+0x30` của object phiên lấy từ `FUN_1804DED10`.
   Nếu `+0xB0` khác `0`, client gọi `FUN_1804E00C0` với subcommand `0`.
   Khi field phiên `+0x30` tồn tại, helper này tạo command logic `0xA9` với
   payload:

   ```text
   [subcommand:byte = 0]
   [storedText:length-prefixed value]
   [counter94:u32 BE]
   [counter90:u32 BE]
   ```

   Nếu field `+0x30` null, helper chỉ đặt cờ transport `+0x61/+0x60` và
   không gửi message. Tên `storedText/counter94/counter90` là nhãn cấu trúc,
   không phải ý nghĩa nghiệp vụ đã xác nhận.
5. `FUN_1804E0EF0` đặt cờ `+0x60`, mảng `+0x68`, giá trị `+0x70` và hai
   chỉ số `+0x71/+0x72` về `0`. Có call trực tiếp từ đường worker nhận
   `FUN_1804E3D60` và từ `FUN_1804E09B0`; hàm thứ hai đóng một object
   liên quan transport rồi gọi reset. Chưa xác định đủ mọi điều kiện đóng.

`Confirmed` ở đây là luồng lệnh trong binary, không xác nhận đã xảy ra
trong phiên chơi. `Inferred`: message `0xE5` đóng vai trò thiết lập trạng
thái biến đổi cho các packet tiếp theo. Không dùng tên gọi này để suy ra
định dạng toàn bộ payload hay hành vi server.

## Giới hạn

- Chưa có byte payload hợp lệ nên không biết giá trị khóa, chiều dài thực tế,
  hoặc client xử lý thế nào với độ dài biên/hỏng trong runtime.
- Encoding và ý nghĩa của giá trị text-like sau `shift` chưa xác định; cách
  đọc length/byte và gọi decoder đã thấy trong native.
- Không biết server gửi `0xE5` tại bước nào, việc bật cờ có bắt buộc cho mọi
  phiên không, hay có nhiều lần cập nhật khóa.
- Scanner tìm 12 phép gán ở 52/53 function có tham chiếu trực tiếp đến
  class transport trong project Ghidra phân tích từng phần. Một function
  decompile không hoàn tất và các đường ghi gián tiếp có thể bị bỏ sót.

## Chứng cứ tái lập

- `analysis/generated/ghidra/native-workers.log`: worker nhận, nhánh `0xE5`.
- `analysis/generated/ghidra/transport-key-init.log`: `FUN_1804E2E00`,
  `FUN_1804E0EF0`, `FUN_1804E00C0` và xref.
- `analysis/generated/ghidra/transport-key-read-reset.log`: helper đọc byte
  `FUN_1801A0450`, reader text-like `FUN_1801A0680` và đường đóng/reset
  `FUN_1804E09B0`.
- `analysis/generated/ghidra/transport-state-writes-v2-script.log`:
  kết quả của script chỉ đọc
  `scripts/ghidra/InspectTransportStateWrites.java` với class pointer
  `1814545B8`.
