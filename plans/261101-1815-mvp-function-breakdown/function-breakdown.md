# Function backlog — PII detection và secure PDF redaction MVP

Trạng thái: bản phân rã để giao việc, chưa phải đặc tả code đã triển khai. Ngày: 2026-11-01.

## Phạm vi và cách sử dụng

- Đã chốt: 7 thành viên, khoảng 10–11 tuần; web có đăng nhập trên server riêng; chỉ dùng dữ liệu công khai hoặc tổng hợp; huấn luyện trên Colab Pro.
- PDF tiếng Anh native, scan và mixed; tự động phát hiện chữ in; chữ viết tay/chữ ký được khoanh vùng thủ công.
- Sáu nhóm PII đề xuất: tên người, email, điện thoại, địa chỉ, ngày sinh và mã định danh cá nhân. Chính sách nhãn và hệ mã ID còn chờ CORE-01; chưa mặc định hỗ trợ toàn cầu.
- Function code là mã chức năng/work package để giao việc, không bắt buộc tương ứng một hàm lập trình, endpoint hay pull request. Mã giữ ổn định khi đổi owner hoặc thứ tự ưu tiên; không đưa mã vào production comments hay tên migration.
- Mỗi function có một owner chịu trách nhiệm cuối. Cơ cấu chuyên môn đã chốt: ML1 (1 ML), CS1/CS2 (2 Cyber Security), SE1–SE4 (4 Software Engineer). Đã hoàn tất gán 7 thành viên chính thức vào cột Assignee trong CSV và backlog.
- Phụ thuộc là điều kiện tích hợp/nghiệm thu. Các nhóm có thể lập trình đồng thời theo contract đã chốt; không dùng mock để tuyên bố hoàn thành.
- Mỗi việc phải có bằng chứng kiểm tra phù hợp; các ca liên quan dữ liệu/quyền/redaction cần kiểm thử lỗi và reviewer khác owner. Một task lớn có thể chia subtasks nhưng giữ nguyên mã cha.
- Size S/M/L là độ lớn tương đối, không phải ngày công. P0 là gate an toàn/hợp đồng; P1 vẫn là phần bắt buộc của MVP, không phải tính năng tùy chọn.
- Workflow: TODO → IN_PROGRESS → IN_REVIEW → DONE; BLOCKED kèm blocker. Không đánh DONE nếu thiếu evidence hoặc gate bắt buộc chưa chạy.
- Markdown này là đặc tả chức năng; CSV là bảng tracking. Phase files tham chiếu mã, không chép lại acceptance. Khi đổi phạm vi phải cập nhật Markdown và CSV cùng nhau.

## Phân công theo cơ cấu 1 ML, 2 Cyber Security, 4 Software Engineer

Mã vai trò không phải tên thật: ML1, CS1, CS2, SE1, SE2, SE3, SE4. Prefix function mô tả miền chức năng, không bắt buộc trùng chuyên môn người thực hiện; ví dụ ML-04 (regex) giao SE4, ML-03 (serving) giao SE2.

| Vai trò | Assignee (Tên thật) | Trách nhiệm chính | Function owner | Số mã |
|---|---|---|---|---|
| ML1 — Machine Learning | Nguyễn Đăng Đạt (ICT) | Baseline mô hình, preprocessing, fine-tune/checkpoint trên Colab Pro và đánh giá ML | ML-01, ML-02, ML-05, ML-07 | 4 |
| CS1 — Security Engineering | Nguyễn Quang Anh (CS) | Chính sách PII, phân quyền/audit, kiểm tra vùng và dữ liệu ẩn, resource isolation, ma trận an toàn và race tests | CORE-01; BE-03/12; RED-01/02/05; QA-01/05; OPS-03 | 9 |
| CS2 — Security Verification | Hoàng Thị Kiều Ly (CS) | Verification độc lập, fixture đối kháng, kiểm thử redaction/quyền truy cập và nghiệm thu | DATA-05; VER-01–06; QA-03/04/07 | 10 |
| SE1 — Frontend | Đỗ Minh Tấn (ICT) | Giao diện, viewer, duyệt vùng và E2E sản phẩm | FE-01–12; QA-02 | 13 |
| SE2 — Backend và vận hành | Nguyễn Đinh Phú Vinh (ICT) | Kiến trúc hệ thống, API/jobs/storage/revision, tích hợp model serving, server demo và đồng thiết kế model | CORE-03; BE-01/02/04–11; ML-03; OPS-01/02/04/05 | 16 |
| SE3 — Document/OCR | Nguyễn Tuấn Vinh (ICT) | Extraction, OCR, geometry và mapping entity thành vùng | CORE-02; OCR-01–09; ML-08 | 11 |
| SE4 — Data và PDF engine | Dương Minh Đức (ICT) | Dữ liệu, regex/hybrid, redaction text/ảnh, xuất PDF và benchmark sản phẩm | DATA-01–04/06; ML-04/06; RED-03/04/06/07; QA-06 | 12 |

