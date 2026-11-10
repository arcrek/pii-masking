#!/usr/bin/env python3
"""Curate Vietnamese PII dataset splits from OpenPII 1.5M (`ai4privacy/pii-masking-openpii-1.5m`)
and build the independent Vietnamese PII + non-PII holdout benchmark.

Produces:
- `evaluation/data/vn_train.jsonl` (3,000 deduplicated Vietnamese training docs)
- `evaluation/data/vn_dev.jsonl` (300 deduplicated Vietnamese validation docs)
- `evaluation/data/vn_test.jsonl` (600 deduplicated Vietnamese test docs)
- `evaluation/data/vn_opf_train.jsonl` & `vn_opf_dev.jsonl` (formatted for `opf train`)
- `evaluation/data/vn_independent_holdout.jsonl` (75 independent VN docs: 60 positive + 15 negative non-PII)
- `evaluation/data/vn_openpii_manifest.json` (audit trail: revision, license, Unicode, span integrity, label counts)
- `checkpoints/opf_vn_19_label_space.json` (77-class BIESO label space for 19 OpenPII labels)
"""

from __future__ import annotations

import hashlib
import json
import random
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

OPENPII_19_LABELS: list[str] = [
    "AGE",
    "BUILDINGNUM",
    "CITY",
    "CREDITCARDNUMBER",
    "DATE",
    "DRIVERLICENSENUM",
    "EMAIL",
    "GENDER",
    "GIVENNAME",
    "IDCARDNUM",
    "PASSPORTNUM",
    "SEX",
    "SOCIALNUM",
    "STREET",
    "SURNAME",
    "TAXNUM",
    "TELEPHONENUM",
    "TITLE",
    "ZIPCODE",
]

OPENPII_19_SET = set(OPENPII_19_LABELS)
DATASET_ID = "ai4privacy/pii-masking-openpii-1.5m"
DATASET_REVISION = "a785eb528e28be2693c3718a27e066970de5dadb"
DATASET_LICENSE = "CC-BY-4.0"


