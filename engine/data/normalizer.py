import unicodedata
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class NormalizedEntitySpan:
    start: int                  # Vị trí ký tự bắt đầu (0-based)
    end: int                    # Vị trí ký tự kết thúc
    label: str                  # Nhãn chuẩn
    value: str                  # Giá trị chuỗi thực tế
    is_valid_offset: bool       # text[start:end] == value

def validate_annotation_integrity(doc: Dict[str, Any]) -> List[str]:
    """
    Validates that the entities in the doc match the text content
    after NFC normalization.
    """
    text = unicodedata.normalize("NFC", doc["text"])
    errors = []
    
    for ent in doc["entities"]:
        start = ent["start"]
        end = ent["end"]
        value = ent["value"]
        
        span_text = text[start:end]
        if span_text != value:
            errors.append(f"Offset mismatch: expected '{value}', got '{span_text}'")
            
    return errors

def normalize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes text to NFC and validates entities.
    """
    doc["text"] = unicodedata.normalize("NFC", doc["text"])
    errors = validate_annotation_integrity(doc)
    
    if errors:
        raise ValueError(f"Annotation integrity check failed: {errors}")
        
    return doc
