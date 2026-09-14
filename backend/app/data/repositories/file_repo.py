import os
import json
from pathlib import Path
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

class FileRepository:
    def __init__(self, base_path: str = "generated"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_json(self, data: Dict[str, Any], filename: str) -> str:
        path = self.base_path / filename
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved JSON: {path}")
        return str(path)

    def load_json(self, filename: str) -> Dict[str, Any]:
        path = self.base_path / filename
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_files(self) -> List[str]:
        return [str(p) for p in self.base_path.glob("*")]