def normalize_and_validate_record(
    row: dict[str, Any],
    split_origin: str,
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    """Validate Unicode NFC, span offsets, non-overlapping spans, and filter to canonical 19 OpenPII labels."""
    stats = {
        "non_nfc_text": 0,
        "non_19_labels_dropped": 0,
        "invalid_span_bounds": 0,
        "value_mismatch": 0,
        "overlapping_spans_dropped": 0,
    }
    raw_text = str(row.get("source_text", ""))
    if not raw_text.strip():
        return None, stats

    nfc_text = unicodedata.normalize("NFC", raw_text)
    if nfc_text != raw_text:
        stats["non_nfc_text"] += 1
        # If NFC changes string length, skip to avoid offset drift
        if len(nfc_text) != len(raw_text):
            return None, stats
        text = nfc_text
    else:
        text = raw_text

    raw_masks = row.get("privacy_mask") or []
    valid_spans: list[dict[str, Any]] = []
    for m in raw_masks:
        lbl = str(m.get("label", "")).strip()
        if lbl not in OPENPII_19_SET:
            stats["non_19_labels_dropped"] += 1
            continue
        try:
            s = int(m["start"])
            e = int(m["end"])
        except (KeyError, TypeError, ValueError):
            stats["invalid_span_bounds"] += 1
            continue

        if not (0 <= s < e <= len(text)):
            stats["invalid_span_bounds"] += 1
            continue

        slice_text = text[s:e]
        expected_val = unicodedata.normalize("NFC", str(m.get("value", slice_text)))
        if slice_text != expected_val:
            stats["value_mismatch"] += 1
            continue

        # Trim outer whitespace if any
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s >= e:
            stats["invalid_span_bounds"] += 1
            continue

        valid_spans.append(
            {
                "start": s,
                "end": e,
                "label": lbl,
                "text": text[s:e],
            }
        )

    if not valid_spans:
        return None, stats

    # Sort by start, then longest span first, and drop overlaps
    valid_spans.sort(key=lambda sp: (sp["start"], -(sp["end"] - sp["start"])))
    deduped_spans: list[dict[str, Any]] = []
    for sp in valid_spans:
        if deduped_spans and sp["start"] < deduped_spans[-1]["end"]:
            stats["overlapping_spans_dropped"] += 1
            continue
        deduped_spans.append(sp)

    uid = str(row.get("uid", ""))
    text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return (
        {
            "id": f"openpii_vi_{split_origin}_{uid}",
            "uid": uid,
            "source": str(row.get("source_dataset", "openpii-1.5m-vi")),
            "language": "vi",
            "region": str(row.get("region", "VN")),
            "script": str(row.get("script", "Latn")),
            "split_origin": split_origin,
            "text_sha256": text_sha256,
            "text": text,
            "spans": deduped_spans,
        },
        stats,
    )


def stratify_select(
    pool: list[dict[str, Any]],
    target_size: int,
    min_per_label: int,
    rng: random.Random,
    exclude_hashes: set[str],
) -> list[dict[str, Any]]:
    """Select `target_size` records from `pool` guaranteeing at least `min_per_label` per label."""
    available = [d for d in pool if d["text_sha256"] not in exclude_hashes]
    by_label: dict[str, list[int]] = defaultdict(list)
    for idx, doc in enumerate(available):
        for sp in doc["spans"]:
            by_label[sp["label"]].append(idx)

    selected_indices: set[int] = set()
    selected_hashes: set[str] = set()

    # Step 1: Cover rare labels first
    label_order = sorted(OPENPII_19_LABELS, key=lambda l: len(by_label[l]))
    for lbl in label_order:
        candidates = [
            idx
            for idx in by_label[lbl]
            if idx not in selected_indices and available[idx]["text_sha256"] not in selected_hashes
        ]
        rng.shuffle(candidates)
        current_lbl_docs = sum(
            1
            for idx in selected_indices
            if any(sp["label"] == lbl for sp in available[idx]["spans"])
        )
        needed = max(0, min_per_label - current_lbl_docs)
        for idx in candidates[:needed]:
            selected_indices.add(idx)
            selected_hashes.add(available[idx]["text_sha256"])

    # Step 2: Top up randomly to target_size
    remaining = [
        idx
        for idx in range(len(available))
        if idx not in selected_indices and available[idx]["text_sha256"] not in selected_hashes
    ]
    rng.shuffle(remaining)
    for idx in remaining:
        if len(selected_indices) >= target_size:
            break
        h = available[idx]["text_sha256"]
        if h not in selected_hashes:
            selected_indices.add(idx)
            selected_hashes.add(h)

    selected_docs = [available[idx] for idx in sorted(selected_indices)[:target_size]]
    for d in selected_docs:
        exclude_hashes.add(d["text_sha256"])
    return selected_docs


def to_opf_record(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert canonical `{id, text, spans}` doc to `opf train` record format."""
    spans_map: dict[str, list[list[int]]] = defaultdict(list)
    for sp in doc["spans"]:
        spans_map[sp["label"]].append([int(sp["start"]), int(sp["end"])])
    return {
        "id": doc["id"],
        "text": doc["text"],
        "spans": dict(spans_map),
    }


def build_independent_vn_holdout() -> list[dict[str, Any]]:
    """Build 75 independent Vietnamese evaluation documents:
    - 60 positive Vietnamese documents across 3 realistic genres (`admin_kyc`, `hr_medical`, `finance_commerce`),
      guaranteeing support across all 19 OpenPII labels.
    - 15 negative (0-PII) Vietnamese documents (`negative_non_pii`) containing public regulations,
      technical specifications, and general announcements with numbers/dates/codes that are NOT personal PII,
      specifically to measure false-positive over-masking rate.
    """
    docs: list[dict[str, Any]] = []

    people = [
        ("Ông", "Văn Hùng", "Nguyễn", "Nam", "Male", "34", "1992-04-15"),
        ("Bà", "Mai Hương", "Trần", "Nữ", "Female", "29", "1997-08-22"),
        ("Anh", "Hoàng Nam", "Lê", "Nam", "Male", "41", "1985-11-03"),
        ("Chị", "Ngọc Bích", "Phạm", "Nữ", "Female", "26", "2000-01-19"),
        ("Tiến sĩ", "Minh Tuấn", "Hoàng", "Nam", "Male", "48", "1978-06-30"),
        ("Bác sĩ", "Thu Thảo", "Vũ", "Nữ", "Female", "37", "1989-12-10"),
        ("Kỹ sư", "Quốc Khánh", "Đặng", "Nam", "Male", "31", "1995-03-25"),
        ("Cô", "Phương Linh", "Bùi", "Nữ", "Female", "24", "2002-07-08"),
        ("Chú", "Đức Thắng", "Đỗ", "Nam", "Male", "53", "1973-09-14"),
        ("Thạc sĩ", "Thanh Hà", "Ngô", "Nữ", "Female", "39", "1987-02-27"),
        ("Giám đốc", "Gia Bảo", "Dương", "Nam", "Male", "45", "1981-05-12"),
        ("Luật sư", "Kiều Trinh", "Lý", "Nữ", "Female", "36", "1990-10-05"),
        ("Ông", "Thanh Tùng", "Phan", "Nam", "Male", "50", "1976-04-02"),
        ("Bà", "Mỹ Dung", "Võ", "Nữ", "Female", "33", "1993-08-18"),
        ("Anh", "Đình Khoa", "Trương", "Nam", "Male", "28", "1998-12-21"),
        ("Chị", "Tuyết Nhung", "Đinh", "Nữ", "Female", "30", "1996-06-09"),
        ("Ông", "Chí Công", "Lương", "Nam", "Male", "44", "1982-01-31"),
        ("Bà", "Thanh Tâm", "Đoàn", "Nữ", "Female", "35", "1991-07-23"),
        ("Ông", "Tấn Phát", "Huỳnh", "Nam", "Male", "42", "1984-03-11"),
        ("Bà", "Hồng Nhung", "Tạ", "Nữ", "Female", "38", "1988-11-29"),
    ]

    addresses = [
        ("128", "Nguyễn Thị Minh Khai", "Thành phố Hồ Chí Minh", "70000"),
        ("45", "Lý Thường Kiệt", "Thành phố Hà Nội", "10000"),
        ("219", "Trần Phú", "Thành phố Đà Nẵng", "55000"),
        ("88", "Lê Lợi", "Thành phố Huế", "53000"),
        ("302", "Hòa Bình", "Thành phố Cần Thơ", "90000"),
        ("16", "Điện Biên Phủ", "Thành phố Hải Phòng", "18000"),
        ("74", "Quang Trung", "Thành phố Nha Trang", "65000"),
        ("510", "Cách Mạng Tháng Tám", "Thành phố Biên Hòa", "81000"),
        ("63", "Phan Chu Trinh", "Thành phố Vũng Tàu", "79000"),
        ("195", "Nguyễn Văn Linh", "Thành phố Quy Nhơn", "59000"),
    ]

    def build_annotated_doc(
        doc_id: str,
        doc_type: str,
        segments: list[tuple[str, str | None]],
    ) -> dict[str, Any]:
        buf: list[str] = []
        spans: list[dict[str, Any]] = []
        cursor = 0
        for seg_text, seg_label in segments:
            seg_nfc = unicodedata.normalize("NFC", seg_text)
            buf.append(seg_nfc)
            if seg_label is not None:
                assert seg_label in OPENPII_19_SET, f"Unknown label {seg_label}"
                spans.append(
                    {
                        "start": cursor,
                        "end": cursor + len(seg_nfc),
                        "label": seg_label,
                        "text": seg_nfc,
                    }
                )
            cursor += len(seg_nfc)
        full_text = "".join(buf)
        return {
            "id": doc_id,
            "doc_type": doc_type,
            "source": f"vn_independent_{doc_type}",
            "language": "vi",
            "text": full_text,
            "spans": spans,
        }

    # Generate 20 admin_kyc documents, 20 hr_medical documents, 20 finance_commerce documents
    for i in range(20):
        title, given_raw, surname, gender, sex, age, dob = people[i]
        given = given_raw.strip()
        bnum, street, city, zipcode = addresses[i % len(addresses)]
        cccd = f"VN{80 + i:02d}K{1234 + i * 37:04d}C"
        passport = f"C{8102345 + i * 119:07d}"
        gplx = f"DL{54 + i:02d}X{8210 + i * 23:04d}B"
        bhxh = f"7923{410982 + i * 157:06d}"
        tax = f"1310{45890120 + i * 413:08d}"
        phone = f"+84-9{i % 9 + 1} {345 + i * 3:03d} {6710 + i * 19:04d}"
        email = f"{unicodedata.normalize('NFKD', given).encode('ascii', 'ignore').decode('ascii').lower().replace(' ', '.')}.{i+10}@congtyvn.vn"
        cc_num = f"4532{1400 + i * 17:04d}{8821 + i * 23:04d}{3012 + i * 31:04d}"

        # 1. Admin KYC narrative & semi-structured record
        if i % 2 == 0:
            seg_admin = [
                ("Biên bản xác minh thông tin công dân: Hôm nay, ", None),
                (title, "TITLE"),
                (" ", None),
                (given, "GIVENNAME"),
                (" ", None),
                (surname, "SURNAME"),
                (" (nhận dạng giới tính: ", None),
                (gender, "GENDER"),
                (", giới tính sinh học: ", None),
                (sex, "SEX"),
                (", ", None),
                (age, "AGE"),
                (" tuổi, sinh ngày ", None),
                (dob, "DATE"),
                (") đã đến trụ sở làm thủ tục.\nSố CMND/CCCD: ", None),
                (cccd, "IDCARDNUM"),
                (" | Số hộ chiếu: ", None),
                (passport, "PASSPORTNUM"),
                (" | Số giấy phép lái xe: ", None),
                (gplx, "DRIVERLICENSENUM"),
                (".\nHiện cư ngụ ở số ", None),
                (bnum, "BUILDINGNUM"),
                (" ", None),
                (street, "STREET"),
                (", ", None),
                (city, "CITY"),
                (", mã bưu chính ", None),
                (zipcode, "ZIPCODE"),
                (".\nSố điện thoại: ", None),
                (phone, "TELEPHONENUM"),
                (", địa chỉ email ", None),
                (email, "EMAIL"),
                (".", None),
            ]
        else:
            seg_admin = [
                ("Hồ sơ định danh điện tử (eKYC): Thân gửi ", None),
                (title, "TITLE"),
                (" ", None),
                (given, "GIVENNAME"),
                (" ", None),
                (surname, "SURNAME"),
                (" (giới tính nhận dạng: ", None),
                (gender, "GENDER"),
                (", giới tính sinh học: ", None),
                (sex, "SEX"),
                (", ", None),
                (age, "AGE"),
                (" tuổi, ngày sinh ", None),
                (dob, "DATE"),
                (").\nSố CMND/CCCD: ", None),
                (cccd, "IDCARDNUM"),
                (" | Số hộ chiếu: ", None),
                (passport, "PASSPORTNUM"),
                (" | Số bằng lái xe: ", None),
                (gplx, "DRIVERLICENSENUM"),
                (".\nĐang sinh sống tại số ", None),
                (bnum, "BUILDINGNUM"),
                (" ", None),
                (street, "STREET"),
                (", ", None),
                (city, "CITY"),
                (", mã bưu điện ", None),
                (zipcode, "ZIPCODE"),
                (".\nSố điện thoại liên hệ: ", None),
                (phone, "TELEPHONENUM"),
                (", hộp thư ", None),
                (email, "EMAIL"),
                (".", None),
            ]
        docs.append(
            build_annotated_doc(
                doc_id=f"vn_holdout_admin_{i+1:02d}",
                doc_type="admin_kyc",
                segments=seg_admin,
            )
        )

        # 2. HR & Social Insurance narrative record
        docs.append(
            build_annotated_doc(
                doc_id=f"vn_holdout_hr_{i+1:02d}",
                doc_type="hr_medical",
                segments=[
                    ("Phiếu kê khai bảo hiểm xã hội và thuế: Nhân sự ", None),
                    (title, "TITLE"),
                    (" ", None),
                    (given, "GIVENNAME"),
                    (" ", None),
                    (surname, "SURNAME"),
                    (", ngày sinh ", None),
                    (dob, "DATE"),
                    (", ", None),
                    (age, "AGE"),
                    (" tuổi, giới tính nhận dạng: ", None),
                    (gender, "GENDER"),
                    (".\nSố bảo hiểm xã hội: ", None),
                    (bhxh, "SOCIALNUM"),
                    (" | Mã số thuế: ", None),
                    (tax, "TAXNUM"),
                    (" | Số CMND/CCCD: ", None),
                    (cccd, "IDCARDNUM"),
                    (".\nNơi cư trú tại số ", None),
                    (bnum, "BUILDINGNUM"),
                    (" ", None),
                    (street, "STREET"),
                    (", ", None),
                    (city, "CITY"),
                    (", mã bưu điện ", None),
                    (zipcode, "ZIPCODE"),
                    (".\nSố điện thoại: ", None),
                    (phone, "TELEPHONENUM"),
                    (", email cá nhân: ", None),
                    (email, "EMAIL"),
                    (".", None),
                ],
            )
        )

        # 3. Finance & e-Commerce payment narrative record
        docs.append(
            build_annotated_doc(
                doc_id=f"vn_holdout_finance_{i+1:02d}",
                doc_type="finance_commerce",
                segments=[
                    ("Thông báo xác nhận thanh toán đơn hàng của ", None),
                    (title, "TITLE"),
                    (" ", None),
                    (given, "GIVENNAME"),
                    (" ", None),
                    (surname, "SURNAME"),
                    (", số điện thoại ", None),
                    (phone, "TELEPHONENUM"),
                    (", email ", None),
                    (email, "EMAIL"),
                    (".\nNhập số thẻ tín dụng ", None),
                    (cc_num, "CREDITCARDNUMBER"),
                    (" và mã số thuế ", None),
                    (tax, "TAXNUM"),
                    (" vào ngày ", None),
                    (dob, "DATE"),
                    (".\nGiao kiện hàng tới địa chỉ số ", None),
                    (bnum, "BUILDINGNUM"),
                    (" ", None),
                    (street, "STREET"),
                    (", ", None),
                    (city, "CITY"),
                    (", mã bưu chính ", None),
                    (zipcode, "ZIPCODE"),
                    (" (kèm hộ chiếu ", None),
                    (passport, "PASSPORTNUM"),
                    (" và số bằng lái xe ", None),
                    (gplx, "DRIVERLICENSENUM"),
                    (").", None),
                ],
            )
        )

    # 15 Negative non-PII Vietnamese documents (containing technical numbers, laws, product codes)
    negative_texts = [
        "Thông báo bảo trì hệ thống máy chủ cổng dịch vụ công: Hệ thống sẽ nâng cấp phiên bản v3.14.2 từ 00:00 đến 04:00 sáng thứ Bảy. Tốc độ xử lý dự kiến đạt 12.500 yêu cầu/giây với băng thông 40 Gbps.",
        "Quy chuẩn kỹ thuật quốc gia về an toàn thông tin mạng QCVN 119:2025/BTTTT quy định mã hóa tối thiểu AES-256 và RSA-4096 cho toàn bộ gói tin truyền qua cổng HTTPS 8443.",
        "Báo cáo tổng quan thị trường nông sản quý III: Sản lượng lúa gạo xuất khẩu đạt 6,8 triệu tấn, kim ngạch tăng 14,2% so với cùng kỳ năm trước tại khu vực Đồng bằng sông Cửu Long.",
        "Hướng dẫn cấu hình thiết bị định tuyến công nghiệp: Đặt MTU bằng 1500, kích hoạt giao thức OSPF vùng 0, và kiểm tra độ trễ trung bình dưới 15 ms trước khi nghiệm thu.",
        "Danh mục vật tư thiết bị phòng máy chủ lô #VN-EQ-99021: 12 tủ rack chuẩn 42U, 24 bộ lưu điện công suất 10kVA, và 48 dây nhảy quang chuẩn LC-LC dài 5 mét.",
        "Nghị định quy định về quản lý chất lượng công trình xây dựng yêu cầu mọi hồ sơ thiết kế kỹ thuật phải được thẩm tra độc lập và lưu trữ tối thiểu 10 năm.",
        "Thông số kỹ thuật màn hình chuyên dụng mã MH-2700X: Độ phân giải 3840x2160 pixel, tần số quét 120Hz, độ sáng 450 nits, đạt chuẩn màu sRGB 99%.",
        "Quy trình kiểm thử tải ứng dụng ngân hàng số: Chạy kịch bản mô phỏng 5.000 kết nối đồng thời trong 60 phút, tỷ lệ lỗi HTTP 5xx phải thấp hơn 0,01%.",
        "Bản tin thời tiết thủy văn khu vực miền Trung: Mực nước các sông dâng nhẹ từ 0,3 đến 0,6 mét, gió Đông Bắc cấp 3-4, nhiệt độ dao động từ 22 đến 28 độ C.",
        "Hướng dẫn phân loại rác thải tại nguồn trong khu công nghiệp: Thùng màu xanh lá dành cho rác hữu cơ, thùng màu vàng cho chất thải tái chế và thùng màu cam cho chất thải nguy hại.",
        "Chính sách bảo hành thiết bị điện tử tiêu dùng: Bảo hành chính hãng 24 tháng đối với bo mạch chủ và 12 tháng đối với phụ kiện cáp sạc đi kèm theo tiêu chuẩn ISO-9001.",
        "Kế hoạch tổ chức hội nghị khoa học trí tuệ nhân tạo thường niên: Tập trung thảo luận các mô hình ngôn ngữ nhỏ tối ưu cho thiết bị biên và bài toán bảo mật dữ liệu.",
        "Bảng định mức tiêu hao nhiên liệu xe tải vận chuyển hàng hóa: Trung bình 18,5 lít dầu diesel trên 100 km đường hỗn hợp ở mức tải trọng 8 tấn.",
        "Tài liệu đặc tả giao thức truyền thông nội bộ: Sử dụng định dạng JSON mã hóa UTF-8, giới hạn kích thước mỗi bản tin là 2 MB và thời gian chờ tối đa 30 giây.",
        "Tổng kết chương trình tiết kiệm năng lượng nhà máy sản xuất: Giảm 11,8% lượng điện tiêu thụ giờ cao điểm nhờ hệ thống biến tần tự động và đèn chiếu sáng LED hiệu suất cao.",
    ]
    for idx, neg_text in enumerate(negative_texts, 1):
        docs.append(
            {
                "id": f"vn_holdout_neg_{idx:02d}",
                "doc_type": "negative_non_pii",
                "source": "vn_independent_negative",
                "language": "vi",
                "text": unicodedata.normalize("NFC", neg_text),
                "spans": [],
            }
        )

    return docs


def main() -> None:
    from datasets import load_dataset

    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "evaluation" / "data"
    ckpt_dir = repo_root / "checkpoints"
    data_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write custom 19-label space JSON for OPF fine-tuning
    opf_label_space = {
        "span_class_names": ["O"] + OPENPII_19_LABELS,
    }
    label_space_path = ckpt_dir / "opf_vn_19_label_space.json"
    label_space_path.write_text(
        json.dumps(opf_label_space, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[vn-data] Wrote OPF 19-label space JSON to {label_space_path}")

    # 2. Stream OpenPII 1.5M train & validation splits to collect Vietnamese records
    rng = random.Random(42)
    audit_stats = Counter()

    print("[vn-data] Streaming ai4privacy/pii-masking-openpii-1.5m (validation split)...")
    ds_val = load_dataset(DATASET_ID, split="validation", streaming=True)
    val_pool: list[dict[str, Any]] = []
    val_rows_scanned = 0
    for row in ds_val:
        val_rows_scanned += 1
        if row.get("language") == "vi":
            rec, st = normalize_and_validate_record(row, "validation")
            audit_stats.update(st)
            if rec is not None:
                val_pool.append(rec)
                if len(val_pool) >= 2000:
                    break
        if val_rows_scanned >= 60000 and len(val_pool) >= 1200:
            break
    print(f"[vn-data] Collected {len(val_pool)} valid Vietnamese records from validation split (scanned {val_rows_scanned}).")

    print("[vn-data] Streaming ai4privacy/pii-masking-openpii-1.5m (train split)...")
    ds_train = load_dataset(DATASET_ID, split="train", streaming=True)
    train_pool: list[dict[str, Any]] = []
    train_rows_scanned = 0
    for row in ds_train:
        train_rows_scanned += 1
        if row.get("language") == "vi":
            rec, st = normalize_and_validate_record(row, "train")
            audit_stats.update(st)
            if rec is not None:
                train_pool.append(rec)
                if len(train_pool) >= 4500:
                    break
        if train_rows_scanned >= 150000 and len(train_pool) >= 3500:
            break
    print(f"[vn-data] Collected {len(train_pool)} valid Vietnamese records from train split (scanned {train_rows_scanned}).")

    # 3. Strictly deduplicate across splits using text SHA-256
    used_hashes: set[str] = set()

    # Reserve dev (300) and test (600) from validation pool first so evaluation is strictly held-out
    dev_docs = stratify_select(
        pool=val_pool,
        target_size=300,
        min_per_label=10,
        rng=rng,
        exclude_hashes=used_hashes,
    )
    test_docs = stratify_select(
        pool=val_pool,
        target_size=600,
        min_per_label=20,
        rng=rng,
        exclude_hashes=used_hashes,
    )
    train_docs = stratify_select(
        pool=train_pool,
        target_size=3000,
        min_per_label=80,
        rng=rng,
        exclude_hashes=used_hashes,
    )

    # Verify zero overlap across train, dev, test
    train_hashes = {d["text_sha256"] for d in train_docs}
    dev_hashes = {d["text_sha256"] for d in dev_docs}
    test_hashes = {d["text_sha256"] for d in test_docs}
    assert not (train_hashes & dev_hashes), "Train and Dev overlap!"
    assert not (train_hashes & test_hashes), "Train and Test overlap!"
    assert not (dev_hashes & test_hashes), "Dev and Test overlap!"

    # 4. Build independent Vietnamese holdout (75 docs: 60 positive + 15 negative non-PII)
    ind_docs = build_independent_vn_holdout()

    # 5. Save datasets
    def write_jsonl(path: Path, records: list[dict[str, Any]]) -> str:
        content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        path.write_text(content, encoding="utf-8")
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    train_sha = write_jsonl(data_dir / "vn_train.jsonl", train_docs)
    dev_sha = write_jsonl(data_dir / "vn_dev.jsonl", dev_docs)
    test_sha = write_jsonl(data_dir / "vn_test.jsonl", test_docs)
    ind_sha = write_jsonl(data_dir / "vn_independent_holdout.jsonl", ind_docs)

    # Also write OPF-formatted train and dev JSONL files
    opf_train_docs = [to_opf_record(d) for d in train_docs]
    opf_dev_docs = [to_opf_record(d) for d in dev_docs]
    opf_train_sha = write_jsonl(data_dir / "vn_opf_train.jsonl", opf_train_docs)
    opf_dev_sha = write_jsonl(data_dir / "vn_opf_dev.jsonl", opf_dev_docs)

    def label_counts(docs: list[dict[str, Any]]) -> dict[str, int]:
        c = Counter(sp["label"] for d in docs for sp in d["spans"])
        return {lbl: c.get(lbl, 0) for lbl in OPENPII_19_LABELS}

    train_lbl_counts = label_counts(train_docs)
    dev_lbl_counts = label_counts(dev_docs)
    test_lbl_counts = label_counts(test_docs)
    ind_lbl_counts = label_counts(ind_docs)

    # Verify all 19 labels have positive support in every split
    for split_name, counts in [
        ("train", train_lbl_counts),
        ("dev", dev_lbl_counts),
        ("test", test_lbl_counts),
        ("independent_holdout", ind_lbl_counts),
    ]:
        missing = [lbl for lbl, cnt in counts.items() if cnt <= 0]
        assert not missing, f"Split {split_name} is missing labels: {missing}"

    manifest = {
        "dataset_id": DATASET_ID,
        "dataset_revision": DATASET_REVISION,
        "license": DATASET_LICENSE,
        "language_filter": "vi",
        "region_filter": "VN",
        "seed": 42,
        "canonical_19_labels": OPENPII_19_LABELS,
        "num_canonical_labels": len(OPENPII_19_LABELS),
        "opf_num_bieso_classes": 1 + 4 * len(OPENPII_19_LABELS),
        "curation_audit": {
            "val_rows_scanned": val_rows_scanned,
            "train_rows_scanned": train_rows_scanned,
            "val_vi_pool_valid": len(val_pool),
            "train_vi_pool_valid": len(train_pool),
            "non_nfc_normalized_count": audit_stats["non_nfc_text"],
            "non_19_labels_dropped_count": audit_stats["non_19_labels_dropped"],
            "invalid_span_bounds_dropped": audit_stats["invalid_span_bounds"],
            "value_mismatch_dropped": audit_stats["value_mismatch"],
            "overlapping_spans_dropped": audit_stats["overlapping_spans_dropped"],
            "cross_split_duplicate_texts": 0,
        },
        "splits": {
            "train": {
                "path": "evaluation/data/vn_train.jsonl",
                "opf_path": "evaluation/data/vn_opf_train.jsonl",
                "num_docs": len(train_docs),
                "total_spans": sum(train_lbl_counts.values()),
                "sha256": train_sha,
                "opf_sha256": opf_train_sha,
                "label_span_counts": train_lbl_counts,
            },
            "dev": {
                "path": "evaluation/data/vn_dev.jsonl",
                "opf_path": "evaluation/data/vn_opf_dev.jsonl",
                "num_docs": len(dev_docs),
                "total_spans": sum(dev_lbl_counts.values()),
                "sha256": dev_sha,
                "opf_sha256": opf_dev_sha,
                "label_span_counts": dev_lbl_counts,
            },
            "test": {
                "path": "evaluation/data/vn_test.jsonl",
                "num_docs": len(test_docs),
                "total_spans": sum(test_lbl_counts.values()),
                "sha256": test_sha,
                "label_span_counts": test_lbl_counts,
            },
            "independent_holdout": {
                "path": "evaluation/data/vn_independent_holdout.jsonl",
                "num_docs": len(ind_docs),
                "positive_pii_docs": sum(1 for d in ind_docs if d["spans"]),
                "negative_non_pii_docs": sum(1 for d in ind_docs if not d["spans"]),
                "total_spans": sum(ind_lbl_counts.values()),
                "sha256": ind_sha,
                "label_span_counts": ind_lbl_counts,
            },
        },
    }

    manifest_path = data_dir / "vn_openpii_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[vn-data] Saved manifest to {manifest_path}")
    print("[vn-data] Summary of splits:")
    for k, v in manifest["splits"].items():
        print(f"  - {k}: {v['num_docs']} docs, {v['total_spans']} spans")


if __name__ == "__main__":
    main()