### Ranh giới trách nhiệm ML và SE

- ML1 (Nguyễn Đăng Đạt) chịu trách nhiệm chính về ML-01, ML-02, ML-05 (trực tiếp chạy Colab Pro fine-tune checkpoint) và ML-07. SE2 (Nguyễn Đinh Phú Vinh) phối hợp đồng thiết kế kiến trúc mô hình, schema nhãn và chuyển giao cho Đạt chạy Colab Pro.
- SE4 (Dương Minh Đức) chuẩn bị nguồn, annotation, dedup/split, regex và code kết hợp kết quả. ML1 duyệt DATA-02/03/06 và ML-04/06; SE không tự thay taxonomy hoặc tune threshold trên test.
- SE2 (Nguyễn Đinh Phú Vinh) đóng gói, load và tích hợp model do ML1 bàn giao; SE3 (Nguyễn Tuấn Vinh) ánh xạ spans sang vùng PDF.
- Reviewer SE4 của ML-01/02/05/07 kiểm tra dữ liệu, cấu hình, metrics, artifact và khả năng tái lập. Quyết định chạy và huấn luyện trên Colab Pro thuộc ML1.
- SE2/SE4 hỗ trợ môi trường, dữ liệu và pipeline tích hợp cho ML-05.

### Ranh giới Security và SE

- CS1 trực tiếp phụ trách các function security được giao, phối hợp SE2 tích hợp middleware/audit/isolation và SE4 tích hợp validation/sanitization vào engine. CS1 có deliverable code/kiểm tra rõ, không chỉ viết báo cáo.
- CS2 xây verification và kiểm thử độc lập; không đồng thời là owner các function RED. RED có reviewer CS2; QA-03 có reviewer SE3, giúp không để người viết RED tự xác nhận an toàn.
- SE vẫn phải thực hiện validation, xử lý lỗi và kiểm thử của phần mình. Hai thành viên security không gánh mọi bug hay thay thế unit/integration test của SE.
- CSV có cột contributors cho hỗ trợ liên module; chỉ owner chịu trách nhiệm đóng task, reviewer kiểm tra evidence. Một function vẫn chỉ có một owner; assignee tên thật còn trống.
- Số mã không phải ngày công: 4 mã của ML1 bao gồm fine-tune/experiments; SE2 có 16 mã và là điểm có thể nghẽn tích hợp. CORE-03 phải chốt ranh giới file/module khi nhiều người cùng đóng góp; sau đó ước lượng theo năng lực và giờ tham gia, không chia đều số mã.

## Hợp đồng liên module phải chốt ở P1

1. Mô hình dữ liệu: Document → Page → Token/normalized text → Entity → Region → ReviewRevision → ExportArtifact → VerificationReport.
2. Tọa độ lưu trên trang PDF: đơn vị, gốc, page/crop box, rotation, forward/inverse transform. FE chỉ biến đổi góc nhìn theo contract, không tự suy diễn tọa độ OCR.
3. Entity có offset, nhãn, nguồn và model version; Region có trang, nhiều rectangle khi nhiều dòng và provenance. Confidence OCR khác confidence mô hình.
4. Bản gốc bất biến; mỗi export gắn document hash, review revision, vùng xóa và phiên bản pipeline. Sửa review làm export cũ mất hiệu lực; không để tác vụ cũ ghi đè tác vụ mới.
5. Gợi ý residual mới chưa duyệt làm mất hiệu lực snapshot và quay về review revision mới; gợi ý đã bị từ chối trên nội dung không đổi không gây vòng lặp. BE kiểm tra dấu đã xóa và revision ngay trước publish.
6. Giới hạn tài nguyên/cách ly parser có trước xử lý PDF; preview không thực thi active content hoặc external fetch.
7. Mandatory verification: PASS/FAIL/INCONCLUSIVE; FAIL/INCONCLUSIVE không được xuất chính thức. Phân tích lỗi/chưa duyệt không trở thành tài liệu đã sạch.
8. Trạng thái phát hiện, người dùng đã duyệt và verification redaction độc lập; không gộp thành bảo đảm đã tìm hết PII. Quét lại bằng cùng model/OCR chỉ là tín hiệu bổ sung.

## Function inventory

Mỗi hàng dưới đây có deliverable trong cột phạm vi, điều kiện nghiệm thu và dependency. Owner/reviewer/contributors/size/status đầy đủ ở [CSV giao việc](./function-backlog.csv).

