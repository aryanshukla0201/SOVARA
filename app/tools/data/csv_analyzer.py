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

        # --------------------------------------------------
        # Metric selection
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Requested operations
        # --------------------------------------------------

        wants_average = bool(
            re.search(r"\b(average|mean|avg)\b", query)
        )

        wants_sum = bool(
            re.search(r"\b(sum|total)\b", query)
        )

        wants_minimum = bool(
            re.search(
                r"\b(minimum|lowest|smallest|min)\b",
                query,
            )
        )

        wants_maximum = bool(
            re.search(
                r"\b(maximum|highest|largest|max)\b",
                query,
            )
        )

        analyses: list[dict[str, Any]] = []

        # --------------------------------------------------
        # Average
        # --------------------------------------------------

        if wants_average:
            analyses.append(
                {
                    "analysis_type": "average",
                    "metric": metric,
                    "average": round(
                        float(values.mean()),
                        2,
                    ),
                    "valid_values": len(values),
                }
            )

        # --------------------------------------------------
        # Sum
        # --------------------------------------------------

        if wants_sum:
            analyses.append(
                {
                    "analysis_type": "sum",
                    "metric": metric,
                    "sum": round(
                        float(values.sum()),
                        2,
                    ),
                    "valid_values": len(values),
                }
            )

        # --------------------------------------------------
        # Minimum record
        # --------------------------------------------------

        if wants_minimum:
            minimum_index = values.idxmin()
            minimum_row = df.loc[minimum_index]

            analyses.append(
                {
                    "analysis_type": "minimum",
                    "metric": metric,
                    "minimum": float(
                        values.loc[minimum_index]
                    ),
                    "record": self._serialize_row(
                        minimum_row
                    ),
                }
            )

        # --------------------------------------------------
        # Maximum record
        # --------------------------------------------------

        if wants_maximum:
            maximum_index = values.idxmax()
            maximum_row = df.loc[maximum_index]

            analyses.append(
                {
                    "analysis_type": "maximum",
                    "metric": metric,
                    "maximum": float(
                        values.loc[maximum_index]
                    ),
                    "record": self._serialize_row(
                        maximum_row
                    ),
                }
            )

        # --------------------------------------------------
        # Requested deterministic analyses found
        # --------------------------------------------------

        if analyses:
            if len(analyses) == 1:
                result = analyses[0]

                result.update(
                    {
                        "dataset_rows": len(df),
                        "inspected_columns": list(df.columns),
                    }
                )

                return result

            return {
                "analysis_type": "compound",
                "metric": metric,
                "analyses": analyses,
                "dataset_rows": len(df),
                "valid_values": len(values),
                "inspected_columns": list(df.columns),
            }

        # --------------------------------------------------
        # Default trend analysis
        # --------------------------------------------------

        if len(values) < 2:
            return {
                "analysis_type": "trend_analysis",
                "metric": metric,
                "start_value": float(values.iloc[0]),
                "end_value": float(values.iloc[-1]),
                "percentage_change": 0.0,
                "units": "",
                "dataset_rows": len(df),
                "inspected_columns": list(df.columns),
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

    @staticmethod
    def _serialize_row(
        row: pd.Series,
    ) -> dict[str, Any]:

        result: dict[str, Any] = {}

        for key, value in row.items():

            if pd.isna(value):
                result[str(key)] = None

            elif hasattr(value, "item"):
                result[str(key)] = value.item()

            else:
                result[str(key)] = value

        return result