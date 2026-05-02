from __future__ import annotations

from typing import Any

from workload_intelligence.ingest.raw_event import RawUsageEvent, raw_event_to_dict
from workload_intelligence.normalize.template_fingerprint import fingerprint_query


def normalize_elasticsearch_event(event: RawUsageEvent) -> dict[str, Any]:
    payload = raw_event_to_dict(event)
    raw_query = event.operation.get("raw_query")
    if raw_query is None:
        raw_query = event.operation.get("body") or {}

    fingerprint = fingerprint_query(raw_query)
    payload["operation"]["raw_query"] = raw_query
    payload["operation"]["normalized_query"] = fingerprint["normalized_query"]
    payload["template_id"] = fingerprint["template_id"]
    return payload

