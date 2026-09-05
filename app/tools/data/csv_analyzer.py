from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd


class CSVAnalyzer:
    def analyze_csv(
        self,
        csv_source: str | bytes,
        user_query: str = "",
    ) -> dict[str, Any]:

        # -------------------------------------------------
        # LOAD CSV SOURCE
        # -------------------------------------------------
        if isinstance(csv_source, bytes):
            data = csv_source.decode("utf-8")
            df = pd.read_csv(io.StringIO(data))

        elif isinstance(csv_source, str):

            source_path = Path(csv_source)

            if source_path.exists() and source_path.is_file():
                df = pd.read_csv(source_path)
            else:
                df = pd.read_csv(io.StringIO(csv_source))

        else:
            raise TypeError(
                "CSV source must be a file path, string, or bytes."
            )

        # -------------------------------------------------
        # EMPTY DATASET
        # -------------------------------------------------
        if df.empty:
            return {
                "analysis_type": "empty_dataset",
                "message": "CSV is empty.",
                "metric": None,
            }

        # -------------------------------------------------
        # FIND NUMERIC COLUMNS
        # -------------------------------------------------
        numeric_columns = (
            df.select_dtypes(include="number")
            .columns
            .tolist()
        )

        if not numeric_columns:
            return {
                "analysis_type": "non_numeric_dataset",
                "message": "No numeric columns detected.",
                "columns": list(df.columns),
            }

        # -------------------------------------------------
        # SELECT METRIC
        # -------------------------------------------------
        metric = numeric_columns[0]

        values = (
            pd.to_numeric(df[metric], errors="coerce")
            .dropna()
        )

        # -------------------------------------------------
        # INSUFFICIENT VALUES
        # -------------------------------------------------
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
            }

        # -------------------------------------------------
        # TREND CALCULATION
        # -------------------------------------------------
        start_value = float(values.iloc[0])
        end_value = float(values.iloc[-1])

        percentage_change = (
            ((end_value - start_value) / start_value) * 100.0
            if start_value != 0
            else 0.0
        )

        return {
            "analysis_type": "trend_analysis",
            "metric": metric,
            "start_value": start_value,
            "end_value": end_value,
            "percentage_change": round(
                percentage_change,
                2,
            ),
            "units": "",
            "dataset_rows": len(df),
            "inspected_columns": list(df.columns),
        }