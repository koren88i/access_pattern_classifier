from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from statistics import mean
from typing import Any, Callable


DEFAULT_WEIGHTING_MODES = (
    "request_count",
    "latency_cost",
    "response_volume",
    "unique_systems",
    "unique_customers",
)

DAILY_VIEW_DIMENSIONS = {
    "profile": ("system_id", "customer_id", "platform", "database_or_index"),
    "system": ("system_id", "platform"),
    "platform": ("platform",),
    "customer": ("customer_id", "platform"),
    "template": ("system_id", "platform", "template_id"),
}

MISSING_DIMENSION_VALUES = {
    "customer_id": "unknown_customer",
    "system_id": "unknown_system",
    "template_id": "unknown_template",
    "database_or_index": "unknown_database_or_index",
    "platform": "unknown_platform",
}


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _window_start(value: str) -> datetime:
    timestamp = _parse_timestamp(value)
    return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return ordered[index]


def _average_optional(values: list[Any]) -> float | None:
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    return mean(numeric) if numeric else None


def _known_values(events: list[dict[str, Any]], key: str) -> set[str]:
    return {
        str(event[key])
        for event in events
        if event.get(key) not in (None, "")
    }


def _dimension_value(event: dict[str, Any], dimension: str) -> str:
    value = event.get(dimension)
    if value in (None, ""):
        return MISSING_DIMENSION_VALUES.get(dimension, f"unknown_{dimension}")
    return str(value)


def _aggregate_window_id(key: dict[str, Any]) -> str:
    raw = json.dumps(key, sort_keys=True, default=str)
    return "agg-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _weight_value(event: dict[str, Any], mode: str) -> float:
    if mode == "request_count":
        return 1.0
    if mode == "latency_cost":
        return max(0.0, float(event.get("latency_ms") or 0.0))
    if mode == "response_volume":
        return max(0.0, float(event.get("response_bytes") or 0.0))
    raise ValueError(f"unsupported event weighting mode: {mode}")


def _weighted_primitive_profile(
    events: list[dict[str, Any]],
    primitive_names: list[str],
    weight_fn: Callable[[dict[str, Any]], float],
) -> dict[str, float]:
    weighted_total = sum(weight_fn(event) for event in events)
    if weighted_total <= 0:
        return {primitive: 0.0 for primitive in primitive_names}

    return {
        primitive: (
            sum(
                event["primitive_signals"][primitive]["signal_weight"] * weight_fn(event)
                for event in events
            )
            / weighted_total
        )
        for primitive in primitive_names
    }


def _entity_weighted_primitive_profile(
    events: list[dict[str, Any]],
    primitive_names: list[str],
    entity_key: str,
) -> dict[str, float]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        entity = event.get(entity_key)
        if entity not in (None, ""):
            grouped[str(entity)].append(event)

    if not grouped:
        return {primitive: 0.0 for primitive in primitive_names}

    entity_profiles = [
        _weighted_primitive_profile(entity_events, primitive_names, lambda _event: 1.0)
        for entity_events in grouped.values()
    ]
    return {
        primitive: mean(profile[primitive] for profile in entity_profiles)
        for primitive in primitive_names
    }


def _primitive_profiles(
    events: list[dict[str, Any]],
    primitive_names: list[str],
) -> dict[str, dict[str, float]]:
    return {
        "request_count": _weighted_primitive_profile(
            events,
            primitive_names,
            lambda event: _weight_value(event, "request_count"),
        ),
        "latency_cost": _weighted_primitive_profile(
            events,
            primitive_names,
            lambda event: _weight_value(event, "latency_cost"),
        ),
        "response_volume": _weighted_primitive_profile(
            events,
            primitive_names,
            lambda event: _weight_value(event, "response_volume"),
        ),
        "unique_systems": _entity_weighted_primitive_profile(events, primitive_names, "system_id"),
        "unique_customers": _entity_weighted_primitive_profile(events, primitive_names, "customer_id"),
    }


