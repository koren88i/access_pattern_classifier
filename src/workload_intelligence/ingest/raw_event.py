from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


SUPPORTED_PLATFORMS = {
    "elasticsearch",
    "redis",
    "mongo",
    "postgres",
    "cassandra",
    "s3",
}


@dataclass(frozen=True)
class RawUsageEvent:
    event_id: str
    timestamp: datetime
    identity: dict[str, Any]
    platform: dict[str, Any]
    operation: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any]

    @property
    def system_id(self) -> str:
        return str(self.identity["system_id"])

    @property
    def platform_type(self) -> str:
        return str(self.platform["type"])


def parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError(f"timestamp must be datetime or ISO string, got {type(value)!r}")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def raw_event_from_dict(payload: dict[str, Any]) -> RawUsageEvent:
    platform = payload.get("platform") or {}
    platform_type = platform.get("type")
    if platform_type not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported platform type: {platform_type!r}")

    identity = payload.get("identity") or {}
    if not identity.get("system_id"):
        raise ValueError("identity.system_id is required")

    response = payload.get("response") or {}
    if "latency_ms" not in response:
        raise ValueError("response.latency_ms is required")

    return RawUsageEvent(
        event_id=str(payload["event_id"]),
        timestamp=parse_timestamp(payload["timestamp"]),
        identity=dict(identity),
        platform=dict(platform),
        operation=dict(payload.get("operation") or {}),
        request=dict(payload.get("request") or {}),
        response=dict(response),
    )


def raw_event_to_dict(event: RawUsageEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat().replace("+00:00", "Z"),
        "identity": event.identity,
        "platform": event.platform,
        "operation": event.operation,
        "request": event.request,
        "response": event.response,
    }

