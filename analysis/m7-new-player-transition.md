# M7: Danh sách khu vực/phòng sau `Chơi mới`

Phân tích này dùng bản client M1 và phiên runtime cô lập firewall ngày
2026-09-29. Client chỉ có một socket TCP tới `127.0.0.1:19150`.

## Kết luận hiện tại

- `Confirmed`: revision `0xC4` phải khớp byte cache `vcBig`. Cache của
  phiên cuối là `3`; cache-hit bỏ qua resource download và tới màn hình
  account.
- `Confirmed`: client hiển thị `Chơi mới`, `Chọn tài khoản` và dòng
  chọn server; socket vẫn sống và server tiếp tục heartbeat.
- `Confirmed`: lần bấm đầu vào `Chơi mới` chỉ dựng list mode `2` từ dữ
  liệu local, không gửi packet. Khi chọn mục đầu của list, client gọi
  `FUN_180313C20(session, 0, 0xFF, 0)`, gửi command `0xE4` payload `00`,
  rồi bật màn hình tải. Quan sát runtime cũ chỉ theo dõi lần bấm đầu nên
  kết luận "không có command mới" trước đây chưa bao phủ thao tác chọn cuối.
- `Confirmed`: helper UnityWebRequest không còn request đang chờ và helper
  file I/O ở state idle. Cache `dataItem` rỗng không phải bằng chứng trực tiếp
  cho blocker.
- `Confirmed`: màn hình xanh là overlay tại static field `UI manager +0xA0`;
  main screen phía dưới vẫn là login screen. Overlay chứa đúng một chuỗi
  `Cần quan sát tốc độ gió trước khi bắn` và ba callback `+0x10/+0x18/+0x20`
  đều null tại thời điểm bị kẹt.

## Mapping nút account và sender `0xE4`

`FUN_1801A2FE0` dispatch theo index menu:

| Index | Hành vi tĩnh | Mức chắc chắn |
| --- | --- | --- |
| `0` | gọi `FUN_1801A2DB0`, dựng list local mode `2` | `Confirmed` |
| `1` | khi app sẵn sàng, gửi `0x9E/selector 0` | `Confirmed` |
| `2` | gọi sender chọn server | `Confirmed` |

Thứ tự này khớp ba control nhìn thấy. `FUN_1801A2DB0` đọc object global,
kiểm tra dword `+0x358`, rồi qua `FUN_1801A2160` và `FUN_1801A7C90`
để dựng list mode `2`; nhánh này chưa gửi network.

Dispatcher `FUN_1801A2FE0` cũng xử lý lựa chọn tiếp theo. Với mode `2`,
selector tài khoản đầu và selected index `0`, nó gọi callback UI rồi
`FUN_180313C20(..., 0, 0xFF, 0)`. Sender tạo:

```text
client 0xE4 payload: [mode:u8 = 0]
wire frame chưa transform: E4 00 01 00
```

Sau enqueue, sender gọi `FUN_1804EA350`, routine bật loading controller và chọn
tip hiện tại. Đây là edge còn thiếu giữa thao tác người dùng, packet
outbound và overlay màu xanh.

## Response `0xE4`

`Confirmed` từ jump table `0x180256C88`:

```text
command 0xE4 -> entry 98 -> 0x18021FBD9
```

Handler lấy reader của message và đọc một signed byte đầu tiên. Nếu byte bằng
`1`, nhánh ngắn không đọc thêm payload; localization `0x692` giải mã thành
`Nhập mật khẩu của phòng`. Nhánh này dựng hộp thoại nhập liệu trên object
`UI manager +0x80`; nó không phải response tạo người chơi mới.

Nếu selector khác `1`, handler lặp tới khi reader hết payload. Schema tĩnh:

```text
server 0xE4 payload:
  [selector:u8 != 1]
  repeated until payload exhausted:
    [areaId:s8]
    if areaId != -1:
      [flag11:u8]
      [flag13:u8]
      [occupancy:u8]
      [capacity:u8]
      [money:u32 BE]
    [name:string16]
```

Localization liên quan xác nhận ngữ cảnh: `0x3DB = Tìm khu vực`,
`0x846 = Tạo khu vực`, `0x2B9 = money room= `, `0x609 = /` và
`0x88E = id = `. Vì vậy `areaId`, `occupancy`, `capacity`, `money` là tên
`Inferred` có bằng chứng consumer; hai byte flag vẫn để tên cấu trúc. Cuối
nhánh list, handler gọi `FUN_1804EA920` để reset loading controller.

Server Python hiện parse nghiêm request `E4 00 01 00` và trả selector `0`
cùng một record `Khu vực Local` trong state `ACCOUNT_PANEL_READY`. Unit và
integration test bao phủ codec, transform và state transition. Một lần push
chủ động sau `0xDB` giữ kết nối sống, nhưng inspector thấy `UI manager +0xA8`
đã tồn tại trong khi pointer record dự đoán ở `+0x230` vẫn null. Do đó parser
acceptance ở runtime chưa được nâng thành `Confirmed`: response có thể tới
trước khi màn hình sẵn sàng hoặc offset/object lưu record cần hiệu chỉnh.

## Overlay và primitive đóng

`Confirmed`: `FUN_180458EA0` ghi `0` vào `UI manager +0xA0` kèm write
barrier. `FUN_18029D590` cấu hình overlay; `FUN_18029D3D0` kích hoạt nó.
Update `FUN_1804E4850` chỉ gọi callback input nếu callback khác null, nên overlay
hiện tại không tự đóng qua input. Callback ID `0x22B2` trong `FUN_180459240`
gọi primitive đóng; `0x0FA0/0x22B2` là ID method/callback, không phải timeout.

`Confirmed`: response cần thiết đã được nối với command `0xE4`; nó không còn
là một server-push command chưa biết. Selector `1` thuộc flow mật khẩu phòng;
nhánh list mới là ứng viên hoàn tất request mode `0` và gọi loading-reset.

Không phát chủ động `0x9E`: selector `0` của command này thuộc nút
`Chọn tài khoản`, không phải `Chơi mới`.

## Bằng chứng tái lập

- `FUN_1801A2DB0`, `FUN_1801A2160`, `FUN_1801A7C90`: dựng list local.
- `FUN_1801A2FE0`, `FUN_180313C20`: route chọn mục và sender `0xE4`.
- jump-table entry `98`, `0x18021FBD9`: handler response `0xE4`.
- `FUN_1804EA350` / `FUN_1804EA920`: bật/tắt loading controller.
- `FUN_180263140` / `FUN_180263F70`: activation live của object `+0x80` và
  writer thay overlay `+0xA0`.
- `FUN_18029D590`, `FUN_18029D3D0`, `FUN_1804E4850`: cấu hình, kích hoạt
  và update overlay.
- `FUN_180458EA0`: xóa `UI manager +0xA0`.
- `FUN_180459240`, case callback `0x22B2`: gọi primitive xóa overlay.
- `scripts/ghidra/TraceIncomingToRange.java`: reverse direct-call không tìm thấy edge
  trực tiếp từ primitive đóng vào dispatcher, phù hợp virtual/callback path.
- `tools/inspect_runtime_state.py` và `tools/inspect_runtime_vtable.py`: inspector
  chỉ-đọc cho phiên client đã được người dùng cho phép.

Bước tiếp theo là xác định chính xác writer/object của record trong nhánh list,
sau đó chạy lại client cô lập và trả response theo request mode `0` thực tế
thay vì push sớm. Khi record xuất hiện, chọn khu vực/phòng và capture command
kế tiếp.
