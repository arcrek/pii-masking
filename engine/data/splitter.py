import hashlib
import json
import random
from typing import List, Dict, Any

def compute_document_fingerprint(text: str) -> str:
    # Chuẩn hóa khoảng trắng và lowercase để băm chống trùng ngữ nghĩa
    normalized = " ".join(text.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

class DatasetSplitter:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.fingerprints = {}
        for doc in data:
            fp = compute_document_fingerprint(doc["text"])
            self.fingerprints[fp] = doc

    def split(self, train_size: float, dev_size: float, test_size: float):
        """
        Splits data into train, dev, test sets using fingerprints to ensure no overlaps.
        """
        fingerprints = list(self.fingerprints.keys())
        random.shuffle(fingerprints)
        
        n = len(fingerprints)
        train_end = int(n * train_size)
        dev_end = train_end + int(n * dev_size)
        
        train_fps = fingerprints[:train_end]
        dev_fps = fingerprints[train_end:dev_end]
        test_fps = fingerprints[dev_end:]
        
        return {
            "train": [self.fingerprints[fp] for fp in train_fps],
            "dev": [self.fingerprints[fp] for fp in dev_fps],
            "test": [self.fingerprints[fp] for fp in test_fps]
        }

def save_manifest(split_data: Dict[str, List[Dict[str, Any]]], output_dir: str):
    """
    Saves the split data into jsonl files in the specified output directory.
    """
    for split_name, docs in split_data.items():
        with open(f"{output_dir}/vn_{split_name}.jsonl", "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
