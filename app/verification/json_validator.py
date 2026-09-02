from __future__ import annotations

import json
from typing import Any


class JSONValidator:
    def validate(self, payload: Any) -> bool:
        try:
            json.dumps(payload)
            return True
        except Exception:
            return False