def _window_key(
    view_name: str,
    group_by: tuple[str, ...],
    dimension_values: tuple[Any, ...],
    start: datetime,
) -> dict[str, Any]:
    return {
        "aggregation_view": view_name,
        **dict(zip(group_by, dimension_values)),
        "window_start": start.isoformat().replace("+00:00", "Z"),
        "window_end": (start + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
    }


def _volume_metrics(events: list[dict[str, Any]], template_counts: Counter) -> dict[str, int]:
    return {
        "request_count": len(events),
        "unique_template_count": len(template_counts),
        "unique_system_count": len(_known_values(events, "system_id")),
        "unique_customer_count": len(_known_values(events, "customer_id")),
    }


def _latency_metrics(latencies: list[float]) -> dict[str, float]:
    return {
        "avg_latency_ms": mean(latencies) if latencies else 0.0,
        "p95_latency_ms": _p95(latencies),
        "max_latency_ms": max(latencies) if latencies else 0.0,
    }


def _data_metrics(events: list[dict[str, Any]]) -> dict[str, float | None]:
    return {
        "avg_response_bytes": _average_optional([event.get("response_bytes") for event in events]),
        "avg_result_count": _average_optional([event.get("result_count") for event in events]),
    }


def _top_templates(
    events: list[dict[str, Any]],
    template_counts: Counter,
    primitive_names: list[str],
) -> list[dict[str, Any]]:
    request_count = len(events)
    top_templates = []
    for template_id, count in template_counts.most_common(10):
        matching_events = [event for event in events if event["template_id"] == template_id]
        top_templates.append(
            {
                "template_id": template_id,
                "request_count": count,
                "contribution": count / request_count,
                "primitive_summary": {
                    primitive: sum(
                        event["primitive_signals"][primitive]["signal_weight"]
                        for event in matching_events
                    )
                    / count
                    for primitive in primitive_names
                },
            }
        )
    return top_templates


def _top_templates_coverage(template_counts: Counter, request_count: int) -> float:
    top_ten_count = sum(count for _, count in template_counts.most_common(10))
    return top_ten_count / request_count if request_count else 0.0


def aggregate_daily_by(
    primitive_events: list[dict[str, Any]],
    group_by: tuple[str, ...],
    view_name: str = "custom",
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for event in primitive_events:
        key = (
            *(_dimension_value(event, dimension) for dimension in group_by),
            _window_start(event["timestamp"]),
        )
        grouped[key].append(event)

    windows: list[dict[str, Any]] = []
    for group_key, events in sorted(grouped.items(), key=lambda item: item[0]):
        dimension_values = group_key[:-1]
        start = group_key[-1]
        request_count = len(events)
        template_counts = Counter(event["template_id"] for event in events)
        latencies = [float(event["latency_ms"]) for event in events]
        primitive_names = list(events[0]["primitive_signals"].keys()) if events else []
        primitive_profiles = _primitive_profiles(events, primitive_names)
        top_templates_coverage = _top_templates_coverage(template_counts, request_count)
        top_templates = _top_templates(events, template_counts, primitive_names)
        key = _window_key(view_name, group_by, dimension_values, start)

        windows.append(
            {
                "aggregate_window_id": _aggregate_window_id(key),
                "key": key,
                "volume_metrics": _volume_metrics(events, template_counts),
                "latency_metrics": _latency_metrics(latencies),
                "data_metrics": _data_metrics(events),
                "primitive_profile": primitive_profiles["request_count"],
                "primitive_profiles": primitive_profiles,
                "template_metrics": {
                    "top_templates_coverage": top_templates_coverage,
                    "template_stability": top_templates_coverage,
                },
                "top_templates": top_templates,
            }
        )
    return windows


def aggregate_daily(primitive_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return aggregate_daily_by(
        primitive_events,
        group_by=DAILY_VIEW_DIMENSIONS["profile"],
        view_name="profile",
    )


def aggregate_daily_views(primitive_events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        view_name: aggregate_daily_by(
            primitive_events,
            group_by=dimensions,
            view_name=view_name,
        )
        for view_name, dimensions in DAILY_VIEW_DIMENSIONS.items()
    }
