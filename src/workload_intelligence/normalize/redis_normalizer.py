from __future__ import annotations

from typing import Any

from workload_intelligence.ingest.raw_event import RawUsageEvent, raw_event_to_dict
from workload_intelligence.normalize.template_fingerprint import template_id_for


TTL_COMMANDS = {"SETEX", "PSETEX", "EXPIRE", "PEXPIRE"}
SET_COMMANDS_WITH_TTL_OPTIONS = {"EX", "PX", "EXAT", "PXAT"}


def _tokens(event: RawUsageEvent) -> list[str]:
    explicit = event.operation.get("args")
    if isinstance(explicit, list):
        return [str(token) for token in explicit]
    raw_query = event.operation.get("raw_query")
    if isinstance(raw_query, str):
        return raw_query.split()
    return []


def redis_has_ttl_signal(event: RawUsageEvent) -> bool:
    command = str(event.operation.get("command", "")).upper()
    if command in TTL_COMMANDS:
        return True
    return any(token.upper() in SET_COMMANDS_WITH_TTL_OPTIONS for token in _tokens(event))


def normalize_redis_event(event: RawUsageEvent) -> dict[str, Any]:
    payload = raw_event_to_dict(event)
    command = str(event.operation.get("command", "")).upper()
    tokens = _tokens(event)
    key = event.operation.get("key") or (tokens[1] if len(tokens) > 1 else None)
    key_pattern = event.operation.get("key_pattern") or (str(key).split(":")[0] + ":*" if key else None)
    normalized = {
        "command": command,
        "key_pattern": key_pattern,
        "has_ttl": redis_has_ttl_signal(event),
    }
    payload["operation"]["command"] = command
    payload["operation"]["normalized_query"] = normalized
    payload["operation"]["ttl_or_expire_signal"] = normalized["has_ttl"]
    payload["template_id"] = template_id_for(normalized)
    return payload

