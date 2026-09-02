from __future__ import annotations

from pathlib import Path

import pandas as pd


class XlsxGenerator:
    def generate(self, data: list[dict], output_path: str | Path) -> str:
        df = pd.DataFrame(data)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(str(out), index=False)
        return str(out)
