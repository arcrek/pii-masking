import unittest
from engine.data.normalizer import normalize_document, validate_annotation_integrity

class TestNormalizer(unittest.TestCase):
    def test_nfc_normalization(self):
        # Example of NFD (combining characters)
        # 'a' + '◌́' = 'á'
        text_nfd = "a\u0301" 
        text_nfc = "\u00e1"
        
        doc = {
            "text": text_nfd,
            "entities": []
        }
        
        normalized_doc = normalize_document(doc)
        self.assertEqual(normalized_doc["text"], text_nfc)
        
    def test_offset_validation_pass(self):
        doc = {
            "text": "Nguyễn Văn An",
            "entities": [
                {"start": 0, "end": 6, "value": "Nguyễn", "label": "NAME"}
            ]
        }
        errors = validate_annotation_integrity(doc)
        self.assertEqual(len(errors), 0)
        
    def test_offset_validation_fail(self):
        doc = {
            "text": "Nguyễn Văn An",
            "entities": [
                {"start": 0, "end": 5, "value": "Nguyễn", "label": "NAME"}
            ]
        }
        errors = validate_annotation_integrity(doc)
        self.assertGreater(len(errors), 0)
        self.assertIn("Offset mismatch", errors[0])

if __name__ == '__main__':
    unittest.main()
