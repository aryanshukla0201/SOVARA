from __future__ import annotations

from typing import Any

import pandas as pd


class ExcelAnalyzer:
    def analyze_excel(self, file_path: str, user_query: str = "",) -> dict[str, Any]:

        df = pd.read_excel(file_path)

        if df.empty:
            return {
                "analysis_type": "empty_dataset",
                "message": "Excel dataset is empty.",
                "metric": None,
            }

        numeric_columns = df.select_dtypes(include="number").columns.tolist()

        if not numeric_columns:
            return {
                "analysis_type": "non_numeric_dataset",
                "message": "No numeric columns detected.",
                "columns": list(df.columns),
                "dataset_rows": len(df),
            }

        metric = numeric_columns[0]

        values = (
            pd.to_numeric(df[metric], errors="coerce")
            .dropna()
        )

        if len(values) < 2:
            return {
                "analysis_type": "trend_analysis",
                "metric": metric,
                "start_value": (
                    float(values.iloc[0])
                    if len(values)
                    else 0.0
                ),
                "end_value": (
                    float(values.iloc[-1])
                    if len(values)
                    else 0.0
                ),
                "percentage_change": 0.0,
                "units": "",
                "dataset_rows": len(df),
                "inspected_columns": list(df.columns),
            }

        start_value = float(values.iloc[0])
        end_value = float(values.iloc[-1])

        percentage_change = (
            ((end_value - start_value) / start_value * 100.0)
            if start_value != 0
            else 0.0
        )

        return {
            "analysis_type": "trend_analysis",
            "metric": metric,
            "start_value": start_value,
            "end_value": end_value,
            "percentage_change": round(percentage_change, 2),
            "units": "",
            "dataset_rows": len(df),
            "inspected_columns": list(df.columns),
        }