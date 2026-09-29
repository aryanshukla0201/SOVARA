from pathlib import Path

import pytest

from app.workflow.nodes.input_processor import prepare_uploaded_files


def test_prepare_uploaded_files_rejects_missing_file(tmp_path: Path):
    missing_file = tmp_path / "missing.pdf"

    with pytest.raises(ValueError, match="File not found"):
        prepare_uploaded_files(
            user_query="analyze this file",
            files=[missing_file],
            base_dir=str(tmp_path / "uploads"),
        )
