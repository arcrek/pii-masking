---
title: "mvp-function-breakdown"
description: "Function backlog và phân công MVP PII PDF cho 7 thành viên, 10–11 tuần"
status: pending
priority: P1
effort: "10–11 calendar weeks; capacity unconfirmed"
tags: [pii, pdf, mvp, function-backlog]
created: 2026-11-01
---

# mvp-function-breakdown

## Overview

Backlog 75 function codes cho MVP tiếng Anh, PDF native/scan/mixed; chữ viết tay khoanh vùng thủ công. Cơ cấu 1 ML, 2 Cyber Security và 4 Software Engineer, server demo có đăng nhập, dữ liệu công khai/tổng hợp, Colab Pro huấn luyện. Chưa triển khai code.

- [Danh mục chức năng và acceptance](./function-breakdown.md)
- [CSV phân công và tracking](./function-backlog.csv)

Function codes là work packages; không phải tên hàm code. Đã hoàn tất gán tên thật cho cả 7 vai trò (ML1: Nguyễn Đăng Đạt, SE2: Nguyễn Đinh Phú Vinh, SE3: Nguyễn Tuấn Vinh, SE4: Dương Minh Đức, SE1: Đỗ Minh Tấn, CS1: Nguyễn Quang Anh, CS2: Hoàng Thị Kiều Ly). Fine-tune ML-05 do ML1 (Đăng Đạt) trực tiếp chạy Colab Pro với sự hỗ trợ thiết kế kiến trúc từ SE2 (Phú Vinh). Các phase là roadmap tích hợp, không cản phát triển song song theo contract.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Giao việc theo function code, owner, dependency và acceptance | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Start](./phase-01-start.md) | Pending |

## Success Criteria

- [ ] Chốt assignee và các quyết định CORE-01/03, QA-01.
- [ ] Hoàn thành từng function và phase với evidence, bao gồm mandatory security/export gates.
- [ ] Nghiệm thu luồng native/scan/mixed và báo cáo ML/OCR/engine/product.

<!-- slug: mvp-function-breakdown -->

## Validation

Đã tái sử dụng quyết định trong trao đổi: product MVP, English public/synthetic data, native+scan, handwriting manual, 7 người, 2,5 tháng và server riêng có đăng nhập. Không hỏi lại các quyết định này. Các lựa chọn kỹ thuật còn mở đã được đưa vào function có owner; không tự đặt ngưỡng chất lượng hoặc phạm vi ID.

Đã kiểm tra cấu trúc mã, dependency và phase. Chưa kiểm thử sản phẩm; chưa có code/stack/lệnh test. Không có task-management service phù hợp trong phiên; tracking nằm trong CSV và phase checkboxes. Chỉ mục AgentKit ngoài workspace không cập nhật được khi scaffold; file trong project là nguồn chính.

Journal skipped by preference (`journal.auto=false`).

### Whole-plan consistency sweep

75 function codes, CSV và phase checkboxes đã đối chiếu. Sau review, đồng bộ dependencies, owner và mốc ở toàn bộ artifact; không dùng cảnh báo của reviewer để kết luận runtime bug khi chưa có code. Scope/quality/server decisions còn mở có owner trong backlog. File links và DAG được kiểm tra lại sau chỉnh sửa.

### Cập nhật cơ cấu chuyên môn và gán nhân sự

Phân bổ 75 function cho 1 ML, 2 Cyber Security và 4 SE và đã chốt tên thật 7 thành viên vào CSV tracking. Fine-tune ML-05 do ML1 (Nguyễn Đăng Đạt) trực tiếp chạy Colab Pro; SE2 (Nguyễn Đinh Phú Vinh) gánh Backend & System Lead và đồng thiết kế model. SE hỗ trợ data/regex/serving, CS2 verification độc lập với RED. Đồng bộ toàn bộ inventory, CSV và các phase.
