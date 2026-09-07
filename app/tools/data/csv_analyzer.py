from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

import pandas as pd


class CSVAnalyzer:
    def analyze_csv(
        self,
        csv_source: str | bytes,
        user_query: str = "",
    ) -> dict[str, Any]:

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

        if df.empty:
            return {
                "analysis_type": "empty_dataset",
                "message": "CSV is empty.",
                "metric": None,
            }

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

        query = user_query.lower()

        metric = numeric_columns[0]

        for column in numeric_columns:
            if re.search(
                rf"\b{re.escape(str(column).lower())}\b",
                query,
            ):
                metric = column
                break

        values = (
            pd.to_numeric(df[metric], errors="coerce")
            .dropna()
        )

        if values.empty:
            return {
                "analysis_type": "no_valid_values",
                "metric": metric,
                "dataset_rows": len(df),
            }

        if any(
            word in query
            for word in ("average", "mean", "avg")
        ):
            return {
                "analysis_type": "average",
                "metric": metric,
                "average": round(float(values.mean()), 2),
                "dataset_rows": len(df),
                "valid_values": len(values),
                "inspected_columns": list(df.columns),
            }

        if any(
            word in query
            for word in ("sum", "total")
        ):
            return {
                "analysis_type": "sum",
                "metric": metric,
                "sum": round(float(values.sum()), 2),
                "dataset_rows": len(df),
                "valid_values": len(values),
                "inspected_columns": list(df.columns),
            }

        if any(
            word in query
            for word in ("minimum", "minimum value", "min")
        ):
            return {
                "analysis_type": "minimum",
                "metric": metric,
                "minimum": float(values.min()),
                "dataset_rows": len(df),
                "valid_values": len(values),
                "inspected_columns": list(df.columns),
            }

        if any(
            word in query
            for word in ("maximum", "maximum value", "max")
        ):
            return {
                "analysis_type": "maximum",
                "metric": metric,
                "maximum": float(values.max()),
                "dataset_rows": len(df),
                "valid_values": len(values),
                "inspected_columns": list(df.columns),
            }

        if len(values) < 2:
            return {
                "analysis_type": "trend_analysis",
                "metric": metric,
                "start_value": float(values.iloc[0]),
                "end_value": float(values.iloc[-1]),
                "percentage_change": 0.0,
                "units": "",
                "dataset_rows": len(df),
            }

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