### CORE — Hợp đồng và chính sách (3 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| CORE-01 | Chốt chính sách PII | Định nghĩa sáu nhóm đề xuất, ví dụ âm/dương, hệ mã định danh và quy tắc xóa | Có taxonomy versioned và quyết định phạm vi mã ID; từng nhãn có ví dụ và ranh giới rõ | — | CS1 | P1 |
| CORE-02 | Chốt hợp đồng tài liệu và tọa độ | Document, Page, Token, Entity, Region, ReviewRevision và nguồn native/ocr/manual | Có ví dụ thật cho trang xoay và thực thể nhiều dòng; thống nhất PDF units, gốc tọa độ, crop và phép biến đổi | — | SE3 | P1 |
| CORE-03 | Chốt hợp đồng API và tác vụ | Trạng thái, lỗi theo trang, review revision, idempotency, schema dữ liệu và giới hạn đầu vào | FE/BE/OCR/RED thống nhất contract; khóa trạng thái xuất khi phân tích chưa đầy đủ hoặc kiểm tra thất bại | CORE-01, CORE-02 | SE2 | P1 |

### FE — Frontend (12 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| FE-01 | Đăng nhập và đăng xuất | Form đăng nhập, hết phiên và thông báo lỗi | Đăng nhập hợp lệ được; sai thông tin/hết phiên được xử lý; đăng xuất mất quyền truy cập | BE-01, BE-02 | SE1 | P2 |
| FE-02 | Tải PDF lên | Chọn file, tiến trình upload, giới hạn và lỗi phía người dùng | Upload thành công trả về tài liệu; lỗi định dạng/dung lượng hiển thị được và cho thử lại | BE-04 | SE1 | P2 |
| FE-03 | Danh sách tài liệu và tác vụ | Danh sách của tài khoản hiện tại, trạng thái và mở lại tác vụ | Không hiển thị tài liệu người khác; tải lại trang vẫn truy cập được tác vụ đã lưu | BE-05, BE-06 | SE1 | P2 |
| FE-04 | Hiển thị tiến trình và lỗi theo trang | Đang xử lý, trang lỗi, thử lại và trạng thái cần duyệt | Không hiển thị hoàn tất khi còn trang lỗi; retry hiển thị đúng tác vụ mới hoặc lần chạy mới | BE-06, BE-07 | SE1 | P2 |
| FE-05 | PDF viewer | Hiển thị bản gốc, chuyển trang, phóng to và xoay góc nhìn | Native/scan/mixed mở được, đúng số trang; viewer không thực thi active content/tải ngoài; zoom/rotate không sửa tọa độ lưu | BE-05, CORE-02 | SE1 | P2 |
| FE-06 | Overlay vùng PII | Vẽ vùng theo entity/region, loại và điểm tin cậy | Vùng bám đúng nội dung khi zoom/rotate/crop; không coi confidence là xác suất đã hiệu chỉnh | FE-05, ML-08 | SE1 | P2 |
| FE-07 | Danh sách và lọc kết quả PII | Lọc loại, chọn kết quả để đến đúng trang | Danh sách và overlay đồng bộ; không tìm thấy PII vẫn yêu cầu duyệt trực quan | FE-06 | SE1 | P2 |
| FE-08 | Duyệt gợi ý | Chấp nhận/bỏ chọn từng vùng và theo nhóm | Lựa chọn được lưu đúng revision; bỏ chọn không xóa kết quả phát hiện gốc | FE-07, BE-08 | SE1 | P2 |
| FE-09 | Khoanh vùng thủ công | Thêm/sửa/xóa vùng cho PII bị bỏ sót, chữ viết tay và chữ ký | Vùng nằm trong trang, tồn tại sau mở lại; tọa độ hiển thị và lưu khớp nhau | FE-05, BE-08 | SE1 | P2 |
| FE-10 | Xác nhận duyệt tài liệu | Theo dõi trang đã duyệt, nhắc chữ viết tay và chốt revision | Không xác nhận bản cũ khi vùng thay đổi hoặc có candidate mới; chỉ dẫn trở lại duyệt; trang chưa duyệt/lỗi và giới hạn chữ viết tay hiển thị rõ | FE-08, FE-09, BE-09 | SE1 | P2 |
| FE-11 | Xuất và tải kết quả | Kích hoạt redaction, xem kết quả kiểm tra và tải file | Chỉ tải artifact đúng revision đã kiểm tra; phân biệt lỗi với không phát hiện thêm PII | FE-10, BE-10 | SE1 | P2 |
| FE-12 | Xóa tài liệu | Xác nhận xóa, phản ánh hết hạn và liên kết đã thu hồi | Sau xóa không mở được bản gốc, preview hoặc kết quả; hiển thị tiến trình xóa nếu chưa xong | BE-11 | SE1 | P2 |

