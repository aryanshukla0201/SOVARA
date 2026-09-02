from __future__ import annotations

from datetime import datetime, timezone


class TraceabilityService:
    @staticmethod
    def create_trace(node_name: str, model_used: str, tools_used: list[str], success: bool, relevant_output_ids: list[str] | None = None) -> dict:
        return {
            "node_name": node_name,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "model_used": model_used,
            "tools_used": tools_used,
            "success": success,
            "relevant_output_ids": relevant_output_ids or [],
        }
