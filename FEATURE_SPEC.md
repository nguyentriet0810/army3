# Đặc tả tính năng: Army3 Offline 0.1.0

**Trạng thái:** Bản nháp 1

**Phạm vi:** Chơi cá nhân trên một máy Windows

**Liên quan:** [ROADMAP.md](ROADMAP.md), [AGENTS.md](AGENTS.md)

## 1. Mục tiêu

Người chơi mở client Army3 hiện có, kết nối tới server chạy trên chính máy của
mình, đăng nhập bằng hồ sơ cục bộ, tạo một phòng, chơi và kết thúc một trận cơ
bản mà không cần Internet.

Phiên bản `0.1.0` là mốc chứng minh luồng chơi hoàn chỉnh. Những tính năng và
thông số cụ thể sẽ được chốt sau khi xác nhận khả năng của client và giao thức.

## 2. Người dùng và môi trường

- Một người chơi sử dụng client Windows đang có trong
  `Mobiarmy3HA_3.0.0_GOC/`.
- Server tương thích chạy trên cùng máy, chỉ lắng nghe ở `127.0.0.1` theo mặc
  định.
- Dữ liệu người chơi được lưu trên máy và không cần tài khoản trực tuyến.
- Client gốc được giữ nguyên; mọi bước chuẩn bị bản chơi phải tái lập được.

## 3. Luồng chơi cần đạt

1. Người chơi khởi động môi trường offline theo hướng dẫn hoặc bằng launcher.
2. Client kết nối tới server cục bộ và hiển thị màn hình đăng nhập.
3. Người chơi chọn hoặc tạo một hồ sơ offline và vào màn hình chính.
4. Người chơi tạo phòng một người và chọn một bản đồ được hỗ trợ.
5. Người chơi bắt đầu trận, thực hiện các thao tác cơ bản và hoàn tất trận.
6. Client hiển thị kết quả, quay về phòng hoặc màn hình chính.
7. Sau khi khởi động lại, hồ sơ và tiến trình đã lưu vẫn sử dụng được.

Nếu giao thức yêu cầu nhiều người chơi để bắt đầu trận, server có thể tạo một
đối thủ cục bộ tối thiểu. Hành vi bot hoàn chỉnh thuộc giai đoạn sau.

## 4. Yêu cầu chức năng

| ID | Yêu cầu | Tiêu chí nghiệm thu |
| --- | --- | --- |
| F01 | Kết nối cục bộ | Client kết nối, bắt tay và duy trì phiên với server trên `127.0.0.1`. |
| F02 | Hồ sơ offline | Có thể vào game bằng hồ sơ cục bộ, không gọi dịch vụ xác thực bên ngoài. |
| F03 | Màn hình chính | Client nhận đủ dữ liệu bắt buộc để hiển thị màn hình chính ổn định. |
| F04 | Phòng chơi | Có thể tạo, vào, rời một phòng cục bộ và chọn một bản đồ được hỗ trợ. |
| F05 | Bắt đầu trận | Client tải bản đồ và chuyển sang trạng thái trận đấu. |
| F06 | Lượt chơi cơ bản | Người chơi có thể thực hiện các hành động tối thiểu mà client hỗ trợ để tiến tới kết thúc trận. |
| F07 | Kết thúc trận | Trận có kết quả hợp lệ và client có thể quay về phòng hoặc màn hình chính. |
| F08 | Lưu dữ liệu | Hồ sơ và tiến trình tối thiểu còn nguyên sau khi khởi động lại server. |
| F09 | Chạy offline | Luồng F01–F08 hoạt động khi máy bị ngắt Internet. |

## 5. Yêu cầu chất lượng

- Server xử lý gói tin sai hoặc thiếu mà không bị dừng đột ngột.
- Các bước tạo hồ sơ và khởi động lại có kết quả dự đoán được; người dùng có
  cách đặt lại dữ liệu cục bộ.
- Địa chỉ và cổng server có thể cấu hình, nhưng mặc định chỉ dùng loopback.
- Log đủ để chẩn đoán lỗi kết nối và trạng thái trận, không chứa mật khẩu,
  token hoặc thông tin nhạy cảm.
- Mã nguồn, test và script có thể dựng lại môi trường từ client gốc mà không cần
  commit binary hoặc asset của game.

## 6. Ngoài phạm vi của 0.1.0

- Multiplayer qua Internet, máy chủ công cộng và ghép trận trực tuyến.
- Thanh toán, nạp tiền, quảng cáo và các dịch vụ thương mại.
- Tái tạo đầy đủ cửa hàng, nhiệm vụ, sự kiện, xếp hạng và kinh tế của server cũ.
- Hỗ trợ mọi bản đồ, nhân vật, vật phẩm hoặc mọi phiên bản client.
- Bot nâng cao và cân bằng độ khó.

Các mục này chỉ được xem xét sau khi đã có một trận offline cơ bản hoạt động.

## 7. Điều kiện kỹ thuật cần xác minh

Những điểm sau hiện chưa phải yêu cầu đã chốt; kết quả phân tích M1–M4 sẽ quyết
định cách triển khai:

- Endpoint và giao thức mạng của client.
- Cơ chế xác thực, mã hóa, nén hoặc kiểm tra phiên bản.
- Dữ liệu bắt buộc để client hiển thị màn hình chính và vào trận.
- Phần mô phỏng trận đấu do client hay server chịu trách nhiệm.
- Cách chuyển hướng client về localhost ít xâm lấn nhất.
- Khả năng bắt đầu trận với một người chơi; nếu không, định dạng đối thủ cục bộ
  tối thiểu.

Ghi kết quả có bằng chứng vào tài liệu phân tích trước khi thay đổi yêu cầu hoặc
chọn kiến trúc server.

## 8. Cách nghiệm thu phiên bản 0.1.0

Trên một máy có client gốc và bản build server từ source:

1. Khởi động server và client theo tài liệu.
2. Ngắt Internet hoặc chặn toàn bộ kết nối ra ngoài của hai chương trình.
3. Thực hiện liên tục luồng ở mục 3, từ đăng nhập đến kết thúc trận.
4. Khởi động lại server và xác nhận hồ sơ cục bộ vẫn sử dụng được.
5. Xác minh server chỉ lắng nghe trên loopback và client không cần kết nối tới
   dịch vụ bên ngoài trong toàn bộ luồng.

`0.1.0` hoàn thành khi F01–F09 đạt trên một bản client đã ghi hash, các lỗi còn
biết được ghi lại, và quy trình có thể lặp lại theo tài liệu trong repository.