### BE — Backend (12 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| BE-01 | Quản lý tài khoản demo | Tạo tài khoản giới hạn, đăng nhập và lưu thông tin xác thực an toàn | Không cần đăng ký công khai; không lưu mật khẩu dạng rõ; thử đăng nhập sai có giới hạn | CORE-03 | SE2 | P2 |
| BE-02 | Quản lý phiên truy cập | Xác thực, hết hạn và đăng xuất | API bảo vệ từ chối phiên hết hạn/đã thu hồi; đáp ứng chính sách phiên đã chọn | BE-01 | SE2 | P2 |
| BE-03 | Phân quyền tài liệu và artifact | Kiểm tra owner trên mọi thao tác và đường dẫn tải | Tài khoản A không đọc/sửa/xóa/tải tài liệu hay artifact của B dù biết ID | BE-02 | CS1 | P2 |
| BE-04 | Tiếp nhận và kiểm tra PDF | Kiểm tra nội dung file, size/pages, mã hóa, lỗi và tên file | Từ chối có lý do với file không hỗ trợ; không dùng đường dẫn upload do client tự chỉ định | BE-03, OPS-01, OPS-03 | SE2 | P2 |
| BE-05 | Lưu và truy xuất tài liệu | Bản gốc bất biến, preview, metadata và danh sách phân trang | Preview/bản gốc được phân quyền, không thực thi JavaScript/action/attachment hay tải tài nguyên ngoài; có checksum; storage private và response không content sniffing | BE-04 | SE2 | P2 |
| BE-06 | Điều phối pipeline | Gọi extraction/OCR, detection và mapping; lưu lỗi và tiến trình theo trang | Có kết quả hoàn chỉnh hoặc lỗi có cấu trúc; không âm thầm bỏ trang; ghi version pipeline | BE-05, OCR-09, ML-08, OPS-03 | SE2 | P2 |
| BE-07 | Thử lại và chống tác vụ trùng | Idempotency, timeout, hủy tác vụ và phục hồi khi worker dừng | Retry không ghi đè kết quả mới; hai yêu cầu trùng không tạo hai artifact chính thức | BE-06 | SE2 | P2 |
| BE-08 | Lưu và đọc quyết định duyệt | Accepted/rejected/manual regions với optimistic revision | Vùng ngoài trang bị từ chối; sửa đồng thời được báo xung đột; mở lại không mất quyết định | BE-05, CORE-02 | SE2 | P2 |
| BE-09 | Khóa snapshot đã duyệt | Xác nhận đủ điều kiện, lưu revision bất biến cho export | Chặn khi trang phân tích lỗi/chưa duyệt hoặc có candidate mới chưa xử lý; sửa review làm snapshot xuất cũ mất hiệu lực; lưu revision bất biến | BE-06, BE-08 | SE2 | P2 |
| BE-10 | Điều phối xuất và tải an toàn | Redaction, verification, báo cáo và kiểm tra quyền tải artifact | Chỉ phát hành khi mandatory checks đạt, revision còn hiệu lực và không có gợi ý mới chưa duyệt; kiểm tra dấu đã xóa ngay trước publish; không phát hành file tạm | BE-09, RED-07, VER-05, VER-06, BE-07, BE-11 | SE2 | P2 |
| BE-11 | Vòng đời và xóa dữ liệu | Xóa theo yêu cầu/retention, thu hồi truy cập, dọn input/preview/OCR/output/temp | Xóa áp dụng cả tài liệu chưa xử lý/xuất; đánh dấu đã xóa, hủy job và dọn mọi artifact; job không tái tạo file sau xóa | BE-03, BE-05, BE-07 | SE2 | P2 |
| BE-12 | Nhật ký xử lý | Ai, thao tác, thời điểm, document/revision/model IDs và kết quả | Không ghi raw PII, nội dung OCR, mật khẩu hoặc token vào log/báo cáo mặc định | CORE-03 | CS1 | P2 |

### OCR — Xử lý tài liệu và OCR (9 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| OCR-01 | Kiểm tra và phân loại trang | Phân loại native/scanned/mixed theo từng trang, không chỉ toàn file | Bộ mẫu có ba loại và trang hỗn hợp được nhận diện; lớp OCR cũ không mặc định được tin cậy | CORE-02 | SE3 | P2 |
| OCR-02 | Trích xuất văn bản native | Ký tự/từ, vị trí, trang, reading order và provenance | Có offset mapping; không mất nguồn vị trí do nối đoạn; báo lỗi khi không trích xuất được | OCR-01 | SE3 | P2 |
| OCR-03 | Render và tiền xử lý OCR | Chuẩn bị ảnh, xoay/deskew và lưu phép biến đổi | Ảnh có kích thước và transform rõ; đảo biến đổi về trang gốc kiểm tra được | OCR-01 | SE3 | P2 |
| OCR-04 | Nhận dạng chữ in tiếng Anh | OCR vùng ảnh/trang cần đọc, token và confidence | Trả token/bbox/confidence; trang không đọc được hoặc timeout có trạng thái riêng | OCR-03 | SE3 | P2 |
| OCR-05 | Chuẩn hóa văn bản cho ML | Nối dòng, khoảng trắng và ký tự nhưng giữ ánh xạ nguồn | Mọi span mô hình dùng truy ngược được token gốc; không tìm lại vị trí bằng text matching đơn thuần | OCR-02, OCR-04 | SE3 | P2 |
| OCR-06 | Khôi phục thứ tự đọc | Xử lý block, nhiều cột và bảng trong phạm vi layout hỗ trợ | Bộ mẫu layout đã chọn có chuỗi văn bản và mapping đúng; giới hạn layout được công bố | OCR-05 | SE3 | P2 |
| OCR-07 | Chuẩn hóa tọa độ PDF | Chuyển bbox ảnh/OCR về hệ tọa độ chung, rotation và crop | Kiểm tra trang xoay/crop/DPI khác nhau; round-trip điểm và vùng trong tolerance đã định nghĩa | OCR-03, OCR-04, CORE-02 | SE3 | P2 |
| OCR-08 | Đánh giá chất lượng trang | Lưu cảnh báo OCR thấp, nguồn bị thiếu và trang cần kiểm tra | Không kết luận không có PII từ OCR rỗng; lỗi nguồn/trang được BE và FE thể hiện | OCR-02, OCR-04 | SE3 | P2 |
| OCR-09 | Hợp nhất native và OCR | Duyệt ảnh chứa chữ trên trang mixed, khử trùng và giữ provenance | Không bỏ qua ảnh chỉ vì trang có text; một nội dung không nhân đôi do lớp OCR cũ | OCR-06, OCR-07, OCR-08 | SE3 | P2 |

