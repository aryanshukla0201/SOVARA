from __future__ import annotations

from typing import Any

from app.tools.data.csv_analyzer import CSVAnalyzer


def execute_csv_analyzer(
    csv_source: str | bytes,
    user_query: str = "",
) -> dict[str, Any]:
    analyzer = CSVAnalyzer()

    return analyzer.analyze_csv(
        csv_source=csv_source,
        user_query=user_query,
    )