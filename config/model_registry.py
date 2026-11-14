"""Model Registry and Version Management module for PII Detection & Redaction MVP.

Manages version-pinned NER and rule-based models, verifying checkpoint integrity
and label spaces according to OPS-01 acceptance criteria.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ModelMetadata:
    """Metadata describing a version-pinned detection model or pipeline component."""

    id: str
    version: str
    type: str
    framework: str
    language: str
    path: str
    label_space: str
    label_count: int
    description: str

    def get_full_id(self) -> str:
        """Return canonical identifier with version."""
        return f"{self.id}:{self.version}"


class ModelRegistry:
    """Registry managing model catalog, versions, and local checkpoint verification."""

    def __init__(self, registry_file: Path | str | None = None, repo_root: Path | str | None = None) -> None:
        if repo_root is None:
            self.repo_root = Path(__file__).resolve().parent.parent
        else:
            self.repo_root = Path(repo_root)

        if registry_file is None:
            self.registry_file = self.repo_root / "configs" / "models.json"
        else:
            self.registry_file = Path(registry_file)

        self.registry_version: str = "1.0.0"
        self.default_model: str = "spacy_vn_19_ner"
        self._models: Dict[str, Dict[str, ModelMetadata]] = {}
        self._load()

    def _load(self) -> None:
        """Load and parse the models manifest JSON file."""
        if not self.registry_file.is_file():
            raise FileNotFoundError(f"Model registry file not found: {self.registry_file}")

        with open(self.registry_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.registry_version = data.get("registry_version", "1.0.0")
        self.default_model = data.get("default_model", "spacy_vn_19_ner")

        for item in data.get("models", []):
            model = ModelMetadata(
                id=item["id"],
                version=item["version"],
                type=item["type"],
                framework=item["framework"],
                language=item["language"],
                path=item["path"],
                label_space=item["label_space"],
                label_count=item["label_count"],
                description=item.get("description", ""),
            )
            if model.id not in self._models:
                self._models[model.id] = {}
            self._models[model.id][model.version] = model

    def list_models(self) -> List[ModelMetadata]:
        """Return list of all registered models across all versions."""
        result: List[ModelMetadata] = []
        for v_map in self._models.values():
            result.extend(v_map.values())
        return result

    def get_model(self, model_id: str, version: Optional[str] = None) -> ModelMetadata:
        """Retrieve model metadata by ID and optional version (defaults to latest/1.0.0)."""
        if model_id not in self._models:
            raise KeyError(f"Model ID '{model_id}' is not registered.")

        versions = self._models[model_id]
        if version is None:
            # Pick latest or first available
            version = sorted(versions.keys(), reverse=True)[0]

        if version not in versions:
            raise KeyError(f"Version '{version}' not found for model '{model_id}'. Available: {list(versions.keys())}")

        return versions[version]

    def verify_checkpoints(self) -> Dict[str, bool]:
        """Verify that checkpoint paths and label spaces exist on disk."""
        status = {}
        for model in self.list_models():
            model_path = self.repo_root / model.path
            label_space_path = self.repo_root / model.label_space
            exists = model_path.exists() and label_space_path.is_file()
            status[model.get_full_id()] = exists
        return status

    def load_label_space(self, model_id: str, version: Optional[str] = None) -> List[str]:
        """Load and return label class list for a given model."""
        meta = self.get_model(model_id, version)
        label_file = self.repo_root / meta.label_space
        with open(label_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        classes = data.get("span_class_names", [])
        return [c for c in classes if c != "O"]


# Global default registry instance
_REGISTRY_INSTANCE: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    """Retrieve global cached ModelRegistry instance."""
    global _REGISTRY_INSTANCE
    if _REGISTRY_INSTANCE is None:
        _REGISTRY_INSTANCE = ModelRegistry()
    return _REGISTRY_INSTANCE


if __name__ == "__main__":
    reg = get_model_registry()
    print(f"Registry Version: {reg.registry_version}")
    print(f"Total Models Registered: {len(reg.list_models())}")
    for m in reg.list_models():
        print(f" - {m.get_full_id()} [{m.framework}] -> {m.path}")
    print(f"Checkpoints status: {reg.verify_checkpoints()}")