### DATA — Dữ liệu và annotation (6 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| DATA-01 | Khảo sát dữ liệu và giấy phép | Nguồn public/synthetic, nhãn, giới hạn sử dụng và provenance | Có danh mục dataset cùng giấy phép/version; không đưa dữ liệu nhạy cảm thật vào project | CORE-01 | SE4 | P1 |
| DATA-02 | Chuẩn hóa annotation | Mapping nhãn, character offsets và hướng dẫn gắn nhãn | Kiểm tra span đúng substring; nêu nhãn không phủ đủ; ví dụ sai nhãn được rà soát | DATA-01, CORE-01 | SE4 | P1 |
| DATA-03 | Tách train/validation/test | Chống trùng lặp và leakage theo nguồn/template khi có thể | Có manifest tái lập, thống kê phân bố và dedup; test không dùng để tune hoặc chọn threshold | DATA-02 | SE4 | P1 |
| DATA-04 | Bộ tài liệu PDF chuẩn | Mẫu native/scan/mixed, handwriting thủ công và ground truth text/regions | Có ground truth text/regions; PDF đánh giá dùng nguồn held-out theo split, không dùng text train; phủ native/scan/mixed, handwriting thủ công và các layout/rotation/noise đã chọn | DATA-03, CORE-02 | SE4 | P2 |
| DATA-05 | Bộ ca redaction đối kháng | Mẫu text ẩn, OCR cũ, ảnh tái sử dụng, metadata/annotation/attachment và lịch sử lưu | Mỗi ca có nội dung mục tiêu và cách truy xuất kỳ vọng; synthetic có nhãn không chứa PII thật | DATA-04 | CS2 | P2 |
| DATA-06 | Version và báo cáo dữ liệu | Manifest train/PDF/security suites, class counts và data limitations | Mọi kết quả tham chiếu được dataset version; phân biệt PDF tổng hợp và mẫu public thực tế | DATA-04, DATA-05 | SE4 | P3 |

### ML — Phát hiện PII và huấn luyện (8 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| ML-01 | Baseline có thể tái lập | Baseline rule-based và pretrained phù hợp, cấu hình cố định | Báo cáo cùng taxonomy/split; công bố entity không hỗ trợ thay vì coi là true negative | DATA-03 | ML1 | P2 |
| ML-02 | Chuẩn bị dữ liệu huấn luyện | Token alignment, nhãn span/token và xử lý đoạn dài | Không làm lệch offset; cửa sổ chồng lấn có quy tắc ghép và kiểm thử thực thể ở ranh giới | DATA-03, CORE-02 | ML1 | P2 |
| ML-03 | Suy luận phát hiện PII | Nhận normalized text, trả entity spans, label, score và model version | Batch/empty/long text xử lý được; score không tự coi là probability; model load được ngoài Colab | ML-01, ML-02 | SE2 | P2 |
| ML-04 | Luật bổ trợ theo chính sách | Email, phone, DOB có ngữ cảnh, mã ID thuộc phạm vi đã chốt | Có ca đúng/sai gần giống; validation/checksum chỉ áp dụng cho hệ mã có quy tắc tương ứng | CORE-01, ML-01 | SE4 | P2 |
| ML-05 | Fine-tune và quản lý checkpoint | Train Colab Pro, checkpoint/resume, validation và xuất model | Có seed/config/log/version; resume thành công; chọn checkpoint bằng validation và chạy được trên server | ML-02, OPS-01 | ML1 | P2 |
| ML-06 | Kết hợp ML và luật | Resolve overlap/conflict, threshold theo validation và giải thích nguồn phát hiện | So sánh ML/rules/hybrid; không dùng test để tune; kết quả ổn định với input lặp lại | ML-03, ML-04, ML-05 | SE4 | P2 |
| ML-07 | Đánh giá và phân tích lỗi | P/R/F1 theo entity, exact/partial, OCR/native và bỏ sót/nhận nhầm | Có báo cáo test cố định, latency và ví dụ lỗi; đánh giá text chuẩn và text OCR để tách nguyên nhân | ML-06, DATA-06, OCR-09 | ML1 | P3 |
| ML-08 | Ánh xạ entity thành vùng | Span nhiều dòng, nhiều token và kết quả trùng thành regions có provenance | Không chỉ tìm lần xuất hiện đầu tiên; đúng trang, đủ các dòng; lỗi mapping được báo, không âm thầm bỏ | ML-03, OCR-09, CORE-02 | SE3 | P2 |

