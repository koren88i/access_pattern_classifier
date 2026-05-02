from __future__ import annotations

import hashlib
import json
from typing import Any


VALUE_PLACEHOLDER = "?"
STRUCTURAL_VALUE_KEYS = {
    "field",
    "fields",
    "type",
    "order",
    "format",
    "interval",
    "calendar_interval",
    "fixed_interval",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def normalize_template(value: Any, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {str(key): normalize_template(item, str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_template(item, parent_key) for item in value]
    if parent_key in STRUCTURAL_VALUE_KEYS:
        return value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return VALUE_PLACEHOLDER
    return VALUE_PLACEHOLDER


def template_id_for(value: Any) -> str:
    normalized = normalize_template(value)
    return template_id_for_normalized(normalized)


def template_id_for_normalized(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"tpl-{digest[:16]}"


def fingerprint_query(value: Any) -> dict[str, Any]:
    normalized = normalize_template(value)
    return {
        "template_id": template_id_for(value),
        "normalized_query": normalized,
    }
