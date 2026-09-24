# M3: Thử Ghidra trên GameAssembly.dll

**Trạng thái:** Ghidra chạy được; phân tích native chưa hoàn tất.

## Công cụ và đầu vào

- Ghidra `12.1.4_PUBLIC_20260921`, lấy từ
  [release chính thức](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build).
- SHA-256 ZIP Ghidra:
  `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`
  (khớp checksum trên release).
- Temurin JDK `21.0.12.1+1` bản ZIP portable, SHA-256:
  `f9d6e191ab098c0d416e7d588a24420a8621cd2f4720dab2459b8b7b2d2d8b4e`
  (khớp checksum do Adoptium công bố). Bản Ghidra này yêu cầu JDK 21 theo
  [Getting Started](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/GhidraDocs/GettingStarted.md).
- Ghidra và JDK nằm trong `tmp/ghidra/` và bị Git bỏ qua; không cài đặt hệ thống.
- Đầu vào: `Mobiarmy3HA_3.0.0_GOC/GameAssembly.dll`, chỉ đọc.
- Project và log: `analysis/generated/ghidra/`, bị Git bỏ qua.

## Lần chạy

Ghidra headless đã import `GameAssembly.dll` vào project `army3-native` và
phân tích với `-analysisTimeoutPerFile 600 -max-cpu 4`. Phân tích chạm giới hạn
600 giây và báo `Processing not completed`, nhưng import và save đều thành
công. Không có PDB, và trong log có vài cảnh báo decompile/demangle. Do vậy
project là **phân tích từng phần**, không phải kết quả native hoàn chỉnh.

Sau đó chạy [InspectSocketImports.java](../scripts/ghidra/InspectSocketImports.java)
trên project ở chế độ `-process GameAssembly.dll -noanalysis -readOnly`. Script
chạy thành công; project hiện có 43.094 function được nhận diện (con số tại
thời điểm phân tích từng phần).

## Bằng chứng mạng từ mã native

Ghidra xác nhận `GameAssembly.dll` có import `WS2_32.DLL::connect`,
`WSASend`, `WSARecv`, `send`, `socket`, `select`, `closesocket`, `ioctlsocket`,
`recvfrom`. Các ví dụ cross-reference được script trả về:

| Import | Function chứa tham chiếu | Địa chỉ tham chiếu |
| --- | --- | --- |
| `connect` | `FUN_180103790` | `0x1801037D8` |
| `WSASend` | `FUN_1801040E0` | `0x1801041AE` |
| `WSARecv` | `FUN_180104210` | `0x1801042F4` |
| `send` | `FUN_180103FC0` | `0x18010405C` |

**Confirmed:** những import và tham chiếu này tồn tại trong project native.
**Unknown:** chúng thuộc phần runtime/socket wrapper hay logic riêng của game;
chưa nối địa chỉ native với method token `0x0600028D` của DLL Cpp2IL khôi phục.
Không suy ra framing, port, payload hoặc message ID từ các import trên.

## Cập nhật

Đã nối method token Cpp2IL với ba hàm native của transport và xác định hai worker gửi/nhận; xem [m3-native-transport.md](m3-native-transport.md). Phần import socket ở trên vẫn chỉ là bằng chứng cho thư viện native, không phải call site protocol của game. State machine và mô phỏng trận vẫn chưa xác định.

Không chạy client và không truy cập server bên thứ ba.