### RED — Redaction engine (7 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| RED-01 | Kiểm tra snapshot và vùng xóa | Revision, trang, vùng hữu hạn trong bounds và provenance | Từ chối snapshot sai hoặc vùng lỗi; không thay thế bản gốc bằng file đã xử lý | CORE-02, CORE-03 | CS1 | P2 |
| RED-02 | Hợp nhất vùng và padding | Xử lý vùng trùng/chồng, nhiều dòng và padding trong giới hạn trang | Không xóa vùng ngoài yêu cầu do merge tùy tiện; padding có ca ký tự sát mép | RED-01 | CS1 | P2 |
| RED-03 | Redaction nội dung native | Loại bỏ text/vector liên quan trong vùng đã chọn theo khả năng engine | Copy/search/extract không lấy lại nội dung mục tiêu; không chỉ phủ hình chữ nhật | RED-02 | SE4 | P2 |
| RED-04 | Redaction ảnh và lớp OCR | Xóa pixel/vùng ảnh, lớp text OCR; xử lý ảnh được tái sử dụng và trang mixed | Ảnh trích xuất không còn nội dung mục tiêu; cả pixel và OCR layer bị xử lý; không tái gắn ảnh gốc | RED-02, OCR-07 | SE4 | P2 |
| RED-05 | Làm sạch dữ liệu ẩn | Metadata, comments, forms, attachments, hidden layers và active content theo chính sách hỗ trợ | Nội dung phải loại bỏ không còn trong artifact; cấu trúc không xử lý được bị từ chối rõ | RED-03, RED-04, DATA-05 | CS1 | P2 |
| RED-06 | Ghi PDF sạch và bảo toàn nội dung | Ghi file mới không giữ incremental history; bảo toàn phần không redaction theo phạm vi hỗ trợ | File mở được; không chứa bản gốc đính kèm/object cũ cần loại; page geometry và phần giữ lại được kiểm tra | RED-05 | SE4 | P2 |
| RED-07 | Artifact export bất biến | Checksum, revision, vùng đã áp dụng và ghi file tạm rồi hoàn tất | Artifact gắn đúng snapshot; lỗi giữa chừng không để file tải chính thức; đầu vào không bị sửa | RED-06 | SE4 | P2 |

### VER — Kiểm tra đầu ra (6 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| VER-01 | Kiểm tra text còn sót | Trích xuất lại và kiểm tra mục tiêu tại vùng/phạm vi cần loại | Phát hiện fixture chỉ phủ màu; không đánh fail nếu chuỗi trùng ở vùng được phép giữ | RED-07, DATA-05 | CS2 | P2 |
| VER-02 | Kiểm tra ảnh và OCR đầu ra | Render lại, OCR và kiểm tra ảnh nhúng tại vùng mục tiêu | Phát hiện pixel chưa xóa hoặc OCR layer còn sót; failure/inconclusive không thành pass | RED-07, DATA-05 | CS2 | P2 |
| VER-03 | Kiểm tra cấu trúc và dữ liệu ẩn | Metadata, attachment, form, hidden objects/history theo chính sách | Fixture dữ liệu ẩn rò rỉ bị fail; công bố những cấu trúc được phép/không được phép còn lại | RED-07, DATA-05 | CS2 | P2 |
| VER-04 | Kiểm tra độ toàn vẹn đầu ra | Mở/render, số trang, geometry và ảnh hưởng ngoài vùng xóa | File hỏng, trang thiếu và thay đổi ngoài vùng vượt tolerance bị phát hiện | RED-07, DATA-04 | CS2 | P2 |
| VER-05 | Tổng hợp kiểm tra và báo cáo | Mandatory checks pass/fail/inconclusive, revision, version và bằng chứng không raw PII | Bất kỳ fail/inconclusive bắt buộc đều chặn xuất; không tuyên bố hết PII; không tự cấp pass cho check chưa chạy | VER-01, VER-02, VER-03, VER-04 | CS2 | P2 |
| VER-06 | Quét PII còn sót | Tìm tín hiệu PII ngoài vùng đã chọn và tạo cảnh báo cho vòng duyệt mới | Gợi ý mới chưa được duyệt làm snapshot xuất mất hiệu lực và yêu cầu duyệt revision mới; không lặp lại gợi ý đã bị từ chối trên nội dung không đổi; không chứng minh hết PII | VER-05, ML-06 | CS2 | P2 |

