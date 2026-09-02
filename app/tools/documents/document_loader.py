from __future__ import annotations

from pathlib import Path
from typing import Any


class DocumentLoader:
    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        file_path = Path(path)
        return {"path": str(file_path), "filename": file_path.name, "suffix": file_path.suffix.lower(), "size": file_path.stat().st_size if file_path.exists() else 0}
