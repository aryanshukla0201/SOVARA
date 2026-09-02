from __future__ import annotations

from typing import Any


class VisionAnalyzer:
    def analyze(self, image_path: str, task_context: str) -> dict[str, Any]:
        return {
            "image_id": image_path.split("/")[-1],
            "observations": [
                {
                    "description": f"Image reviewed for {task_context}",
                    "confidence": 0.8,
                }
            ],
        }