### QA — Kiểm thử và nghiệm thu (7 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| QA-01 | Ma trận nghiệm thu và ngưỡng chất lượng | Scope PDF, PII, security, latency, kích thước file và tiêu chí pass | Ngưỡng được chốt trước test cuối; có trace từng tiêu chí đến function code và evidence | CORE-01, CORE-02, CORE-03 | CS1 | P1 |
| QA-02 | E2E luồng sản phẩm | Native/scan/mixed, review thủ công/PII detection, export và tải lại | Cả ba loại tài liệu chạy trọn luồng; trường hợp không có gợi ý vẫn cần duyệt | FE-11, DATA-04, OPS-02 | SE1 | P2 |
| QA-03 | Kiểm thử an toàn redaction độc lập | Tấn công copy/search/extract/images/hidden data trên artifact | Bộ fixture đối kháng phát hiện được engine lỗi; có kiểm tra thủ công độc lập với RED | VER-05, DATA-05 | CS2 | P3 |
| QA-04 | Kiểm thử quyền truy cập | Hai tài khoản, session expiry, direct URLs và các endpoint sửa/xuất/xóa | Không đọc/sửa/tải artifact chéo tài khoản; input giả mạo và phiên hết hạn bị từ chối | BE-03, BE-08, BE-10, BE-11, FE-01 | CS2 | P3 |
| QA-05 | Kiểm thử lỗi và tranh chấp tác vụ | PDF lỗi/mã hóa, trang timeout, retry, sửa review khi export, xóa khi job chạy | Không xuất snapshot cũ, không khôi phục file đã xóa và không báo hoàn tất giả khi thiếu trang | BE-07, BE-09, BE-10, BE-11, BE-12, RED-07, FE-12, OCR-08 | CS1 | P3 |
| QA-06 | Hiệu năng và chất lượng sử dụng | Latency/memory theo trang, concurrency, zoom/rotate, bàn phím và công sức review | Benchmark trên máy mục tiêu; không vượt giới hạn chốt; ghi thao tác sửa và thời gian so với làm thủ công | QA-02, ML-06, OPS-03 | SE4 | P3 |
| QA-07 | Nghiệm thu phát hành | Tập test cố định, báo cáo ML/engine/product, runbook và lỗi còn mở | Các gate bắt buộc đạt; có bằng chứng, giới hạn được công bố và kịch bản demo tái lập | QA-03, QA-04, QA-05, QA-06, ML-07, DATA-06, OPS-05 | CS2 | P4 |

### OPS — Triển khai và vận hành (5 functions)

| Code | Chức năng | Phạm vi / đầu ra | Điều kiện hoàn thành | Phụ thuộc | Owner | Mốc |
|---|---|---|---|---|---|---|
| OPS-01 | Môi trường và cấu hình phiên bản | Môi trường dev/Colab/server, dependency/model pinning và secrets không commit | Nhóm khởi chạy tái lập; model/config có version; không ghi secret vào artifact/log | — | SE2 | P1 |
| OPS-02 | Triển khai demo có đăng nhập | Build/deploy trên server riêng, HTTPS và private storage | Demo truy cập HTTPS; file không public; deployment dùng model version cố định | OPS-01, BE-02, BE-05 | SE2 | P2 |
| OPS-03 | Giới hạn tài nguyên xử lý | Timeout, memory/CPU/pages, worker concurrency và cách ly parser/OCR | Giới hạn và cách ly có trước khi parser/OCR xử lý file; timeout có lý do; không quyền truy cập ngoài storage cần thiết hoặc network tùy ý | OPS-01 | CS1 | P2 |
| OPS-04 | Quan sát và kiểm tra sức khỏe | Health/readiness, metrics, dung lượng và cảnh báo tác vụ lỗi | Phát hiện worker/model chưa sẵn sàng; metrics không raw PII; có cảnh báo disk/queue phù hợp demo | BE-12, OPS-02 | SE2 | P3 |
| OPS-05 | Phát hành, rollback và dọn dữ liệu | Version code/model/config, hướng dẫn vận hành, retention và chính sách backup | Rollback đã thử; người vận hành biết xử lý job lỗi; backup không giữ file ngược chính sách xóa | OPS-02, OPS-03, OPS-04, BE-11 | SE2 | P4 |

## Mốc tích hợp và critical path

| Mốc | Thời gian đề xuất | Kết quả và điều kiện |
|---|---|---|
| P1 | Tuần 1 | Contract, taxonomy, split dữ liệu, môi trường và ma trận nghiệm thu; quyết định ID/giới hạn/retention/threshold không để mở đến cuối |
| P2 | Tuần 2–6 | Xây luồng đầu tiên trước cuối tuần 3 trên tập mẫu nhỏ, rồi hoàn tất chức năng cốt lõi trước cuối tuần 6; có native/scan/mixed và duyệt thủ công |
| P3 | Tuần 7–8 | Đánh giá giữ nguyên test, kiểm tra an toàn, concurrency/xóa dữ liệu, hiệu năng và usability; sửa lỗi thuộc owner module |
| P4 | Tuần 9–10 | Nghiệm thu tích hợp, deploy, rollback, báo cáo và demo tái lập |
| Dự phòng | Phần thời gian còn lại | Lỗi tích hợp, chỉnh sửa theo nghiệm thu; không tự thêm scope |

