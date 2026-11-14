---
title: "Phase 1: Contracts and data foundations"
status: todo
---

# Contracts and data foundations

## Phạm vi

Mốc P1; xem lịch và hợp đồng trong [Function breakdown](./function-breakdown.md).

## Công việc

- [ ] CORE-01 — Chốt chính sách PII (owner CS1, reviewer ML1).
- [ ] CORE-02 — Chốt hợp đồng tài liệu và tọa độ (owner SE3, reviewer SE4).
- [ ] CORE-03 — Chốt hợp đồng API và tác vụ (owner SE2, reviewer CS1).
- [ ] DATA-01 — Khảo sát dữ liệu và giấy phép (owner SE4, reviewer CS1).
- [ ] DATA-02 — Chuẩn hóa annotation (owner SE4, reviewer ML1).
- [ ] DATA-03 — Tách train/validation/test (owner SE4, reviewer ML1).
- [ ] QA-01 — Ma trận nghiệm thu và ngưỡng chất lượng (owner CS1, reviewer ML1).
- [x] OPS-01 — Môi trường và cấu hình phiên bản (owner SE2, reviewer CS1).

## Thực hiện và kiểm tra

1. Kiểm tra dependency của từng mã trong inventory và chọn assignee thật trong CSV.
2. Đọc acceptance của mã; thống nhất contract và giới hạn chưa chốt trước khi code phần liên quan.
3. Triển khai, kiểm tra ca thành công/lỗi và ghi evidence vào CSV.
4. Reviewer kiểm tra, đồng bộ checkbox khi đạt acceptance; phase chỉ xong khi toàn bộ mã của phase đạt.

## Rủi ro và rollback

Không ghi đè bản gốc hoặc bỏ gate export. Quyết định stack/file code chưa được chọn; owner bổ sung lệnh test thực tế trước triển khai. Rollback theo phiên bản code/model/config; không xóa fixture đánh giá để làm pass.
