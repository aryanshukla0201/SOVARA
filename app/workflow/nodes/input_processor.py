from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.constants import SUPPORTED_INPUT_TYPES
from app.state.workflow_state import UploadedFileRecord


def detect_input_modalities(
    user_query: str,
    files: list[str | Path] | None = None,
) -> dict[str, bool]:
    detection = {
        key: False
        for key in SUPPORTED_INPUT_TYPES
    }

    if user_query:
        detection["text"] = True

    if files:
        for file in files:
            path = Path(file)
            suffix = path.suffix.lower().lstrip(".")

            if suffix in {
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "bmp",
                "gif",
                "webp",
            }:
                detection[
                    "pdf" if suffix == "pdf" else "image"
                ] = True

            elif suffix == "csv":
                detection["csv"] = True

            elif suffix == "docx":
                detection["docx"] = True

            elif suffix in {"xlsx", "xls"}:
                detection["xlsx"] = True

    return detection


def _file_id(path: Path) -> str:
    digest = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    return f"file_{digest[:8]}"


def prepare_uploaded_files(
    user_query: str,
    files: list[str | Path],
    base_dir: str = "data/uploads",
) -> list[UploadedFileRecord]:
    prepared: list[UploadedFileRecord] = []

    for file in files:
        path = Path(file)

        suffix = (
            path.suffix
            .lower()
            .lstrip(".")
        )

        file_type = (
            "pdf"
            if suffix == "pdf"
            else "image"
            if suffix in {
                "png",
                "jpg",
                "jpeg",
                "bmp",
                "gif",
                "webp",
            }
            else suffix
        )

        file_id = _file_id(path)

        destination_path = (
            Path(base_dir)
            / f"{file_id}_{path.name}"
        )

        destination_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if path.exists():
            destination_path.write_bytes(
                path.read_bytes()
            )

        prepared.append(
            UploadedFileRecord(
                file_id=file_id,
                original_name=path.name,
                storage_path=str(
                    destination_path
                ),
                file_type=file_type,
                metadata={
                    "size": (
                        path.stat().st_size
                        if path.exists()
                        else 0
                    ),
                    "mime": suffix,
                },
            )
        )

    return prepared