P2 chứa cả bản baseline chạy sớm và bản hoàn thiện với fine-tune. Không chờ ML-05 mới tích hợp: ML-03 chạy baseline thật trước, sau đó thay model version; giữ nguyên contract. Slice tuần 3 là mốc chứng minh kỹ thuật trên mẫu nhỏ, không phải tuyên bố đã đạt toàn bộ security/quality gates.

Critical path: CORE-02 → OCR-01..09 → ML-08 → BE-06 → BE-09 → RED-01..07 → VER-01..05 → BE-10 → FE-11 → QA-02. VER-06 khép vòng phát hiện thêm và duyệt lại; BE-11 bảo vệ deletion/publish race. Các mã trong chuỗi biểu diễn luồng tích hợp, dependency chính xác nằm trong inventory/CSV. RED có thể phát triển trước với vùng thủ công thật; BE có thể triển khai theo schema trước khi OCR/ML hoàn tất.

ML-06 là phương án hybrid; BE-06 nhận nguồn detection theo contract ML-03. Khi tích hợp hybrid, phải giữ entity schema và version; QA-07 yêu cầu báo cáo baseline/fine-tune/hybrid cuối cùng. Không cần registry/plugin cho thêm provider chưa có yêu cầu.

## Điều kiện nghiệm thu chung

- [ ] Mỗi function có assignee thật, reviewer, evidence và các phụ thuộc đã kiểm tra.
- [ ] Tất cả chức năng trong inventory hoàn thành; các gate P0 không được bỏ qua.
- [ ] Native/scan/mixed và chữ viết tay khoanh vùng thủ công chạy trọn luồng.
- [ ] Trang lỗi, mapping lỗi, vùng chưa duyệt và verification lỗi không bị che giấu thành pass.
- [ ] Kiểm tra redaction có fixture text/ảnh/OCR layer/dữ liệu ẩn; độc lập với người viết RED.
- [ ] Artifact chỉ phát hành từ snapshot hiện hành; sửa/xóa/retry không làm lộ artifact cũ hoặc tái sinh dữ liệu.
- [ ] Kết quả ML/OCR/engine/product có nguồn dữ liệu, version và giới hạn công bố rõ.
- [ ] Server demo có đăng nhập, HTTPS, phân quyền artifact, cleanup và rollback đã kiểm tra.

## Rủi ro, quyết định còn mở và rollback

- CORE-01 phải chốt mã ID cụ thể và chính sách xóa. Không cam kết nhận dạng chữ viết tay tự động.
- QA-01 và OPS-01/03 phải chốt giới hạn file/pages/concurrency, latency và ngưỡng chất lượng trên máy mục tiêu; chưa có benchmark để ước lượng cấu hình/GPU.
- BE-11 và OPS-05 phải chốt retention, xử lý backup và xóa khi job đang chạy. Chỉ dùng dữ liệu công khai/tổng hợp; không mở rộng sang dữ liệu thật bằng cấu hình ngầm.
- Chưa chọn stack, thư viện PDF/OCR hoặc schema database; tên API, file code và lệnh test sẽ được xác định trong CORE-03/OPS-01. Đây là backlog chức năng, chưa đủ để giao agent triển khai toàn bộ không cần quyết định kỹ thuật.
- Rollback: pin code/model/config, vô hiệu hóa export khi mandatory checks lỗi, rollback phiên bản release; không sửa bản gốc. Mọi migration tương lai phải backup trước theo quy tắc project.
- Không bảo đảm tìm hết PII: OCR/ML có thể bỏ sót. Kiểm tra vùng đã chọn không phải chứng nhận toàn tài liệu không còn PII.

## Kiểm tra backlog

Mã duy nhất, dependency tồn tại, không có chu trình, không phụ thuộc mốc tương lai; đủ owner/reviewer và 7 vai trò. Đây là kiểm tra cấu trúc kế hoạch, không phải kiểm thử sản phẩm. Chưa có code để chạy unit/integration/security benchmark.

Rà soát độc lập đã được tích hợp: deletion không chờ export; kiểm tra tombstone trước publish; residual candidates khép vòng revision; parser limits đưa lên P2; dependency của kiểm thử bám chức năng được kiểm tra; phân công theo 1 ML, 2 Cyber Security và 4 SE, với CS2 verification độc lập và ML1 thực hiện fine-tune. Dependency mô tả thứ tự triển khai, không tự giới hạn thao tác người dùng lúc runtime.
