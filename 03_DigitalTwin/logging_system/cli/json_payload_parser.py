from __future__ import annotations

import json


def parse_json_object(payload: str) -> dict[str, object]:
    if payload.strip() == "":
        return {}
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON object payload: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("JSON payload must be an object")
    return parsed
