from dataclasses import dataclass
from typing import List

@dataclass
class DatasetSourceRecord:
    dataset_id: str             # Ví dụ: "openpii-1.5m-vi"
    source_url: str             # "https://huggingface.co/datasets/ai4privacy/..."
    revision: str               # Git commit hash của dataset nguồn
    license_type: str           # "CC-BY-4.0", "MIT", "Apache-2.0"
    is_synthetic: bool          # True nếu là dữ liệu sinh tổng hợp
    has_real_pii: bool          # BẮT BUỘC = False
    supported_languages: List[str] # ["vi", "en"]
    provenance_notes: str       # Ghi chú phương pháp sinh và thu thập

    def validate(self):
        if self.has_real_pii:
            raise ValueError(f"Dataset {self.dataset_id} contains real PII and cannot be used.")
        
        valid_licenses = ["CC-BY-4.0", "MIT", "Apache-2.0"]
        if self.license_type not in valid_licenses:
            raise ValueError(f"Dataset {self.dataset_id} uses an unsupported license: {self.license_type}")

class LicenseRegistry:
    def __init__(self):
        self.records: List[DatasetSourceRecord] = []

    def register_dataset(self, record: DatasetSourceRecord):
        record.validate()
        self.records.append(record)
        print(f"Registered dataset {record.dataset_id} with license {record.license_type}")
