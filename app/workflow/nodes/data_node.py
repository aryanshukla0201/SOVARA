from __future__ import annotations

from app.tools.data.csv_analyzer import CSVAnalyzer
from app.tools.data.excel_analyzer import ExcelAnalyzer


class DataNode:
    def __init__(
        self,
        csv_analyzer=None,
        excel_analyzer=None,
    ):
        self.csv_analyzer = csv_analyzer or CSVAnalyzer()
        self.excel_analyzer = excel_analyzer or ExcelAnalyzer()

    def run(
        self,
        source: str | bytes,
        file_type: str,
        user_query: str = "",
    ) -> dict:

        if file_type == "csv":
            return self.csv_analyzer.analyze_csv(
                source,
                user_query,
            )

        if file_type == "xlsx":
            if not isinstance(source, str):
                raise ValueError(
                    "Excel analysis requires a file path."
                )

            return self.excel_analyzer.analyze_excel(
                source,
                user_query,
            )

        raise ValueError(
            f"Unsupported data file type: {file_type}"
        )