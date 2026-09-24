# Kiểm kê tĩnh client Army3

**Trạng thái:** M1 đã hoàn thành

**Nguồn:** `Mobiarmy3HA_3.0.0_GOC/` tại máy cục bộ

**Phương pháp:** chỉ đọc file; không chạy client và không kết nối server

## Nhận diện bản build

| Thuộc tính | Giá trị | Mức độ |
| --- | --- | --- |
| Tên ứng dụng trong `app.info` | `Mobi Army 3` / `Mobi Army 3 HA` | Confirmed |
| Phiên bản Unity từ thông tin file EXE và UnityPlayer | `6000.5.10f1 (3bd4f66ad299)` | Confirmed |
| Kiến trúc của EXE, GameAssembly và UnityPlayer | PE `Machine = 0x8664` (Windows x64) | Confirmed |
| Kiểu build | Unity IL2CPP: có `GameAssembly.dll`, `il2cpp_data/Metadata/global-metadata.dat` và `ScriptingAssemblies.json` | Confirmed |
| Header metadata, 8 byte đầu | `AF-1B-B1-FA-6B-00-00-00` | Confirmed |
| Build GUID trong `boot.config` | `054f63f7a24c4dda91ab221c22867f9c` | Confirmed |

Giá trị 4 byte sau magic của metadata chưa được diễn giải thành phiên bản định
dạng. Cần xác minh bằng công cụ IL2CPP ở M2, đặc biệt vì client có assembly tên
`GUPS.Obfuscator.dll` trong danh sách scripting assembly.

## Kích thước và thành phần

- Tổng cộng **148 file**, **400.505.328 byte** (khoảng **382 MiB**).
- Thành phần chương trình chính: `Mobi Army 3 HA.exe`, `GameAssembly.dll`,
  `UnityPlayer.dll` và các DLL hỗ trợ.
- Unity assets chính: `resources.assets` (116.663.576 byte),
  `resources.assets.resS` (50.577.296 byte), `resources.resource`
  (20.997.792 byte), cùng các file `globalgamemanagers`.
- Metadata IL2CPP: `global-metadata.dat` (8.880.512 byte).
- `StreamingAssets` có bốn archive `res_x1.zip` đến `res_x4.zip` và một số ảnh
  `vip/` nằm ngoài archive.

| Archive | Số entry | Nhóm nội dung thấy từ tên đường dẫn |
| --- | ---: | --- |
| `res_x1.zip` | 1.095 | `x1`, `effect`, `sound`, `hole`, `music`, `font`, `rpg` |
| `res_x2.zip` | 990 | `x2`, các nhóm dùng chung |
| `res_x3.zip` | 988 | `x3`, các nhóm dùng chung |
| `res_x4.zip` | 980 | `x4`, các nhóm dùng chung |

Tên đường dẫn trong archive cho thấy có ảnh, âm thanh, hiệu ứng và dữ liệu RPG,
nhưng chưa xác nhận format hay mức độ đầy đủ của nội dung.

## Chữ ký số

| File | Kết quả `Get-AuthenticodeSignature` |
| --- | --- |
| `Mobi Army 3 HA.exe` | `NotSigned` |
| `GameAssembly.dll` | `NotSigned` |
| `UnityPlayer.dll` | `Valid`, ký bởi Unity Technologies SF |

Kết quả chữ ký chỉ cho biết tình trạng ký file, không xác nhận toàn bộ client an
toàn để chạy. Chưa có phân tích động.

## Hash và cách tái lập

[`hashes.sha256`](hashes.sha256) là manifest SHA-256 cho toàn bộ 148 file, dùng
đường dẫn tương đối với thư mục client. Chạy từ thư mục gốc repository:

```powershell
.\scripts\inventory-client.ps1
```

Script chỉ đọc file và in thống kê cùng manifest. Để tạo lại riêng phần manifest:

```powershell
.\scripts\inventory-client.ps1 | Select-Object -Skip 5
```

Các dump tạm được lưu trong `analysis/generated/`, thư mục này bị Git bỏ qua.
Client gốc không được đưa vào repository.

## Kết quả M1

Xem [m1-findings.md](m1-findings.md) về địa chỉ mạng, tài nguyên bản đồ,
làm rối và các câu hỏi chuyển sang M2.
